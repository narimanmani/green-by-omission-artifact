#!/usr/bin/env python3
"""Inspect retained reports without executing subjects, installing, or using a network.

Run from the extracted artifact root: python verify_results.py --root .
This checks observations and test identities, not independent reproduction or
historical hosting policy. Package byte integrity is checked by the separate
package-manifest verifier. Redaction may change original artifact digests.
"""

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET


class VerificationError(Exception):
    pass


def require(condition, message):
    if not condition:
        raise VerificationError(message)


def read(path):
    return path.read_text(encoding="utf-8-sig")


def load(path):
    return json.loads(read(path))


def junit(directory):
    files = sorted(directory.glob("TEST*.xml"))
    require(files, f"Missing Surefire XML: {directory}")
    cases = []
    for path in files:
        for case in ET.parse(path).getroot().iter("testcase"):
            outcome = next((name for name in ("failure", "error", "skipped")
                            if case.find(name) is not None), "passed")
            cases.append(((case.get("classname"), case.get("name")), outcome))
    require(len({identity for identity, _ in cases}) == len(cases),
            f"Duplicate JUnit identities: {directory}")
    return cases


def validator(root):
    base = root / "experiments/validator-original-nonempty-fixed-20261112/results/run-43348535685"
    output = []
    for number in (1, 2, 3):
        directory = base / f"repetition-{number}"
        arms = {name: junit(directory / f"{name}-surefire")
                for name in ("baseline", "native", "independent")}
        require(Counter(x for _, x in arms["baseline"]) == {"passed": 60}, "Validator baseline")
        require(Counter(x for _, x in arms["native"]) == {"passed": 20}, "Validator native")
        require(Counter(x for _, x in arms["independent"]) == {"passed": 58, "failure": 2},
                "Validator independent oracle")
        baseline = {x for x, _ in arms["baseline"]}
        selected = {x for x, _ in arms["native"]}
        failed = {x for x, outcome in arms["independent"] if outcome == "failure"}
        require(baseline == {x for x, _ in arms["independent"]}, "Validator oracle identities")
        require(selected <= baseline and failed.isdisjoint(selected), "Validator omission")
        require({name for _, name in failed} == {"testIsValidScheme", "testValidator276"},
                "Validator designated failures")
        require(all(name.endswith("CreditCardValidatorTest") for name, _ in selected),
                "Validator selected class")
        identity = load(directory / "candidate-identity.json")
        require(identity["url_class_fingerprint_baseline"] ==
                identity["url_class_fingerprint_candidate"] == 577934113, "Validator fingerprint")
        require(load(directory / "result.json")["exits"] == [0, 0, 1], "Validator exits")
        output.append({"repetition": number, "baseline_pass": 60, "selected_pass": 20,
                       "independent_pass": 58, "omitted_failures": 2})
    return output


def jest(root):
    base = root / "experiments/wxyc-fixed-historical-replay-20261112/native-parallel-correction/results"
    output = []
    for number in (1, 2, 3):
        evidence = load(base / f"repetition-{number}/evidence.json")
        observations = {}
        for name, expected, exit_code in (
                ("baseline", {"passed": 8173}, 0),
                ("selective", {"passed": 8}, 0),
                ("independent_full", {"passed": 8172, "failed": 1}, 1)):
            arm = evidence["arms"][name]
            raw = arm["raw_jest_json"]
            report = json.loads(raw) if isinstance(raw, str) else raw
            cases = [((suite["name"].replace("\\", "/"), case["fullName"]), case)
                     for suite in report["testResults"] for case in suite["assertionResults"]]
            require(Counter(case["status"] for _, case in cases) == expected, f"Jest {name} counts")
            require(len({identity for identity, _ in cases}) == len(cases), "Jest duplicate identities")
            require(not report.get("wasInterrupted") and not report.get("numRuntimeErrorTestSuites", 0),
                    f"Jest {name} infrastructure")
            require(arm["process"]["exit_code"] == exit_code, f"Jest {name} exit")
            require(not arm["process"].get("timed_out") and not arm["process"].get("spawn_error"),
                    f"Jest {name} process error")
            observations[name] = cases
        baseline = {identity for identity, _ in observations["baseline"]}
        selected = {identity for identity, _ in observations["selective"]}
        full = {identity for identity, _ in observations["independent_full"]}
        failed = {identity for identity, case in observations["independent_full"] if case["status"] == "failed"}
        require(baseline == full and selected <= baseline and failed.isdisjoint(selected), "Jest omission identities")
        require(len(failed) == 1 and next(iter(failed))[0].endswith("/cookie-config.test.ts"),
                "Jest designated security-source guard")
        require(all(path.endswith("/account-setup.test.ts") for path, _ in selected), "Jest selected file")
        require(all(evidence["conditions"].values()), "Jest declared qualification conditions")
        output.append({"repetition": number, "baseline_pass": 8173, "selected_pass": 8,
                       "independent_pass": 8172, "omitted_failures": 1})
    return output


def python_repetitions(root):
    base = root / "recovered/incoming-extension/extracted/snp2027_extension_2026-11-07/outputs/logs/single_repeats"
    output = []
    for seed in (0, 1, 42):
        for subject in ("itsdangerous_expiry", "starlette_trusted_host", "requests_crlf_header"):
            arms = {}
            for name in ("baseline", "native", "full"):
                text = read(base / f"seed_{seed}" / subject / f"{name}.log")
                status = re.search(r"^EXIT:\s*(-?\d+)\s*$", text, re.M)
                require(status, "Python repetition missing process exit")
                calls = re.findall(r"^(\S+::\S+)\s+(PASSED|FAILED|SKIPPED)\b", text, re.M)
                arms[name] = (text, int(status.group(1)), calls)
            require(Counter(outcome for _, outcome in arms["baseline"][2]) == {"PASSED": 3}, "Python baseline")
            require(Counter(outcome for _, outcome in arms["full"][2]) == {"PASSED": 2, "FAILED": 1}, "Python full oracle")
            require({identity for identity, _ in arms["baseline"][2]} ==
                    {identity for identity, _ in arms["full"][2]}, "Python oracle identities")
            require(not arms["native"][2] and "no tests ran" in arms["native"][0], "Python empty native selection")
            require([arms[name][1] for name in ("baseline", "native", "full")] == [0, 0, 1], "Python repetition exits")
            output.append({"seed": seed, "subject": subject, "selected_calls": 0, "oracle_failures": 1})
    return output


def depper(root):
    paths = {
        "windows_installed": "native/current-validation/results/results.json",
        "ubuntu_installed": "hosted/current-validation/artifacts/run-42429376249/native-depper-linux-attempt-1/cases/results.json",
        "ubuntu_local": "hosted/current-validation/artifacts/run-42429562709/native-depper-linux-attempt-1/cases/results.json",
    }
    output = {}
    for environment, relative in paths.items():
        rows = load(root / relative)
        require(len(rows) == 36, f"Depper {environment} row count")
        indexed = {(row["case"], row["condition"], row["mode"]): row for row in rows}
        require(len(indexed) == 36, "Depper duplicate conditions")
        require({row["case"] for row in rows} == {"itsdangerous_expiry", "starlette_trusted_host", "requests_crlf_header"}, "Depper subjects")
        require({row["condition"] for row in rows} == {"baseline_nochange", "benign_comment", "ordinary", "collision"}, "Depper conditions")
        require({row["mode"] for row in rows} == {"native_default", "native_fallback", "full_suite"}, "Depper modes")
        for row in rows:
            observer = row["observer"]
            require(not observer.get("collection_errors") and row.get("valid_execution"), "Depper execution eligibility")
            calls = [item for item in observer["reports"] if item["when"] == "call"]
            if row["mode"] == "full_suite":
                require(len(calls) == 3, "Depper full-oracle calls")
                failures = sum(item["outcome"] == "failed" for item in calls)
                expected = 1 if row["condition"] in ("ordinary", "collision") else 0
                require(failures == expected and row["exit"] == expected, "Depper full oracle")
            if row["condition"] in ("ordinary", "collision") and row["mode"] == "native_default":
                detects = environment == "ubuntu_local" and row["case"] == "starlette_trusted_host"
                require(len(calls) == (2 if detects else 0), "Depper default selected calls")
                require(sum(item["outcome"] == "failed" for item in calls) == int(detects), "Depper default failure")
                require(row["exit"] == int(detects), "Depper default exit")
                if not detects:
                    require(len(observer["skipped_tests"]) == 3, "Depper original setup skips")
            if environment == "ubuntu_local" and row["condition"] == "benign_comment" and row["mode"] == "native_default":
                require(len(calls) == 2 and all(item["outcome"] == "passed" for item in calls), "Depper benign control")
        output[environment] = {"processes": 36}
    output["total_processes"] = 108
    return output


def requests_control(root):
    evidence = load(root / "experiments/fixed-historical-replay-20261111/results-corrected-observer/replay-result.json")
    require(len(evidence["repetitions"]) == 3, "Requests repetitions")
    output = []
    for repetition in evidence["repetitions"]:
        sets = {}
        for name, expected, skips, exit_code in (
                ("baseline", {"passed": 205}, 13, 0),
                ("selective", {"passed": 1, "failed": 1}, 0, 1),
                ("independent_full", {"passed": 204, "failed": 1}, 13, 1)):
            arm = repetition[name]
            require(Counter(call["outcome"] for call in arm["calls"]) == expected, f"Requests {name} calls")
            require(arm["setup_skips"] == skips and arm["process_exit"] == exit_code, f"Requests {name} skips/exits")
            require(arm["infrastructure_eligible"] and not arm["collection_errors"] and not arm["internal_errors"] and arm["noncall_errors"] == 0, "Requests infrastructure")
            sets[name] = {call["nodeid"] for call in arm["calls"]}
        require(sets["baseline"] == sets["independent_full"] and sets["selective"] <= sets["baseline"], "Requests oracle identities")
        for name in ("selective", "independent_full"):
            failed = [call["nodeid"] for call in repetition[name]["calls"] if call["outcome"] == "failed"]
            require(failed == [evidence["security_nodeid"]], "Requests original detecting assertion")
        require(not repetition["qualifying_joint_witness"], "Requests must remain a detection control")
        output.append({"repetition": repetition["repeat"], "baseline_pass": 205, "original_setup_skips": 13,
                       "selected_calls": 2, "selected_failures": 1, "independent_pass": 204, "independent_failures": 1})
    return output


def metadata_faults(root):
    base = root / "artifacts/final-bounded-revision-2026-11-11/raw/integrity/extracted/rts_integrity_2026-11-10"
    java_base = base / "ekstazi_study/results/20261110T212203310997Z"
    java_rows = load(java_base / "results.json")
    require(len(java_rows) == 72, "Java fault matrix count")
    for row in java_rows:
        log = read(java_base / "runs" / row["run_id"] / "stdout.log")
        summaries = re.findall(r"^RESEARCH_RESULT\t(\d+)\t(\d+)\t(\d+)\t(false|true)\s*$", log, re.M)
        require(len(summaries) == 1 and summaries[0][1:] == ("2", "0", "false"), "Java raw fault summary")
        require(len(re.findall(r"^RESEARCH_FAILURE\t", log, re.M)) == 2, "Java raw fault failures")
        require(row["returncode"] == 1 and row["failures"] == 2 and row["regression_detected"] and not row["false_green"], "Java matrix outcome")
    testmon_base = base / "testmon_pilot"
    testmon_all = load(testmon_base / "results.json")
    testmon_rows = [row for row in testmon_all if row["repetition"] in (1, 2, 3)]
    require(len(testmon_rows) == 45, "Testmon fault matrix count")
    statuses = Counter(row["status"] for row in testmon_rows)
    require(statuses == {"test_failure": 39, "runner_error": 6}, "Testmon fault classifications")
    for row in testmon_rows:
        directory = testmon_base / "evidence" / row["run_id"]
        if row["status"] == "runner_error":
            text = read(directory / "stdout.txt") + read(directory / "stderr.txt")
            require(row["exit_code"] == 3 and "DatabaseError" in text and not row["xml_exists"], "Testmon explicit database abort")
        else:
            cases = list(ET.parse(directory / "junit.xml").getroot().iter("testcase"))
            require(sum(case.find("failure") is not None for case in cases) == 2, "Testmon raw JUnit failures")
            require(row["exit_code"] == 1 and row["failures"] == 2, "Testmon detecting outcome")
    wrapper_all = load(base / "project_sample/wrapper_pilot/results.json")
    wrapper_rows = [row for row in wrapper_all if row["scenario"] in
                    ("ordinary_change", "target_metadata_missing", "target_metadata_truncated_50pct")]
    require(len(wrapper_rows) == 45, "Wrapper fault matrix count")
    for row in wrapper_rows:
        log = read(base / "project_sample" / row["log"])
        matches = re.findall(r"^@@RESULT run=(\d+) failures=(\d+) ignored=(\d+)\s*$", log, re.M)
        require(len(matches) == 1 and matches[0][1:] == ("1", "0"), "Wrapper raw summary")
        require(row["returncode"] == 1 and row["failure_count"] == 1 and "@@FAIL " in log, "Wrapper detecting outcome")
    control_counts = [len(load(java_base / "controls.json")), len(testmon_all) - len(testmon_rows),
                      len(wrapper_all) - len(wrapper_rows), len(load(base / "ekstazi_study/maven_validation/results.json"))]
    require(control_counts == [4, 4, 15, 4], "Separate setup/control accounting")
    return {"java_comparisons": 72, "testmon_comparisons": 45, "wrapper_comparisons": 45,
            "total_comparisons": 162, "detecting_completions": 156, "explicit_database_aborts": 6,
            "false_passes": 0, "separate_controls": 27}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Extracted artifact root; defaults to current directory")
    args = parser.parse_args()
    root = args.root.resolve()
    checks = {"validator_original_nonempty": validator, "jest_original_source_guard": jest,
              "python_local_repetitions": python_repetitions, "depper_comparison": depper,
              "requests_original_detection_control": requests_control, "metadata_fault_campaign": metadata_faults}
    result = {"status": "PASS", "mode": "offline retained-record inspection; no subject execution", "checks": {}}
    for name, check in checks.items():
        try:
            result["checks"][name] = {"status": "PASS", "observations": check(root)}
        except (OSError, ValueError, KeyError, TypeError, IndexError, ET.ParseError, VerificationError) as error:
            result["status"] = "FAIL"
            result["checks"][name] = {"status": "FAIL", "error": f"{type(error).__name__}: {error}"}
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
