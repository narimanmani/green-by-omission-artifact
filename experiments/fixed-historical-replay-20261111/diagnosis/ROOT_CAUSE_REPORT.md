# Root cause of the detecting native-selection outcome

**Finding: the recorded historical candidate changes the native function fingerprint. It therefore does not meet the fingerprint-preservation precondition of the paper's omission mechanism.** Native selection retaining the detecting original security assertion is consistent with ordinary change detection. No remaining execution or measurement defect was identified in the corrected runs.

## Direct diagnostic measurement

The published pytest-testmon 2.3.0 parser and fingerprint matcher analyzed the exact baseline and candidate source snapshots from the completed experiment, using the same pinned Python 3.13.13 environment. Subject source and tests were parsed, not executed. Both source SHA256 values match the original execution records. No new candidate variant, test-set change or selector setting was introduced.

| Native property for get_netrc_auth | Baseline | Recorded candidate |
|---|---:|---:|
| Signed CRC32 of the native function-block representation | 1276617766 | -1676748471 |
| Baseline function fingerprint matches this module | Yes | No |

The native AST-derived representations also differ. The candidate restores substantive operations inside get_netrc_auth; this is not merely a comment change. Both unchanged original methods, TestGetNetrcAuth.test_works and TestGetNetrcAuth.test_not_vulnerable_to_bad_url_parsing, directly call that function.

## Connection to recorded execution

All three corrected fresh-baseline repetitions executed exactly those two tests under native selection. The valid-input assertion passed and the security assertion failed. Native selection reported 216 deselected items and exited 1. The baseline had 205 passing calls, 13 original setup skips and no failures. The independent 205-call oracle on identical candidate bytes reproduced the security failure. Prior-failure rerunning cannot explain these selections because the baseline was passing.

This diagnostic directly measures fingerprint mismatch for the saved source bytes. It does not export or independently reconstruct the original temporary per-test SQLite fingerprints. Attribution of the complete historical selection decision combines the native fingerprint measurement, published implementation, unchanged direct test calls and saved execution records; it is not presented as an instrumented trace of the original database query.

## Research consequence and correction

The original replay deliberately evaluated one public historical source change without optimization. A historical security regression alone does not imply that its detecting original test will be omitted. The relevant eligibility distinction is now explicit:

- This is a valid original-security-test ordinary-change detection control.
- It is ineligible as a demonstration of fingerprint-preserving omission: native fingerprint preservation is false.
- It is not a nonempty selective false pass: native selection fails and includes the detecting assertion.
- No setup adjustment or repetition of the unchanged case can establish the missing observation already contradicted by these records. A new outcome would require a separate, independently qualifying experimental case and evidence, or the limitation must remain.

The first observer-incompatible attempt remains excluded and preserved separately. Its repair did not change the candidate or test set. No further recorder error was found in the corrected experiment.

The diagnostic container was inspected before starting: network disabled, non-root user, read-only root, no host mounts/devices/credentials/ports, all capabilities dropped and bounded resources. Its 18 boundary checks passed. [Measured result](result.json), [execution receipt](execution.json), [diagnostic program](diagnose_saved_case.py).

This report adds a causal eligibility check; it does not add a new false-pass result, alter the completed study or update the live manuscript.
