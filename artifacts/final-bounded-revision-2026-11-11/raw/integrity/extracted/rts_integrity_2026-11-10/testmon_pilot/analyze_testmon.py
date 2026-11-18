#!/usr/bin/env python3
"""Rebuild descriptive summaries and LaTeX from observed testmon records."""
import collections
import csv
import hashlib
import json
from pathlib import Path
import statistics

root = Path(__file__).resolve().parent
results = json.loads((root / "results.json").read_text())
derived = []
for raw in results:
    # The original field name is retained only in immutable raw results. Set
    # subtraction observes nonexecution; it does not identify selection failure
    # when the runner aborts before completing a run.
    r = {k: v for k, v in raw.items() if k != "relevant_omitted_nodeids"}
    oracle = set(r.get("oracle_failing_nodeids", []))
    unexecuted = sorted(oracle - set(r["executed_nodeids"]))
    assessable = r["repetition"] > 0 and r["status"] in ("pass", "test_failure") and r["xml_exists"]
    r["unexecuted_oracle_nodeids"] = unexecuted
    r["omission_assessable"] = assessable
    r["selection_omission_count"] = len(unexecuted) if assessable else None
    r["selection_omitted_nodeids"] = unexecuted if assessable else None
    r["omission_classification_reason"] = "Completed run with oracle and execution evidence" if assessable else "Runner did not complete normally" if r["status"] == "runner_error" else "Control run has no comparison oracle"
    derived.append(r)
(root / "derived_results.json").write_text(json.dumps(derived, indent=2) + "\n")
fields = ["run_id", "strategy", "fault", "repetition", "source_state", "exit_code", "status", "tests", "failures", "errors", "full_suite_fallback", "false_accept", "omission_assessable", "selection_omission_count", "unexecuted_oracle_nodeids", "selection_omitted_nodeids", "omission_classification_reason", "elapsed_s"]
with (root / "derived_results.csv").open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
    w.writeheader()
    for r in derived:
        row = dict(r)
        row["selection_omission_count"] = r["selection_omission_count"] if r["omission_assessable"] else "N/A"
        row["selection_omitted_nodeids"] = json.dumps(r["selection_omitted_nodeids"]) if r["omission_assessable"] else "N/A"
        row["unexecuted_oracle_nodeids"] = json.dumps(r["unexecuted_oracle_nodeids"])
        w.writerow(row)
groups = collections.defaultdict(list)
for r in derived:
    if r["repetition"] > 0:
        groups[(r["fault"], r["strategy"])].append(r)
summaries = []
for (fault, strategy), records in groups.items():
    vectors = {(r["exit_code"], r["tests"], r["failures"], r["full_suite_fallback"]) for r in records}
    summaries.append({
        "fault": fault, "strategy": strategy,
        "repeats": len(records), "identical_discrete_outcomes": len(vectors) == 1,
        "exit_codes": sorted({r["exit_code"] for r in records}),
        "executed_tests": sorted({r["tests"] for r in records}),
        "detected_oracle_failures": sorted({r["oracle_tests_detected"] for r in records}),
        "false_accepts": sum(r["false_accept"] for r in records),
        "runner_errors": sum(r["status"] == "runner_error" for r in records),
        "omission_assessable_runs": sum(r["omission_assessable"] for r in records),
        "selection_omission_count": sorted({r["selection_omission_count"] for r in records}) if all(r["omission_assessable"] for r in records) else None,
        "unexecuted_oracle_counts": sorted({len(r["unexecuted_oracle_nodeids"]) for r in records}),
        "full_suite_fallbacks": sum(r["full_suite_fallback"] for r in records),
        "elapsed_median_s": statistics.median(r["elapsed_s"] for r in records),
        "elapsed_min_s": min(r["elapsed_s"] for r in records),
        "elapsed_max_s": max(r["elapsed_s"] for r in records),
    })
fault_modes = sorted({fault for fault, strategy in groups if fault != "none"})
baseline_test_count = next(r["tests"] for r in results if r["run_id"] == "00_cold_baseline")
oracle_failure_count = len(next(r["failing_nodeids"] for r in results if r["run_id"] == "03_full_changed_oracle"))
analysis = {
    "fixture_count": 1,
    "designed_fault_modes": len(fault_modes),
    "nonfault_control_conditions": len({fault for fault, strategy in groups if fault == "none"}),
    "control_executions": sum(r["repetition"] == 0 for r in results),
    "comparison_executions": sum(r["repetition"] > 0 for r in results),
    "source_state_hash_count_among_candidates": len({json.dumps(r["source_hashes"], sort_keys=True) for r in results if r["source_state"] == "candidate"}),
    "test_inventory_hash_count": len({json.dumps(r["test_hashes"], sort_keys=True) for r in results}),
    "summaries": summaries,
    "selection_omission_assessable_comparison_runs": sum(r["omission_assessable"] for r in derived),
    "runner_error_comparison_runs": sum(r["status"] == "runner_error" for r in derived if r["repetition"] > 0),
    "omission_definition": "Assess only completed comparison runs. A runner error has omission_assessable=false and selection_omission_count=null. Unexecuted oracle test IDs remain observations, not evidence of omission by RTS selection.",
    "raw_field_note": "Raw results preserve historical relevant_omitted_nodeids values for auditability. Consult derived_results for their corrected interpretation; the raw field is set subtraction, including tests never executed after runner initialization errors.",
    "inference": "Descriptive counts only. Deterministic repeats are not independent trials; no confidence interval or prevalence estimate is calculated.",
    "timing_caution": "Fixed execution order, parallel research processes, startup cost and a tiny suite make elapsed times unsuitable for production performance comparisons.",
}
repeat_counts = sorted({s["repeats"] for s in summaries})
repeat_label = str(repeat_counts[0]) if len(repeat_counts) == 1 else f"{repeat_counts[0]}--{repeat_counts[-1]}"
comparison_rows = [r for r in derived if r["repetition"] > 0]
error_rows = [r for r in comparison_rows if r["status"] == "runner_error"]
completed_rows = [r for r in comparison_rows if r["omission_assessable"]]
detected_rows = [r for r in completed_rows if set(r["oracle_failing_nodeids"]).issubset(r["failing_nodeids"])]
zero_omission_rows = [r for r in completed_rows if r["selection_omission_count"] == 0]
false_accepts = sum(r["false_accept"] for r in comparison_rows)
analysis["repeats_per_condition"] = repeat_counts
analysis["completed_runs_detecting_all_oracle_failures"] = len(detected_rows)
analysis["false_accepts"] = false_accepts
(root / "analysis.json").write_text(json.dumps(analysis, indent=2) + "\n")
esc = lambda x: str(x).replace("_", r"\_")
caption = r"\caption{Observed testmon integrity-fault outcomes in the synthetic fixture. Each row comprises " + repeat_label + r" deterministic repeats. Selection omissions are N/A when the runner aborts; unexecuted tests then do not establish omission by selection.}"
lines = [r"\begin{table}[t]", r"\centering", caption, r"\label{tab:testmon-integrity-pilot}", r"\begin{tabular}{llrrrrr}", r"\hline", r"Fault & Strategy & Tests & Failures & Exit & Fallback & Omissions \\", r"\hline"]
for s in summaries:
    if not s["identical_discrete_outcomes"]:
        raise RuntimeError("Table requires explicit variable-outcome formatting")
    row = next(r for r in derived if r["repetition"] > 0 and r["fault"] == s["fault"] and r["strategy"] == s["strategy"])
    omissions = row["selection_omission_count"] if row["omission_assessable"] else "N/A"
    lines.append(f"{esc(s['fault'])} & {esc(s['strategy'])} & {row['tests']} & {row['failures']} & {row['exit_code']} & {'yes' if row['full_suite_fallback'] else 'no'} & {omissions} " + r"\\")
lines += [r"\hline", r"\end{tabular}", r"\end{table}", ""]
(root / "table_testmon.tex").write_text("\n".join(lines))
old_summary = json.loads((root / "summary.json").read_text())
for row in old_summary["rows"]:
    s = next(s for s in summaries if s["fault"] == row["fault"] and s["strategy"] == row["strategy"])
    row["omission_assessable_runs"] = s["omission_assessable_runs"]
    row["selection_omission_count"] = s["selection_omission_count"]
old_summary["omission_definition"] = analysis["omission_definition"]
old_summary["repetitions"] = repeat_counts[0] if len(repeat_counts) == 1 else repeat_counts
(root / "summary.json").write_text(json.dumps(old_summary, indent=2) + "\n")
md = ["# pytest-testmon synthetic integrity pilot", "", "## Scope", "",
      f"Actual local execution of pytest-testmon 2.3.0 against {baseline_test_count} synthetic tests. The full-suite regression oracle has {oracle_failure_count} unchanged arithmetic tests that fail after a harmless +1 arithmetic mutation. A changed-but-passing label module provides an independent changed test. Another test uses an unchanged module.", "",
      "All metadata faults are controlled simulations. No dependency rows or fingerprints were selectively edited. No real security vulnerability or attacker bypass was introduced.", "",
      "## Observed controls", "", "| Run | Exit | Tests | Failures | Status |", "|---|---:|---:|---:|---|"]
for r in results[:4]:
    md.append(f"| {r['run_id']} | {r['exit_code']} | {r['tests']} | {r['failures']} | {r['status']} |")
md += ["", "## Fault comparisons", "", f"There were {repeat_label} deterministic repeats per condition, with identical discrete outcomes within every condition. Counts below describe one run, not pooled independent trials.", "", "| Fault | Strategy | Tests | Failures | Exit | Fallback | Selection omissions |", "|---|---|---:|---:|---:|---|---:|"]
for s in summaries:
    r = next(r for r in derived if r["repetition"] > 0 and r["fault"] == s["fault"] and r["strategy"] == s["strategy"])
    count = r["selection_omission_count"] if r["omission_assessable"] else "N/A"
    md.append(f"| {r['fault']} | {r['strategy']} | {r['tests']} | {r['failures']} | {r['exit_code']} | {'yes' if r['full_suite_fallback'] else 'no'} | {count} |")
md += ["", "## Outcome classification", "",
       f"The {len(error_rows)} comparison executions classified as runner errors aborted during testmon/SQLite initialization. Their oracle-failing tests were unexecuted. That observation does not establish that RTS selection omitted them. For these rows, `omission_assessable` is false and `selection_omission_count` is null (N/A in tables). They are runner errors, not successful pipelines or completed defect-detection runs.", "",
       f"Of the {len(completed_rows)} completed comparison executions, {len(detected_rows)} detected all arithmetic oracle failures and {len(zero_omission_rows)} had zero selection omissions. There were {false_accepts} false acceptances among {len(comparison_rows)} comparison executions. The overall comparison count includes {len(error_rows)} explicit runner errors and must not be stated as {len(comparison_rows)} successful defect detections.", "",
       "Original `results.json`, `results.csv`, and per-run result files are preserved byte-for-byte. Their historical `relevant_omitted_nodeids` field was raw set subtraction, not a causal selection classification. Use `derived_results.json` or `derived_results.csv` for corrected classifications. They retain those unexecuted IDs as `unexecuted_oracle_nodeids`. Historical derived outputs and hashes are in `historical_before_classification_fix/`.", "",
       "## Validity limits", "",
       "- Full-suite execution disables testmon. Each comparison restores the same cache generation at the same absolute path.",
       "- All test files remain byte-identical; candidate source hashes also match across all changed-fixture executions.",
       "- Verification assumes a separately trusted manifest. It checks cache bytes and test inventory; it does not authenticate provenance or protect against verification/use races.",
       f"- There is one synthetic fixture and {len(fault_modes)} designed fault modes. Deterministic repetitions are repeatability checks, not independent attack trials; no prevalence estimate or inferential confidence interval is justified.",
       "- Runtimes are descriptive only. Startup overhead, fixed ordering, and concurrent work prevent a production performance comparison.",
       "- Unmeasured: attacker capabilities, production cache exposure, larger suites, parallel workers, other versions, and adversarial dependency graphs.", "",
       "## Reproduction", "",
       f"Copy the two Python scripts and requirements files into a fresh directory, create a Python 3.12 virtual environment, install `requirements-lock.txt`, run `python run_testmon_pilot.py --repetitions {repeat_counts[0]}`, then run `python analyze_testmon.py`. The runner accepts any positive repeat count and refuses to overwrite existing experiment directories. The analyzer derives report counts from the observed records and applies the explicit runner-error classification without rerunning native tests.", ""]
(root / "RESULTS.md").write_text("\n".join(md))
manifest = {}
for p in sorted(root.rglob("*")):
    if not p.is_file() or "venv" in p.parts or "__pycache__" in p.parts or "work" in p.parts or p.name == "artifact_manifest.json":
        continue
    manifest[str(p.relative_to(root))] = {"bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
(root / "artifact_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(json.dumps({"runs": len(results), "identical_outcomes_in_all_repeats": all(s['identical_discrete_outcomes'] for s in summaries), "candidate_source_hash_sets": analysis['source_state_hash_count_among_candidates'], "test_hash_sets": analysis['test_inventory_hash_count']}))
