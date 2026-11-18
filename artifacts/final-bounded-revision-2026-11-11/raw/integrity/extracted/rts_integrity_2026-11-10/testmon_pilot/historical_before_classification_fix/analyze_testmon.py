#!/usr/bin/env python3
"""Rebuild descriptive summaries and LaTeX from observed testmon records."""
import collections
import hashlib
import json
from pathlib import Path
import statistics

root = Path(__file__).resolve().parent
results = json.loads((root / "results.json").read_text())
groups = collections.defaultdict(list)
for r in results:
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
        "full_suite_fallbacks": sum(r["full_suite_fallback"] for r in records),
        "elapsed_median_s": statistics.median(r["elapsed_s"] for r in records),
        "elapsed_min_s": min(r["elapsed_s"] for r in records),
        "elapsed_max_s": max(r["elapsed_s"] for r in records),
    })
analysis = {
    "fixture_count": 1,
    "designed_fault_modes": 4,
    "nonfault_control_conditions": 1,
    "control_executions": sum(r["repetition"] == 0 for r in results),
    "comparison_executions": sum(r["repetition"] > 0 for r in results),
    "source_state_hash_count_among_candidates": len({json.dumps(r["source_hashes"], sort_keys=True) for r in results if r["source_state"] == "candidate"}),
    "test_inventory_hash_count": len({json.dumps(r["test_hashes"], sort_keys=True) for r in results}),
    "summaries": summaries,
    "inference": "Descriptive counts only. Deterministic repeats are not independent trials; no confidence interval or prevalence estimate is calculated.",
    "timing_caution": "Fixed execution order, parallel research processes, startup cost and a tiny suite make elapsed times unsuitable for production performance comparisons.",
}
(root / "analysis.json").write_text(json.dumps(analysis, indent=2) + "\n")
esc = lambda x: str(x).replace("_", r"\_")
lines = [r"\begin{table}[t]", r"\centering", r"\caption{Observed testmon integrity-fault outcomes in one synthetic fixture. Each row is reproduced three times. Error indicates a nonzero runner failure, not a successful pipeline.}", r"\label{tab:testmon-integrity-pilot}", r"\begin{tabular}{llrrrr}", r"\hline", r"Fault & Strategy & Tests & Failures & Exit & Fallback \\", r"\hline"]
for s in summaries:
    if not s["identical_discrete_outcomes"]:
        raise RuntimeError("Table requires explicit variable-outcome formatting")
    row = next(r for r in results if r["repetition"] > 0 and r["fault"] == s["fault"] and r["strategy"] == s["strategy"])
    lines.append(f"{esc(s['fault'])} & {esc(s['strategy'])} & {row['tests']} & {row['failures']} & {row['exit_code']} & {'yes' if row['full_suite_fallback'] else 'no'} " + r"\\")
lines += [r"\hline", r"\end{tabular}", r"\end{table}", ""]
(root / "table_testmon.tex").write_text("\n".join(lines))
manifest = {}
for p in sorted(root.rglob("*")):
    if not p.is_file() or "venv" in p.parts or "__pycache__" in p.parts or "work" in p.parts or p.name == "artifact_manifest.json":
        continue
    manifest[str(p.relative_to(root))] = {"bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
(root / "artifact_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(json.dumps({"runs": len(results), "identical_outcomes_in_all_repeats": all(s['identical_discrete_outcomes'] for s in summaries), "candidate_source_hash_sets": analysis['source_state_hash_count_among_candidates'], "test_hash_sets": analysis['test_inventory_hash_count']}))
