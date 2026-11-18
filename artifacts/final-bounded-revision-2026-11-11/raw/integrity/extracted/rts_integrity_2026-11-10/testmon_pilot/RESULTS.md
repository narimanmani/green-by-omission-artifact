# pytest-testmon synthetic integrity pilot

## Scope

Actual local execution of pytest-testmon 2.3.0 against 4 synthetic tests. The full-suite regression oracle has 2 unchanged arithmetic tests that fail after a harmless +1 arithmetic mutation. A changed-but-passing label module provides an independent changed test. Another test uses an unchanged module.

All metadata faults are controlled simulations. No dependency rows or fingerprints were selectively edited. No real security vulnerability or attacker bypass was introduced.

## Observed controls

| Run | Exit | Tests | Failures | Status |
|---|---:|---:|---:|---|
| 00_cold_baseline | 0 | 4 | 0 | pass |
| 01_warm_unchanged | 0 | 0 | 0 | pass |
| 02_full_baseline | 0 | 4 | 0 | pass |
| 03_full_changed_oracle | 1 | 4 | 2 | test_failure |

## Fault comparisons

There were 3 deterministic repeats per condition, with identical discrete outcomes within every condition. Counts below describe one run, not pooled independent trials.

| Fault | Strategy | Tests | Failures | Exit | Fallback | Selection omissions |
|---|---|---:|---:|---:|---|---:|
| none | standard_rts | 3 | 2 | 1 | no | 0 |
| none | fail_closed | 3 | 2 | 1 | no | 0 |
| none | full_suite | 4 | 2 | 1 | no | 0 |
| missing | standard_rts | 4 | 2 | 1 | no | 0 |
| missing | fail_closed | 4 | 2 | 1 | yes | 0 |
| missing | full_suite | 4 | 2 | 1 | no | 0 |
| empty | standard_rts | 4 | 2 | 1 | no | 0 |
| empty | fail_closed | 4 | 2 | 1 | yes | 0 |
| empty | full_suite | 4 | 2 | 1 | no | 0 |
| half_truncated | standard_rts | 0 | 0 | 3 | no | N/A |
| half_truncated | fail_closed | 4 | 2 | 1 | yes | 0 |
| half_truncated | full_suite | 4 | 2 | 1 | no | 0 |
| garbage | standard_rts | 0 | 0 | 3 | no | N/A |
| garbage | fail_closed | 4 | 2 | 1 | yes | 0 |
| garbage | full_suite | 4 | 2 | 1 | no | 0 |

## Outcome classification

The 6 comparison executions classified as runner errors aborted during testmon/SQLite initialization. Their oracle-failing tests were unexecuted. That observation does not establish that RTS selection omitted them. For these rows, `omission_assessable` is false and `selection_omission_count` is null (N/A in tables). They are runner errors, not successful pipelines or completed defect-detection runs.

Of the 39 completed comparison executions, 39 detected all arithmetic oracle failures and 39 had zero selection omissions. There were 0 false acceptances among 45 comparison executions. The overall comparison count includes 6 explicit runner errors and must not be stated as 45 successful defect detections.

Original `results.json`, `results.csv`, and per-run result files are preserved byte-for-byte. Their historical `relevant_omitted_nodeids` field was raw set subtraction, not a causal selection classification. Use `derived_results.json` or `derived_results.csv` for corrected classifications. They retain those unexecuted IDs as `unexecuted_oracle_nodeids`. Historical derived outputs and hashes are in `historical_before_classification_fix/`.

## Validity limits

- Full-suite execution disables testmon. Each comparison restores the same cache generation at the same absolute path.
- All test files remain byte-identical; candidate source hashes also match across all changed-fixture executions.
- Verification assumes a separately trusted manifest. It checks cache bytes and test inventory; it does not authenticate provenance or protect against verification/use races.
- There is one synthetic fixture and 4 designed fault modes. Deterministic repetitions are repeatability checks, not independent attack trials; no prevalence estimate or inferential confidence interval is justified.
- Runtimes are descriptive only. Startup overhead, fixed ordering, and concurrent work prevent a production performance comparison.
- Unmeasured: attacker capabilities, production cache exposure, larger suites, parallel workers, other versions, and adversarial dependency graphs.

## Reproduction

Copy the two Python scripts and requirements files into a fresh directory, create a Python 3.12 virtual environment, install `requirements-lock.txt`, run `python run_testmon_pilot.py --repetitions 3`, then run `python analyze_testmon.py`. The runner accepts any positive repeat count and refuses to overwrite existing experiment directories. The analyzer derives report counts from the observed records and applies the explicit runner-error classification without rerunning native tests.
