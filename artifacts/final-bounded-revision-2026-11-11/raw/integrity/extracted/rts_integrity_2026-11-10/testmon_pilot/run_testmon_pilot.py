#!/usr/bin/env python3
"""Local synthetic testmon metadata-integrity experiment.

This script deliberately changes only toy arithmetic and formatting behavior.
Faults apply to the entire local cache file; no dependency rows, fingerprints,
or checksums are forged. Run inside the pinned virtual environment.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
WORK = ROOT / "work"
EVIDENCE = ROOT / "evidence"
TRUSTED = ROOT / "trusted"
SNAPSHOT = TRUSTED / "baseline"

SOURCES = {
    "arithmetic.py": "def add(a, b):\n    return a + b\n",
    "label.py": "def status():\n    return 'ready'\n",
    "untouched.py": "def identity(x):\n    return x\n",
    "test_arithmetic.py": (
        "from arithmetic import add\n\n"
        "def test_positive():\n    assert add(2, 2) == 4\n\n"
        "def test_negative():\n    assert add(-2, -2) == -4\n"
    ),
    "test_label.py": "from label import status\n\ndef test_label():\n    assert status() == 'ready'\n",
    "test_untouched.py": "from untouched import identity\n\ndef test_identity():\n    assert identity(5) == 5\n",
    "pytest.ini": "[pytest]\ntestpaths = .\npython_files = test_*.py\naddopts = -ra\n",
}

FAULTS = ("none", "missing", "empty", "half_truncated", "garbage")
STRATEGIES = ("standard_rts", "fail_closed", "full_suite")


def digest(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write_json(p: Path, value) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def cache_files() -> list[Path]:
    return sorted(p for p in WORK.glob(".testmondata*") if p.is_file())


def cache_manifest() -> dict:
    return {p.name: {"sha256": digest(p), "bytes": p.stat().st_size} for p in cache_files()}


def test_manifest() -> dict:
    return {p.name: digest(p) for p in sorted(WORK.glob("test_*.py"))}


def source_manifest() -> dict:
    return {p.name: digest(p) for p in sorted(WORK.glob("*.py"))}


def reset_work() -> None:
    if WORK.exists():
        shutil.rmtree(WORK)
    shutil.copytree(SNAPSHOT, WORK)
    for p in WORK.rglob("__pycache__"):
        shutil.rmtree(p)
    shutil.rmtree(WORK / ".pytest_cache", ignore_errors=True)


def candidate_change() -> None:
    (WORK / "arithmetic.py").write_text("def add(a, b):\n    return a + b + 1\n")
    # A second changed module keeps a passing changed test in the selection.
    (WORK / "label.py").write_text("def status():\n    return ''.join(('rea', 'dy'))\n")


def inject_fault(mode: str) -> dict:
    before = cache_manifest()
    if mode != "none":
        p = WORK / ".testmondata"
        if not p.is_file():
            raise RuntimeError("Expected .testmondata database is absent before injection")
        if mode == "missing":
            for f in cache_files():
                f.unlink()
        elif mode == "empty":
            p.write_bytes(b"")
        elif mode == "half_truncated":
            b = p.read_bytes()
            p.write_bytes(b[: len(b) // 2])
        elif mode == "garbage":
            p.write_bytes(b"SYNTHETIC_METADATA_INTEGRITY_FAULT\n")
        else:
            raise ValueError(mode)
    return {"mode": mode, "before": before, "after": cache_manifest()}


def parse_xml(p: Path) -> dict:
    result = {"executed_nodeids": [], "failing_nodeids": [], "skipped_nodeids": [], "tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    if not p.exists():
        result["xml_exists"] = False
        return result
    result["xml_exists"] = True
    root = ET.parse(p).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    for suite in suites:
        for key in ("tests", "failures", "errors", "skipped"):
            result[key] += int(suite.get(key, "0"))
    for case in root.iter("testcase"):
        nodeid = case.get("classname", "").replace(".", "/") + ".py::" + case.get("name", "")
        if case.find("skipped") is not None:
            result["skipped_nodeids"].append(nodeid)
        else:
            result["executed_nodeids"].append(nodeid)
        if case.find("failure") is not None or case.find("error") is not None:
            result["failing_nodeids"].append(nodeid)
    return result


def execute(run_id: str, strategy: str, fault: str, repetition: int, source_state: str, expected: dict | None = None) -> dict:
    out = EVIDENCE / run_id
    out.mkdir(parents=True)
    current_cache = cache_manifest()
    integrity_ok = expected is None or (current_cache == expected["cache"] and test_manifest() == expected["tests"])
    fallback = strategy == "fail_closed" and not integrity_ok
    use_rts = strategy == "standard_rts" or (strategy == "fail_closed" and not fallback)
    cmd = [sys.executable, "-m", "pytest", "-q", "--junitxml=" + str(out / "junit.xml")]
    cmd += ["--testmon"] if use_rts else ["-p", "no:testmon"]
    env = os.environ.copy()
    env.update({"PYTHONHASHSEED": "0", "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "0", "TZ": "UTC"})
    # Any nonempty PYTEST_DISABLE_PLUGIN_AUTOLOAD disables plugins. Explicitly
    # load exactly the one under test, avoiding unrelated ambient plugins.
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    if use_rts:
        cmd.extend(["-p", "testmon.pytest_testmon"])
    write_json(out / "pre_state.json", {"cache": current_cache, "sources": source_manifest(), "tests": test_manifest()})
    start = time.perf_counter()
    proc = subprocess.run(cmd, cwd=WORK, env=env, capture_output=True, text=True, timeout=60)
    elapsed = time.perf_counter() - start
    (out / "stdout.txt").write_text(proc.stdout)
    (out / "stderr.txt").write_text(proc.stderr)
    parsed = parse_xml(out / "junit.xml")
    status = "pass" if proc.returncode == 0 else "no_tests_collected" if proc.returncode == 5 else "test_failure" if proc.returncode == 1 and parsed["failures"] > 0 else "runner_error"
    result = {
        "run_id": run_id, "strategy": strategy, "fault": fault,
        "repetition": repetition, "source_state": source_state,
        "command": cmd, "cwd": str(WORK), "exit_code": proc.returncode,
        "status": status, "elapsed_s": elapsed,
        "integrity_checked": strategy == "fail_closed",
        "integrity_ok": integrity_ok if strategy == "fail_closed" else None,
        "full_suite_fallback": fallback, "used_testmon": use_rts,
        "evidence_class": "controlled_fault_native_execution" if fault != "none" else "native_execution",
        "source_hashes": source_manifest(), "test_hashes": test_manifest(), **parsed,
    }
    write_json(out / "result.json", result)
    print(json.dumps({k: result[k] for k in ("run_id", "exit_code", "status", "tests", "failures", "full_suite_fallback", "elapsed_s")}), flush=True)
    return result


def run(repetitions: int) -> None:
    for d in (WORK, EVIDENCE, TRUSTED):
        if d.exists():
            raise RuntimeError(f"Refusing to overwrite existing experiment directory: {d}")
        d.mkdir()
    for name, content in SOURCES.items():
        (WORK / name).write_text(content)
    versions = {p: importlib.metadata.version(p) for p in ("pytest", "pytest-testmon", "coverage")}
    versions.update({"python": sys.version, "platform": sys.platform})
    write_json(ROOT / "environment.json", versions)
    results = []
    results.append(execute("00_cold_baseline", "standard_rts", "none", 0, "baseline"))
    if results[-1]["exit_code"] != 0 or results[-1]["tests"] != 4:
        raise RuntimeError("Cold baseline failed validation; stop before fault injection")
    results.append(execute("01_warm_unchanged", "standard_rts", "none", 0, "baseline"))
    # Freeze one cache generation, then always restore to the same absolute path.
    shutil.copytree(WORK, SNAPSHOT)
    expected = {"cache": cache_manifest(), "tests": test_manifest(), "sources": source_manifest(), "versions": versions,
                "trust_assumption": "Manifest and baseline snapshot are outside the injected directory and immutable to the fault injector. This is a local harness trust assumption, not deployed authentication."}
    write_json(TRUSTED / "manifest.json", expected)
    reset_work()
    results.append(execute("02_full_baseline", "full_suite", "none", 0, "baseline"))
    reset_work()
    candidate_change()
    results.append(execute("03_full_changed_oracle", "full_suite", "none", 0, "candidate"))
    oracle = set(results[-1]["failing_nodeids"])
    if len(oracle) != 2:
        raise RuntimeError("Changed full-suite oracle must expose exactly two synthetic arithmetic failures")
    for repetition in range(1, repetitions + 1):
        for fault in FAULTS:
            for strategy in STRATEGIES:
                reset_work()
                candidate_change()
                run_id = f"r{repetition}_{fault}_{strategy}"
                state = inject_fault(fault)
                result = execute(run_id, strategy, fault, repetition, "candidate", expected)
                write_json(EVIDENCE / run_id / "fault.json", state)
                result["oracle_failing_nodeids"] = sorted(oracle)
                result["relevant_omitted_nodeids"] = sorted(oracle - set(result["executed_nodeids"]))
                result["false_accept"] = result["exit_code"] == 0
                result["oracle_tests_detected"] = len(oracle & set(result["failing_nodeids"]))
                write_json(EVIDENCE / run_id / "result.json", result)
                results.append(result)
    write_json(ROOT / "results.json", results)
    fields = ["run_id", "strategy", "fault", "repetition", "source_state", "evidence_class", "exit_code", "status", "tests", "failures", "errors", "skipped", "integrity_checked", "integrity_ok", "full_suite_fallback", "oracle_tests_detected", "false_accept", "elapsed_s", "executed_nodeids", "failing_nodeids", "relevant_omitted_nodeids"]
    with (ROOT / "results.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for r in results:
            row = dict(r)
            for k, v in row.items():
                if isinstance(v, list):
                    row[k] = json.dumps(v)
            writer.writerow(row)
    summarize(results, repetitions)


def summarize(results: list[dict], repetitions: int) -> None:
    rows = []
    for fault in FAULTS:
        for strategy in STRATEGIES:
            group = [r for r in results if r["fault"] == fault and r["strategy"] == strategy and r["repetition"] > 0]
            rows.append({"fault": fault, "strategy": strategy, "runs": len(group),
                         "tests": sorted({r["tests"] for r in group}),
                         "failures": sorted({r["failures"] for r in group}),
                         "statuses": sorted({r["status"] for r in group}),
                         "false_accepts": sum(r["false_accept"] for r in group),
                         "fallbacks": sum(r["full_suite_fallback"] for r in group),
                         "median_elapsed_s": sorted(r["elapsed_s"] for r in group)[len(group)//2]})
    write_json(ROOT / "summary.json", {"rows": rows, "repetitions": repetitions,
        "statistical_unit": "One deterministic synthetic fixture; repetitions assess repeatability and are not independent security trials.",
        "population_inference": "None. These results do not estimate real-world bypass or defect prevalence."})
    lines = ["# pytest-testmon synthetic integrity pilot", "", "## Scope", "",
             "Actual local execution of pytest-testmon 2.3.0 against four synthetic tests. Two unchanged arithmetic tests fail after a harmless +1 arithmetic mutation. A changed-but-passing label module keeps an independent changed test available. A fourth test uses an unchanged module.", "",
             "All cache faults are simulations of missing/corrupted metadata. No dependency rows or fingerprints were selectively edited. No real security vulnerability or attacker bypass was introduced.", "",
             "## Observed controls", "", "| Run | Exit | Tests | Failures | Status |", "|---|---:|---:|---:|---|"]
    for r in results[:4]:
        lines.append(f"| {r['run_id']} | {r['exit_code']} | {r['tests']} | {r['failures']} | {r['status']} |")
    lines += ["", f"## Fault comparison ({repetitions} deterministic repeats per condition)", "", "| Fault | Strategy | Tests per run | Failures per run | Status | False accepts | Fallbacks |", "|---|---|---|---|---|---:|---:|"]
    for r in rows:
        lines.append(f"| {r['fault']} | {r['strategy']} | {r['tests']} | {r['failures']} | {', '.join(r['statuses'])} | {r['false_accepts']} / {r['runs']} | {r['fallbacks']} / {r['runs']} |")
    lines += ["", "## Interpretation limits", "",
              "- `runner_error` means the test process did not complete normally. It is not a passing pipeline or successful defect detection.",
              "- Zero collected tests and their actual exit code are reported without normalization.",
              "- The independent full-suite oracle disables testmon. Cache state is reset at the same absolute path before every comparison.",
              "- Tests remain byte-identical throughout; raw JUnit XML and per-run source/cache hashes are archived.",
              "- SHA-256 verification assumes a trusted, separately stored manifest and unchanged test inventory. It does not authenticate metadata if that manifest is also replaceable, protect against a verification/use race, or establish source-to-cache semantic correctness.",
              "- No confidence interval for attack success is appropriate: there is one designed fixture, five fault conditions, and deterministic repeats.",
              "- Runtimes include Python/pytest startup and local filesystem effects. They are descriptive, not a production performance benchmark.",
              "- Unmeasured: attacker write capability, production cache exposure, larger suites, parallel workers, other Python/testmon versions, and malicious dependency graphs.", "",
              "## Reproduction", "", "Create a fresh directory containing this script and requirements.txt, install the pinned requirements in a Python 3.12 virtual environment, and run `python run_testmon_pilot.py --repetitions 3`. The script refuses to overwrite previous run directories.", ""]
    (ROOT / "RESULTS.md").write_text("\n".join(lines))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repetitions", type=int, default=3)
    args = parser.parse_args()
    if args.repetitions < 1:
        parser.error("repetitions must be positive")
    run(args.repetitions)
