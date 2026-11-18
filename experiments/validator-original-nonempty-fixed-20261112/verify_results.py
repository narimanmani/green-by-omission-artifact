"""Read-only independent audit of retained hosted experimental evidence."""

from __future__ import annotations

import hashlib
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = Path(sys.argv[1]).resolve()
MANIFEST = json.loads((HERE / "input" / "FROZEN_MANIFEST.json").read_text())
AUDIT = json.loads((ROOT / "AUDIT.json").read_text())


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def report_rows(folder: Path) -> list[dict]:
    rows = []
    for path in sorted(folder.glob("TEST-*.xml")):
        tree = ET.parse(path)
        for case in tree.getroot().iter("testcase"):
            state = "failure" if case.find("failure") is not None else "error" if case.find("error") is not None else "skipped" if case.find("skipped") is not None else "passed"
            rows.append({"class": case.get("classname"), "name": case.get("name"), "outcome": state})
    return sorted(rows, key=lambda r: (r["class"], r["name"], r["outcome"]))


assert AUDIT["repetitions"] == 3
assert AUDIT["statuses"] == ["VALID_FIXED_CASE"] * 3
assert AUDIT["joint_observations"] == [True] * 3
assert AUDIT["baseline_counts"] == [60] * 3
assert AUDIT["native_counts"] == [20] * 3
assert AUDIT["independent_counts"] == [60] * 3
assert sha(HERE / "input" / "collision.java") == MANIFEST["collision_java_sha256"]
control_source = HERE / "input" / "upstream" / MANIFEST["candidate_source_paths"][1]
assert sha(control_source) == MANIFEST["control_original_sha256"]
old = MANIFEST["control_fixed_old_snippet"].encode()
new = MANIFEST["control_fixed_new_snippet"].encode()
assert control_source.read_bytes().count(old) == 1
fixed_control_sha = hashlib.sha256(control_source.read_bytes().replace(old, new)).hexdigest()

for n in range(1, 4):
    folder = ROOT / f"repetition-{n}"
    assert (folder / "READY").is_file() and (folder / "runner-exit").read_text().strip() == "0"
    result = json.loads((folder / "result.json").read_text())
    arms = json.loads((folder / "arms.json").read_text())
    identity = json.loads((folder / "candidate-identity.json").read_text())
    saved = AUDIT["raw_records"][n - 1]
    assert saved["repetition"] == n and saved["result"] == result and saved["arms"] == arms and saved["identity"] == identity
    for filename, digest in saved["raw_sha256"].items():
        assert sha(folder / filename) == digest, (n, filename)
    assert [r["arm"] for r in arms] == ["baseline", "unchanged", "native", "independent"]
    for arm in arms:
        label = arm["arm"]
        assert json.loads((folder / f"{label}-process.json").read_text())["exit"] == arm["exit"]
        assert report_rows(folder / f"{label}-surefire") == sorted(arm["tests"], key=lambda r: (r["class"], r["name"], r["outcome"]))
    assert json.loads((folder / "candidate_compile-process.json").read_text())["exit"] == 0
    baseline, unchanged, native, independent = arms
    assert [a["exit"] for a in (baseline, unchanged, native, independent)] == [0, 0, 0, 1]
    assert len(baseline["tests"]) == len(independent["tests"]) == 60
    assert len(unchanged["tests"]) == 0 and len(native["tests"]) == 20
    assert all(t["outcome"] == "passed" for t in baseline["tests"] + native["tests"])
    assert {t["class"].split(".")[-1] for t in baseline["tests"]} == set(MANIFEST["original_full_test_scope"])
    assert {t["class"].split(".")[-1] for t in native["tests"]} == {"CreditCardValidatorTest"}
    ids = lambda arm: {(t["class"], t["name"]) for t in arm["tests"]}
    assert ids(baseline) == ids(independent)
    failures = [t for t in independent["tests"] if t["outcome"] in ("failure", "error")]
    assert {(t["class"].split(".")[-1], t["name"], t["outcome"]) for t in failures} == {
        ("UrlValidatorTest", "testIsValidScheme", "failure"),
        ("UrlValidatorTest", "testValidator276", "failure"),
    }
    assert ids(native).isdisjoint({(t["class"], t["name"]) for t in failures})
    assert result["status"] == "VALID_FIXED_CASE" and result["joint_observation"] is True
    assert result["independent_failed"] == failures and result["omitted_security_failures"] == failures
    assert result["exits"] == [0, 0, 1]
    assert identity["url_class_fingerprint_baseline"] == identity["url_class_fingerprint_candidate"] == MANIFEST["recorded_native_class_fingerprint"]
    assert identity["url_class_sha256"] == MANIFEST["collision_class_sha256"]
    assert identity["url_source_sha256"] == MANIFEST["collision_java_sha256"]
    assert identity["control_source_sha256"] == fixed_control_sha
    metadata = list((folder / "trusted-baseline-metadata").glob("*.clz"))
    assert len(metadata) == 3

print("Verified 3 fresh repetitions: baseline 60 pass; native 20 pass; independent 60 with 2 omitted original URL failures; native URL fingerprint equal.")
