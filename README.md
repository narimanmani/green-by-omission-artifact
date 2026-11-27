# Green by Omission: When Selective CI Skips Security Tests

Reviewer evidence for the SECUTE manuscript, revision `068d134d169b592d9e9158c8d6cb003768b9d80a`.

## Verify the results

Extract the ZIP. From the extracted directory, run the following command with Python 3.8 or later.

```text
python verify_results.py
```

The script reads `observations.json`, rebuilds the reported counts, and prints the tables and figure totals. It uses the Python standard library and runs offline. A missing, duplicate, or inconsistent comparison causes a failure. A successful run ends with `All recorded-outcome checks passed.`

## Evidence in the archive

| Manuscript location | JSON records | Retained sources used to prepare the records |
| --- | --- | --- |
| Table 5 and §5.1 | `local_python`, `local_ordinary_controls` | Local repetition records, ordinary controls, and the numerical audit of actual calls |
| Figure 3 and §5.2 | `hosted_paired`, `hosted_replay` | Hosted paired-run results, the replay's execution and status records, and the later branch-protection readback |
| Table 6 and §5.3.1 | `java_controls`, `validator_60` | Canonical Java outcomes and per-arm results from three fresh Validator repetitions |
| §5.3.2 and Table 7 | `requests_ordinary`, `jest_original` | Corrected Requests replay records and the three eligible Jest repetition records |
| Figures 4 and 5 | `independent_python`, `hosted_paired` | The 108-run pytest-depper matrix and the six hosted testmon conditions |
| Table 8 and §5.4 | `feasibility_pilot`, `configuration_audits` | The ten archived setup outcomes, the search-ranked audit batches, and the 20-repository Apache Commons audit |
| Table 9 and §§4.6.1, 6.3 | `local_guard`, `static_guard`, `hosted_replay`, `validator_raw_digests_differ`, `recorded_seconds` | Runtime guard results, ten saved static decisions, and retained Java and hosted timing records |
| Table 10 and §5.5.2 | `metadata_comparisons`, `metadata_controls` | Native Ekstazi, native testmon, and Java-wrapper result matrices, with the separate archived controls |

Each `executed` count is the number of test cases that ran. `failed` counts executed tests with failing assertions. `exit_code` is the recorded process exit, including successful exits without test execution. `skipped` is included where the corresponding comparison records skips separately. A missing pilot count (`null`) marks an unavailable count after an invalid baseline or setup. The configuration-audit row numbers are anonymous. In the metadata matrix, `detecting_failure` records whether a designated assertion exposed the regression. `runner_error` records a separate execution or database error. The verifier derives the outcome column and counts the 27 setup and control records separately.

## Validator test outcomes and hosted CI timeline

- [Validator test outcomes](validator-test-outcomes.csv) support Table 6 and §5.3.1. Each row records one executed test case from the archived Surefire reports for the baseline, selective, or independent arm. The class and method identify the same test across arms and repetitions. For each repetition, the independent run has two failures whose identities are absent from the selective run.
- [Hosted CI timeline](hosted-ci-timeline.json) supports Table 3 and §5.2.2. The timestamps and outcomes come from the saved GitHub run, status, and pull request records and the archived test summaries. The branch-protection entry gives the date of the later verification of the policy.

## Scope of verification

The observations are selected fields from retained records. The archive supports numerical verification and recomputation of the manuscript's reported outcomes. It contains no candidate revisions, source snapshots, CI workflows, or live experiment harnesses.

The 60-test Validator configuration has no matched ordinary-change control. Its three repetitions are technical repeats of a fixed case. The Requests original-test result concerns an ordinary regression. The hosted replay used one reviewed fixture. Its review requirement comes from a later policy readback, and its pull request closed unmerged. The static guard data contain recorded decisions, with no runtime measurement of the block-level guard. The declared-provenance condition tests a label change. The campaign did not restore an authentic stale baseline. Configuration rows describe the inspected records and cannot establish use of a required live check. Timing values are single retained observations with different boundaries, as described in the manuscript.
