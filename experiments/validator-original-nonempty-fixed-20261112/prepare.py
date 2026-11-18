"""Freeze the source and original test inputs before the first candidate run."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path


HERE = Path(__file__).resolve().parent
UPSTREAM = HERE / "input" / "upstream"
ARCHIVE = HERE.parents[1] / "artifacts" / "final-bounded-revision-2026-11-11" / "remote-java" / "canonical" / "upstream-commons"
PROVENANCE = ARCHIVE.parents[1] / "provenance"
EXPECTED_HEAD = "f9bb21748a9f9c50fbc31862de25ed49433ecc88"
SOURCE_PATH = "src/main/java/org/apache/commons/validator/routines/UrlValidator.java"
CONTROL_PATH = "src/main/java/org/apache/commons/validator/routines/CreditCardValidator.java"
TEST_CLASSES = ("UrlValidatorTest", "RegexValidatorTest", "CreditCardValidatorTest")
ORIGINAL_GUARD = b"""        if (card == null || card.length() == 0) {
            return false;
        }
"""
CONTROL_GUARD = b"""        if (card == null || card.length() == 0) {
            return Boolean.FALSE.booleanValue();
        }
"""


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


head = subprocess.check_output(["git", "-C", str(UPSTREAM), "rev-parse", "HEAD"], text=True).strip()
assert head == EXPECTED_HEAD, head
assert not subprocess.check_output(["git", "-C", str(UPSTREAM), "status", "--porcelain"], text=True).strip()
assert (UPSTREAM / SOURCE_PATH).read_bytes() == (ARCHIVE / "baseline.java").read_bytes()
assert (ARCHIVE / "collision.java").is_file()
control = (UPSTREAM / CONTROL_PATH).read_bytes()
assert control.count(ORIGINAL_GUARD) == 1
assert CONTROL_GUARD != ORIGINAL_GUARD

original_pom = (UPSTREAM / "pom.xml").read_bytes()
existing = b"<include>**/routines/RegexValidatorTest.java</include>"
assert original_pom.count(existing) == 0
integrated = (ARCHIVE / "integrated-pom.xml").read_bytes()
assert integrated.count(existing) == 1
extra = b"<include>**/routines/CreditCardValidatorTest.java</include>"
assert extra not in integrated
integrated = integrated.replace(existing, existing + extra)
(HERE / "input" / "upstream-pom.xml").write_bytes(original_pom)
(UPSTREAM / "pom.xml").write_bytes(integrated)
shutil.copyfile(ARCHIVE / "collision.java", HERE / "input" / "collision.java")
shutil.copyfile(PROVENANCE / "canonical-HashProbe.java", HERE / "input" / "HashProbe.java")

files = {}
for root in ("src/main", "src/test"):
    for path in sorted((UPSTREAM / root).rglob("*")):
        if path.is_file():
            files[path.relative_to(UPSTREAM).as_posix()] = sha(path.read_bytes())
manifest = {
    "status": "FROZEN_BEFORE_CANDIDATE_EXECUTION",
    "upstream_commit": head,
    "original_full_test_scope": list(TEST_CLASSES),
    "candidate_source_paths": [SOURCE_PATH, CONTROL_PATH],
    "collision_java_sha256": sha((HERE / "input" / "collision.java").read_bytes()),
    "collision_class_sha256": sha((ARCHIVE / "collision.class").read_bytes()),
    "baseline_class_sha256": sha((ARCHIVE / "baseline.class").read_bytes()),
    "recorded_native_class_fingerprint": 577934113,
    "control_original_sha256": sha(control),
    "control_fixed_old_snippet": ORIGINAL_GUARD.decode("ascii"),
    "control_fixed_new_snippet": CONTROL_GUARD.decode("ascii"),
    "upstream_pom_sha256": sha(original_pom),
    "integrated_pom_sha256": sha(integrated),
    "original_source_test_sha256": files,
    "repetitions": 3,
    "qualification": "At least one unchanged original test executes and passes under native selection; unchanged UrlValidatorTest omitted there; identical candidate fails the original UrlValidatorTest independently.",
    "stop_rules": ["baseline failure", "unchanged run selects an original test", "native UrlValidator class fingerprint mismatch", "candidate source or original test identity mismatch", "Maven or Ekstazi infrastructure error"],
}
(HERE / "input" / "FROZEN_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"head": head, "manifest_sha256": sha((HERE / "input" / "FROZEN_MANIFEST.json").read_bytes()), "source_test_files": len(files), "pom_sha256": sha(integrated)}, indent=2))
