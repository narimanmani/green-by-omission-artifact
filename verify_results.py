"""Recompute the reported outcomes from the included observations."""

import json
from collections import Counter, defaultdict
from itertools import product
from pathlib import Path


SUBJECTS = ("ItsDangerous", "Starlette", "Requests")
CHANGE_CONDITIONS = ("ordinary", "fingerprint-preserving")
STRATEGIES = ("Standard RTS", "Manifest-verified escalation", "Unconditional complete oracle")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def signature(record):
    """Executed, failed, process exit, and recorded skips."""
    values = tuple(record[key] for key in ("executed", "failed", "exit_code")) + (record.get("skipped", 0),)
    require(all(type(value) is int and value >= 0 for value in values), "Invalid execution counts or exit")
    require(values[1] <= values[0], "Failed tests exceed executed tests")
    return values


def indexed(rows, keys, expected_keys, title):
    index = {tuple(row[key] for key in keys): row for row in rows}
    require(len(index) == len(rows) and set(index) == set(expected_keys), f"Incomplete or duplicate rows: {title}")
    return index


def table(title, columns, rows):
    print(f"\n{title}")
    print("| " + " | ".join(columns) + " |")
    print("| " + " | ".join("---" for _ in columns) + " |")
    for row in rows:
        print("| " + " | ".join(map(str, row)) + " |")


def describe(record):
    executed, failed, exit_code, skipped = signature(record)
    value = f"{executed} executed, {failed} failed, exit {exit_code}"
    return value + (f", {skipped} skipped" if skipped else "")


def local_and_hosted(data):
    local = indexed(data["local_python"], ("subject", "hash_seed"), product(SUBJECTS, (0, 1, 42)), "local Python")
    ordinary = indexed(data["local_ordinary_controls"], ("subject",), product(SUBJECTS), "local ordinary controls")
    summary = []
    for subject in SUBJECTS:
        runs = [row for (case, seed), row in local.items() if case == subject]
        for row in runs:
            require(signature(row["baseline"]) == (3, 0, 0, 0), "Local baseline differs")
            require(signature(row["selective"]) == (0, 0, 0, 0), "Local preserving selection differs")
            require(signature(row["independent"]) == (3, 1, 1, 0), "Local independent run differs")
        exit_code = ordinary[subject,]["selective_exit_code"]
        require(exit_code == 1, "Local ordinary regression should be detected")
        summary.append((subject, exit_code, sum(row["selective"]["exit_code"] == 0 for row in runs),
                        sum(row["independent"]["failed"] > 0 for row in runs)))
    table("Table 5 - local testmon", ("Subject", "Ordinary exit", "Empty selective passes", "Independent detections"), summary)

    paired = indexed(data["hosted_paired"], ("subject", "condition"), product(SUBJECTS, CHANGE_CONDITIONS), "hosted paired")
    summary = []
    for (subject, condition), row in paired.items():
        preserving = condition == "fingerprint-preserving"
        expected = (0, 0, 0, 0) if preserving else (2, 1, 1, 0)
        require(signature(row["selective"]) == expected, "Hosted selective result differs")
        require(signature(row["independent"]) == (3, 1, 1, 0), "Hosted independent result differs")
        require(row["merge_control_enabled"] is preserving, "Hosted merge-control state differs")
        require(row["overall_workflow_conclusion"] == "failure", "Hosted workflow conclusion differs")
        summary.append((subject, condition, describe(row["selective"]), describe(row["independent"]),
                        "enabled" if row["merge_control_enabled"] else "disabled"))
    table("Figure 3 - hosted paired controls", ("Subject", "Condition", "Selective", "Independent", "Merge control"), summary)

    replay = data["hosted_replay"]
    arms = {"baseline": (3, 0, 0, 0), "selective": (1, 0, 0, 0),
            "independent": (3, 1, 1, 0), "diagnostic": (3, 1, 1, 0)}
    require(all(signature(replay[arm]) == expected for arm, expected in arms.items()), "Hosted nonempty replay differs")
    require(replay["required_status"] == "success" and replay["structural_change_flagged"] is True
            and replay["failed_jobs"] == 2, "Hosted status or diagnostics differ")
    require(replay["code_owner_review_in_later_readback"] is True and replay["pull_request_state"] == "closed"
            and replay["pull_request_merged"] is False, "Hosted review or merge evidence differs")
    table("Hosted nonempty replay", ("Arm", "Result"), [(arm, describe(replay[arm])) for arm in arms])
    print("Required check succeeded. Later readback required code-owner review. The PR closed unmerged.")
    return paired


def repeated_arms(rows, label, expected):
    indexed(rows, ("repetition",), [(1,), (2,), (3,)], label)
    for row in rows:
        for arm, signature_expected in expected.items():
            require(signature(row[arm]) == signature_expected, f"{label}: {arm} differs")
    table(label, ("Arm", "Result in each of three repetitions"),
          [(arm, describe(rows[0][arm])) for arm in expected])


def java_and_original_tests(data):
    repeated_arms(data["validator_60"], "Table 6 - Validator 60-test case",
                  {"baseline": (60, 0, 0, 0), "unchanged": (0, 0, 0, 0),
                   "selective": (20, 0, 0, 0), "independent": (60, 2, 1, 0)})
    require(all(row["omitted_failing_original_tests"] == 2 for row in data["validator_60"]),
            "Validator omitted-test counts differ")
    print("The 60-test configuration lacks its own matched ordinary-change control.")

    fixture = {
        "baseline": (3, 0, 0), "unchanged": (0, 0, 0), "ordinary": (2, 1, 1),
        "fingerprint-preserving": (0, 0, 0), "independent": (3, 1, 1),
        "nonempty variant": (1, 0, 0), "independent nonempty variant": (3, 1, 1),
    }
    validator_40 = {
        "baseline": (40, 0, 0), "unchanged": (0, 0, 0), "ordinary": (33, 2, 1),
        "fingerprint-preserving": (0, 0, 0), "independent": (40, 2, 1),
        "nonempty variant": (40, 2, 1), "independent nonempty variant": (40, 2, 1),
        "MD5 baseline": (40, 0, 0), "MD5 comparison": (33, 2, 1),
    }
    expected = {
        (subject, condition): outcome
        for subject, arms in [("Controlled Java fixture", fixture), ("Validator 40-test", validator_40)]
        for condition, outcome in arms.items()
    }
    controls = indexed(data["java_controls"], ("subject", "condition"), expected, "Java controls")
    for key, row in controls.items():
        require(signature(row)[:3] == expected[key], f"Java control differs: {key}")
    table("Table 6 - controlled Java and Validator 40-test comparisons", ("Subject", "Arm", "Outcome"),
          [(subject, condition, describe(row)) for (subject, condition), row in controls.items()])

    repeated_arms(data["requests_ordinary"], "Requests original-test ordinary regression",
                  {"baseline": (205, 0, 0, 13), "selective": (2, 1, 1, 0),
                   "independent": (205, 1, 1, 13)})
    repeated_arms(data["jest_original"], "Table 7 - Jest original source guard",
                  {"baseline": (8173, 0, 0, 0), "selective": (8, 0, 0, 0),
                   "independent": (8173, 1, 1, 0)})


def independent_selector(data, hosted):
    preferred = "Ubuntu, copied subjects only"
    environments = ("Windows, additional subject distributions", "Ubuntu, additional subject distributions", preferred)
    conditions = ("unchanged", "comment-only") + CHANGE_CONDITIONS
    modes = ("default selection", "fallback enabled", "independent")
    records = indexed(data["independent_python"], ("environment", "subject", "condition", "mode"),
                      product(environments, SUBJECTS, conditions, modes), "independent Python selector")
    for (environment, subject, condition, mode), row in records.items():
        executed, failed, exit_code, skipped = signature(row)
        if mode == "independent":
            require(executed == 3 and (failed, exit_code) == ((1, 1) if condition in CHANGE_CONDITIONS else (0, 0)),
                    "Independent Python oracle differs")
        if mode == "default selection" and condition in CHANGE_CONDITIONS and environment != preferred:
            require((executed, failed, exit_code, skipped) == (0, 0, 0, 3), "Installed-distribution case differs")
        if mode == "default selection" and condition == "comment-only" and environment == preferred:
            require((executed, failed, exit_code) == (2, 0, 0), "Comment-only control differs")

    values = []
    for subject in SUBJECTS:
        ordinary = [records[preferred, subject, "ordinary", mode] for mode in modes]
        preserving = [records[preferred, subject, "fingerprint-preserving", mode] for mode in modes]
        require([signature(row) for row in ordinary] == [signature(row) for row in preserving],
                "Paired independent-selector cases differ")
        expected_default = (2, 1, 1) if subject == "Starlette" else (0, 0, 0)
        expected_fallback = (2, 1, 1) if subject == "Starlette" else (3, 1, 1)
        require([signature(row)[:3] for row in ordinary] == [expected_default, expected_fallback, (3, 1, 1)],
                "Ubuntu comparison differs")
        values.append((subject, *(describe(row) for row in ordinary)))

    table("Figure 4 - pytest-depper on Ubuntu with copied subjects only", ("Subject",) + modes, values)
    detections = [sum(row[mode]["failed"] > 0 for row in hosted.values()) for mode in ("selective", "independent")]
    detections += [
        sum(records[preferred, subject, condition, mode]["failed"] > 0
            for subject, condition in product(SUBJECTS, CHANGE_CONDITIONS))
        for mode in modes
    ]
    require(detections == [3, 6, 2, 6, 6], "Figure 5 detection counts differ")
    table("Figure 5 - execution policies", ("Policy", "Detections", "Conditions"),
          [(name, value, 6) for name, value in zip(("Hosted testmon", "Hosted complete oracle") + modes, detections)])
    print(f"Verified {len(records)} independent-selector runs across three environments.")


def feasibility_and_configurations(data):
    pilot = data["feasibility_pilot"]
    require(len(pilot) == 10 and len({row["subject"] for row in pilot}) == 10, "Expected ten pilot subjects")
    verdicts = Counter()
    values = []
    for row in pilot:
        baseline, unchanged = row["baseline_executed"], row["unchanged_executed"]
        if baseline is None:
            require(unchanged is None, "Invalid baseline paired with an unchanged count")
            outcome = "No valid baseline"
        else:
            require(type(baseline) is int and baseline > 0 and type(unchanged) is int and unchanged >= 0,
                    "Invalid pilot test counts")
            outcome = "Screen met" if unchanged == 0 else "No deselection"
        verdicts[outcome] += 1
        values.append((row["subject"], baseline if baseline is not None else "-",
                       unchanged if unchanged is not None else "-", outcome))
    require(verdicts == {"Screen met": 2, "No deselection": 3, "No valid baseline": 5},
            "Pilot totals differ")
    table("Table 8 - upstream-test feasibility screen", ("Subject", "Baseline", "Unchanged", "Outcome"), values)

    audits = data["configuration_audits"]
    search = indexed(audits["search_ranked"], ("language", "row"), product(("python", "java"), range(1, 13)),
                     "24-repository configuration audit")
    apache = indexed(audits["apache_commons"], ("row",), product(range(1, 21)), "Apache Commons configuration audit")
    workflows = sum(row["has_workflow_path"] for row in search.values())
    mentions = sum(row["indexed_selector_mentions"] for row in search.values())
    profiles = sum(row["optional_ekstazi_profile"] for row in apache.values())
    require((workflows, mentions, profiles) == (19, 0, 2), "Configuration-audit totals differ")
    print(f"\nConfiguration audit | {len(search)} repositories, {workflows} workflow paths present, {mentions} indexed matches")
    print(f"Apache Commons | {len(apache)} repositories, {profiles} with optional Ekstazi profiles")


def defenses_and_timings(data):
    runtime = indexed(data["local_guard"], ("subject", "condition"),
                      product(SUBJECTS, ("fingerprint-preserving", "comment-only")), "local guard")
    positive = [row for (subject, condition), row in runtime.items() if condition == "fingerprint-preserving"]
    comments = [row for (subject, condition), row in runtime.items() if condition == "comment-only"]
    require(all(row["flagged"] is True and row["regression_detected"] is True and row["fallback_executed"] == 3
                and row["fallback_exit_code"] == 1 for row in positive), "Local runtime fallback differs")
    require(all(row["flagged"] is False for row in comments), "Local comment-only result differs")
    require(data["validator_raw_digests_differ"] is True, "Validator raw-byte comparison differs")
    print(f"\nTable 9 - local runtime guard flagged {len(positive)} cases and the oracle detected each regression.")
    print(f"The {len(comments)} comment-only controls did not trigger the local guard.")
    print("The hosted runtime diagnostic, native MD5, and Java raw-byte comparison are separate observations.")

    cases = indexed(data["static_guard"], ("row",), product(range(1, 11)), "static guard decisions")
    totals = Counter((row["condition"], row["file_flagged"], row["block_flagged"]) for row in cases.values())
    require(totals == {("empty-selection", True, True): 3, ("ordinary-regression", False, False): 3,
                       ("comment-only", False, False): 3, ("hosted-nonempty", False, True): 1},
            "Static guard decisions differ")
    table("Table 9 - saved static guard decisions", ("Condition", "File flagged", "Block flagged", "Records"),
          [(category, file_flagged, block_flagged, count)
           for (category, file_flagged, block_flagged), count in totals.items()])

    timings = data["recorded_seconds"]
    expected = {
        "Java fixture construction stage": 12.3783,
        "Validator construction stage": 11.7938,
        "Hosted replay selective process": 0.743,
        "Hosted replay independent process": 0.666,
        "Hosted replay AST scan": 0.023,
    }
    require(set(timings) == set(expected), "Incomplete timing records")
    for name, value in timings.items():
        precision = 4 if "construction" in name else 3
        require(round(value, precision) == expected[name], f"Timing differs: {name}")
    table("Recorded timings", ("Measurement", "Seconds"), timings.items())


def metadata_campaign(data):
    summary = Counter()
    matrix = defaultdict(dict)
    for row in data["metadata_comparisons"]:
        executed, failed, exit_code, _ = signature(row)
        strategy = row["strategy"]
        require(strategy in STRATEGIES, "Unknown execution strategy")
        if row["runner_error"]:
            require(not row["detecting_failure"] and exit_code != 0, "Runner error has an inconsistent result")
            outcome = "runner error"
        elif row["detecting_failure"]:
            require(failed > 0 and executed > 0 and exit_code != 0, "Missing detecting execution")
            outcome = "detection"
        else:
            require(exit_code == 0 and failed == 0, "Unclassified comparison")
            outcome = "false pass"

        key = (row["cohort"], row["subject"], row["condition"], row["repetition"])
        require(strategy not in matrix[key], "Duplicate comparison")
        matrix[key][strategy] = outcome, row["fallback"]
        summary[strategy, outcome] += 1

    require(all(set(group) == set(STRATEGIES) for group in matrix.values()), "Each condition needs all three strategies")
    require(Counter(key[0] for key in matrix) ==
            {"Native Ekstazi": 24, "Native testmon": 15, "Java library wrappers": 15}, "Incorrect campaign denominators")
    errors = [(key, group) for key, group in matrix.items() if group[STRATEGIES[0]][0] == "runner error"]
    require(len(errors) == 6 and all(key[0] == "Native testmon" and group[STRATEGIES[1]] == ("detection", True)
                                     for key, group in errors), "Error and fallback evidence differs")

    values = []
    for strategy in STRATEGIES:
        detected, error, false_pass = (summary[strategy, label] for label in ("detection", "runner error", "false pass"))
        values.append((strategy, detected + error + false_pass, detected, error, false_pass))
    require([row[1:] for row in values] == [(54, 48, 6, 0), (54, 54, 0, 0), (54, 54, 0, 0)],
            "Strategy outcome counts differ")
    totals = tuple(sum(row[column] for row in values) for column in range(1, 5))
    table("Table 10 - metadata-fault comparisons", ("Strategy", "Comparisons", "Detect", "Error", "False pass"),
          values + [("Total",) + totals])

    controls = data["metadata_controls"]
    require(Counter(row["cohort"] for row in controls) ==
            {"Native testmon": 4, "Native Ekstazi": 4, "Maven integration": 4, "Java library wrappers": 15},
            "Control count differs")
    for row in controls:
        signature(row)
    print(f"The {len(controls)} setup and control runs are outside the comparison denominator.")


def main():
    observations = Path(__file__).with_name("observations.json")
    data = json.loads(observations.read_text(encoding="utf-8"))
    print(f"Recorded-outcome verification for manuscript revision {data['manuscript_revision']}")
    hosted = local_and_hosted(data)
    java_and_original_tests(data)
    independent_selector(data, hosted)
    feasibility_and_configurations(data)
    defenses_and_timings(data)
    metadata_campaign(data)
    print("\nAll recorded-outcome checks passed.")


if __name__ == "__main__":
    try:
        main()
    except (KeyError, ValueError, OSError) as error:
        raise SystemExit(f"Verification failed. {error}") from None
