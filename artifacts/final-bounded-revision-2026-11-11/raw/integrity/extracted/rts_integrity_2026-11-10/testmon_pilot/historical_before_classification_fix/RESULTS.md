# pytest-testmon synthetic integrity pilot

## Scope

Actual local execution of pytest-testmon 2.3.0 against four synthetic tests. Two unchanged arithmetic tests fail after a harmless +1 arithmetic mutation. A changed-but-passing label module keeps an independent changed test available. A fourth test uses an unchanged module.

All cache faults are simulations of missing/corrupted metadata. No dependency rows or fingerprints were selectively edited. No real security vulnerability or attacker bypass was introduced.

## Observed controls

| Run | Exit | Tests | Failures | Status |
|---|---:|---:|---:|---|
| 00_cold_baseline | 0 | 4 | 0 | pass |
| 01_warm_unchanged | 0 | 0 | 0 | pass |
| 02_full_baseline | 0 | 4 | 0 | pass |
| 03_full_changed_oracle | 1 | 4 | 2 | test_failure |

## Fault comparison (3 deterministic repeats per condition)

| Fault | Strategy | Tests per run | Failures per run | Status | False accepts | Fallbacks |
|---|---|---|---|---|---:|---:|
| none | standard_rts | [3] | [2] | test_failure | 0 / 3 | 0 / 3 |
| none | fail_closed | [3] | [2] | test_failure | 0 / 3 | 0 / 3 |
| none | full_suite | [4] | [2] | test_failure | 0 / 3 | 0 / 3 |
| missing | standard_rts | [4] | [2] | test_failure | 0 / 3 | 0 / 3 |
| missing | fail_closed | [4] | [2] | test_failure | 0 / 3 | 3 / 3 |
| missing | full_suite | [4] | [2] | test_failure | 0 / 3 | 0 / 3 |
| empty | standard_rts | [4] | [2] | test_failure | 0 / 3 | 0 / 3 |
| empty | fail_closed | [4] | [2] | test_failure | 0 / 3 | 3 / 3 |
| empty | full_suite | [4] | [2] | test_failure | 0 / 3 | 0 / 3 |
| half_truncated | standard_rts | [0] | [0] | runner_error | 0 / 3 | 0 / 3 |
| half_truncated | fail_closed | [4] | [2] | test_failure | 0 / 3 | 3 / 3 |
| half_truncated | full_suite | [4] | [2] | test_failure | 0 / 3 | 0 / 3 |
| garbage | standard_rts | [0] | [0] | runner_error | 0 / 3 | 0 / 3 |
| garbage | fail_closed | [4] | [2] | test_failure | 0 / 3 | 3 / 3 |
| garbage | full_suite | [4] | [2] | test_failure | 0 / 3 | 0 / 3 |

## Interpretation limits

- `runner_error` means the test process did not complete normally. It is not a passing pipeline or successful defect detection.
- Zero collected tests and their actual exit code are reported without normalization.
- The independent full-suite oracle disables testmon. Cache state is reset at the same absolute path before every comparison.
- Tests remain byte-identical throughout; raw JUnit XML and per-run source/cache hashes are archived.
- SHA-256 verification assumes a trusted, separately stored manifest and unchanged test inventory. It does not authenticate metadata if that manifest is also replaceable, protect against a verification/use race, or establish source-to-cache semantic correctness.
- No confidence interval for attack success is appropriate: there is one designed fixture, five fault conditions, and deterministic repeats.
- Runtimes include Python/pytest startup and local filesystem effects. They are descriptive, not a production performance benchmark.
- Unmeasured: attacker write capability, production cache exposure, larger suites, parallel workers, other Python/testmon versions, and malicious dependency graphs.

## Reproduction

Create a fresh directory containing this script and requirements.txt, install the pinned requirements in a Python 3.12 virtual environment, and run `python run_testmon_pilot.py --repetitions 3`. The script refuses to overwrite previous run directories.
