"""Run one fresh, fixed Commons Validator/Ekstazi repetition inside the lab."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path


WORK = Path("/work")
OUT = WORK / "out"
OUT.mkdir(parents=True, exist_ok=True)
INPUT = Path("/opt/input")
SOURCE = Path("/opt/upstream")
MANIFEST = json.loads((INPUT / "FROZEN_MANIFEST.json").read_text())
REPO = WORK / "native"
FULL = WORK / "independent"
SOURCE_FILE = MANIFEST["candidate_source_paths"][0]
CONTROL_FILE = MANIFEST["candidate_source_paths"][1]
CLASS_FILE = "target/classes/org/apache/commons/validator/routines/UrlValidator.class"
CONTROL_CLASS = "target/classes/org/apache/commons/validator/routines/CreditCardValidator.class"
BASE_METADATA = OUT / "trusted-baseline-metadata"
M2 = WORK / "m2"
JAR = M2 / "repository/org/ekstazi/org.ekstazi.core/5.3.0/org.ekstazi.core-5.3.0.jar"
ROWS = []


class EligibilityError(Exception):
    pass


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise EligibilityError(reason)


def verify_tree(repo: Path, candidate: bool = False) -> None:
    require(sha((repo / "pom.xml").read_bytes()) == MANIFEST["integrated_pom_sha256"], "integrated POM changed")
    for path, expected in MANIFEST["original_source_test_sha256"].items():
        if candidate and path in (SOURCE_FILE, CONTROL_FILE):
            continue
        require(sha((repo / path).read_bytes()) == expected, "original source or test changed: " + path)
    if candidate:
        require(sha((repo / SOURCE_FILE).read_bytes()) == MANIFEST["collision_java_sha256"], "collision source changed")
        old = MANIFEST["control_fixed_old_snippet"].encode()
        new = MANIFEST["control_fixed_new_snippet"].encode()
        original = (SOURCE / CONTROL_FILE).read_bytes()
        require(original.count(old) == 1, "control edit is not unique")
        require((repo / CONTROL_FILE).read_bytes() == original.replace(old, new), "control source changed outside fixed edit")


def command(label: str, args: list[str], repo: Path, timeout: int = 720) -> subprocess.CompletedProcess[str]:
    begin = time.monotonic()
    proc = subprocess.run(args, cwd=repo, capture_output=True, text=True, timeout=timeout, env={**os.environ, "MAVEN_OPTS": "-Xmx1500m"})
    (OUT / (label + ".log")).write_text(proc.stdout + "\n" + proc.stderr, encoding="utf-8")
    (OUT / (label + "-process.json")).write_text(json.dumps({"command": args, "exit": proc.returncode, "seconds": round(time.monotonic() - begin, 3)}, indent=2) + "\n")
    return proc


def mvn_args(profile: bool, phase: str) -> list[str]:
    args = ["mvn", "-o", "-B", "-ntp", "-Dcheckstyle.skip", "-Drat.skip=true", "-Dmaven.repo.local=" + str(M2 / "repository")]
    if profile:
        args.append("-Pekstazi-study")
    args.append(phase)
    return args


def run(label: str, repo: Path, profile: bool) -> dict:
    reports = repo / "target" / "surefire-reports"
    if reports.exists():
        shutil.rmtree(reports)
    proc = command(label, mvn_args(profile, "test"), repo)
    tests = []
    for report in sorted(reports.glob("TEST-*.xml")) if reports.exists() else []:
        root = ET.parse(report).getroot()
        for case in root.findall("testcase"):
            outcome = "failure" if case.find("failure") is not None else "error" if case.find("error") is not None else "skipped" if case.find("skipped") is not None else "passed"
            tests.append({"class": case.get("classname"), "name": case.get("name"), "outcome": outcome})
    if reports.exists():
        shutil.copytree(reports, OUT / (label + "-surefire"))
    row = {"arm": label, "exit": proc.returncode, "tests": tests}
    ROWS.append(row)
    (OUT / "arms.json").write_text(json.dumps(ROWS, indent=2) + "\n")
    if proc.returncode and not any(t["outcome"] in ("failure", "error") for t in tests):
        raise EligibilityError(label + " Maven failed without test assertion failure")
    return row


def native_fingerprint(path: Path) -> int:
    proc = subprocess.run(["java", "-cp", os.pathsep.join([str(WORK), str(JAR)]), "HashProbe", str(path)], capture_output=True, text=True, check=True)
    return int(proc.stdout.strip(), 16)


def apply_fixed_candidate(repo: Path) -> None:
    (repo / SOURCE_FILE).write_bytes((INPUT / "collision.java").read_bytes())
    old = MANIFEST["control_fixed_old_snippet"].encode()
    new = MANIFEST["control_fixed_new_snippet"].encode()
    original = (repo / CONTROL_FILE).read_bytes()
    require(original.count(old) == 1, "control edit missing or repeated")
    (repo / CONTROL_FILE).write_bytes(original.replace(old, new))
    verify_tree(repo, candidate=True)


try:
    require(MANIFEST["status"] == "FROZEN_BEFORE_CANDIDATE_EXECUTION", "manifest not frozen")
    require(sha((INPUT / "collision.java").read_bytes()) == MANIFEST["collision_java_sha256"], "collision input mismatch")
    shutil.copytree(Path("/home/lab/.m2"), M2)
    shutil.copytree(SOURCE, REPO)
    verify_tree(REPO)
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip() == MANIFEST["upstream_commit"], "upstream revision mismatch")
    require(JAR.is_file(), "native Ekstazi core jar missing")
    javac = subprocess.run(["javac", "-cp", str(JAR), "-d", str(WORK), str(INPUT / "HashProbe.java")], capture_output=True, text=True)
    require(javac.returncode == 0, "HashProbe compile failed: " + javac.stderr[:500])

    baseline = run("baseline", REPO, True)
    require(baseline["exit"] == 0 and baseline["tests"] and all(t["outcome"] == "passed" for t in baseline["tests"]), "original baseline did not fully pass")
    original_classes = {t["class"].rsplit(".", 1)[-1] for t in baseline["tests"]}
    require(original_classes == set(MANIFEST["original_full_test_scope"]), "baseline test class scope mismatch")
    require(sha((REPO / CLASS_FILE).read_bytes()) == MANIFEST["baseline_class_sha256"], "baseline class build differs from archived class")
    control_baseline_class_sha = sha((REPO / CONTROL_CLASS).read_bytes())
    base_crc = native_fingerprint(REPO / CLASS_FILE)
    require(base_crc == MANIFEST["recorded_native_class_fingerprint"], "baseline native fingerprint mismatch")
    require((REPO / ".ekstazi").is_dir(), "baseline Ekstazi metadata absent")
    shutil.copytree(REPO / ".ekstazi", BASE_METADATA)
    unchanged = run("unchanged", REPO, True)
    require(unchanged["exit"] == 0 and not unchanged["tests"], "unchanged-run native deselection did not hold")
    verify_tree(REPO)

    apply_fixed_candidate(REPO)
    comp = command("candidate_compile", mvn_args(False, "compile"), REPO)
    require(comp.returncode == 0, "candidate compilation failed")
    require(sha((REPO / CLASS_FILE).read_bytes()) == MANIFEST["collision_class_sha256"], "compiled collision class differs from archived class")
    candidate_crc = native_fingerprint(REPO / CLASS_FILE)
    require(candidate_crc == base_crc, "candidate did not preserve native UrlValidator fingerprint")
    require((REPO / CONTROL_CLASS).is_file(), "control class absent")
    control_sha = sha((REPO / CONTROL_CLASS).read_bytes())
    require(control_sha != control_baseline_class_sha, "control class did not change")
    (OUT / "candidate-identity.json").write_text(json.dumps({"url_class_fingerprint_baseline": base_crc, "url_class_fingerprint_candidate": candidate_crc, "url_class_sha256": sha((REPO / CLASS_FILE).read_bytes()), "control_class_sha256": control_sha, "url_source_sha256": sha((REPO / SOURCE_FILE).read_bytes()), "control_source_sha256": sha((REPO / CONTROL_FILE).read_bytes())}, indent=2) + "\n")

    shutil.rmtree(REPO / ".ekstazi")
    shutil.copytree(BASE_METADATA, REPO / ".ekstazi")
    before_native = {p: sha((REPO / p).read_bytes()) for p in (SOURCE_FILE, CONTROL_FILE)}
    native = run("native", REPO, True)
    verify_tree(REPO, candidate=True)
    require(before_native == {p: sha((REPO / p).read_bytes()) for p in (SOURCE_FILE, CONTROL_FILE)}, "candidate changed during native execution")

    shutil.copytree(SOURCE, FULL)
    apply_fixed_candidate(FULL)
    require(before_native == {p: sha((FULL / p).read_bytes()) for p in (SOURCE_FILE, CONTROL_FILE)}, "independent candidate differs")
    independent = run("independent", FULL, False)
    verify_tree(FULL, candidate=True)
    require(before_native == {p: sha((FULL / p).read_bytes()) for p in (SOURCE_FILE, CONTROL_FILE)}, "candidate changed during independent execution")
    baseline_ids = {(t["class"], t["name"]) for t in baseline["tests"]}
    full_ids = {(t["class"], t["name"]) for t in independent["tests"]}
    require(baseline_ids == full_ids, "independent original test identity set differs from baseline")
    selected = {(t["class"], t["name"]) for t in native["tests"]}
    omitted = [t for t in independent["tests"] if t["outcome"] == "failure" and t["class"].endswith(".UrlValidatorTest") and (t["class"], t["name"]) not in selected]
    observed = bool(native["tests"] and native["exit"] == 0 and all(t["outcome"] == "passed" for t in native["tests"]) and omitted and independent["exit"] != 0)
    result = {"status": "VALID_FIXED_CASE", "joint_observation": observed, "baseline_test_count": len(baseline["tests"]), "native_test_count": len(native["tests"]), "native_classes": sorted({t["class"] for t in native["tests"]}), "independent_test_count": len(independent["tests"]), "independent_failed": [t for t in independent["tests"] if t["outcome"] in ("failure", "error")], "omitted_security_failures": omitted, "exits": [baseline["exit"], native["exit"], independent["exit"]]}
    (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
except (EligibilityError, subprocess.TimeoutExpired, subprocess.CalledProcessError, OSError, ET.ParseError) as exc:
    result = {"status": "INELIGIBLE_OR_INFRASTRUCTURE", "reason": str(exc), "completed_arms": [r["arm"] for r in ROWS]}
    (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
    sys.exit(2)
