# Original-project security-test historical control

**Result: native testmon detects this fixed historical regression. No nonempty selective false pass was observed.** The same outcome occurred in three fresh-baseline repetitions of one fixed case; these are repeatability checks, not independent cases or a population estimate.

| Arm | Actual test calls | Passed | Failed | Original platform skips | Process outcome |
|---|---:|---:|---:|---:|---|
| Unmodified baseline | 205 | 205 | 0 | 13 | Success |
| Native selection on fixed candidate | 2 | 1 | 1 | 0 | Failure: security regression detected |
| Independent complete evaluation oracle on identical candidate | 205 | 204 | 1 | 13 | Failure: same security assertion |

The complete evaluation oracle is the entire unchanged upstream `tests/test_utils.py` (218 collected items), not the whole Requests project suite. All original tests and configuration remain unchanged. Thirteen original tests are skipped during setup because they require Windows or Python 2 cStringIO; no skipped item is counted as an executed call. Native selection reports 216 deselected items and executes two actual calls. Synthetic deselection items are counted without inventing per-test identities.

The failing original upstream assertion is `TestGetNetrcAuth::test_not_vulnerable_to_bad_url_parsing`. It passes on the baseline and fails in both candidate arms. The other selected test, `TestGetNetrcAuth::test_works`, passes. Consequently, the failing assertion is **selected**, not omitted.

## Scientific interpretation

This control establishes that an unchanged upstream security assertion detects a documented historical authentication regression, and that native selection retains that assertion for this ordinary source change. It strengthens original-test oracle provenance and provides a negative control for selection failure. It does not establish a nonempty original-security-test false pass, fingerprint preservation, a new upstream vulnerability, a hosted approval bypass, or selector safety in general.

The deliberately modified subject is Requests v2.32.5 at `b25c87d7cb8d6a18a37fa12442b5f883f9e41741`, with the sole source change from [official fix 96ba401](https://github.com/psf/requests/commit/96ba401c1296ab1dda74a2365ef36d88f7d144ef) reversed. The [maintainer advisory](https://github.com/psf/requests/security/advisories/GHSA-9hjg-9r4m-mvj7) establishes historical security relevance. This is a replay in a deliberately modified local copy; the pinned unmodified release contains the fix. No alternative candidate was evaluated.

Runtime: Python 3.13.13, pytest 8.4.2, pytest-testmon 2.3.0, coverage 7.11.0. Pytest 8 respects upstream's pytest <9 requirement; upstream doctest configuration remains active. Exact wheel versions and hashes are in requirements-hashed.txt and input-manifest.json. Autoload is disabled in all arms; the same observation plugin is loaded throughout, and only native arms load the testmon plugin. Each repetition starts with an empty database; selective execution uses the baseline's exact source path and dependency state. The independent run does not load testmon or change its database.

## Evidence binding

- Original test-file SHA256: `5ef1d612edb55d4629fa8c3c6867bae0bf69050b951da9954927e42e48b88ff1`.
- Candidate source-tree SHA256 across all 132 original archive files: `6729b4bafe16e78a01b200024e963bfdd0c20c345c17f16bdc1566cfaed399ca`. This is an experiment-defined canonical hash of sorted path-to-SHA256 mappings, not a Git commit.
- Exactly one original file changes: src/requests/utils.py. The same candidate-tree digest holds before and after selective and independent execution, and across all three repetitions.
- Import-origin records resolve Requests to the candidate checkout, not an installed alternate copy. Baseline database snapshots remain unchanged; independent execution leaves the post-selective working database unchanged.
- Corrected raw observations: [replay-result.json](results-corrected-observer/replay-result.json); compact counts: [summary.json](results-corrected-observer/summary.json); container and execution receipt: [execution.json](results-corrected-observer/execution.json).
- Runtime networking is disabled, the root filesystem is read-only, and no host mounts, devices, credentials or Docker socket are exposed. All 18 host boundary checks passed before execution. The test uses only temporary synthetic credentials and URL parsing; no request is sent.

The initial attempt had an observation-plugin error and is ineligible as selective-execution evidence. Its raw records are retained with an explicit eligibility correction; see OBSERVER_CORRECTION.md. Only the corrected run above is used for the scientific result.

Independent read-only verification: [INDEPENDENT_REPLAY_AUDIT.json](INDEPENDENT_REPLAY_AUDIT.json). The audit recomputed the saved outcomes and source identity; it did not execute candidates. Temporary database immutability is verified by the runtime, not by a separate post-exit database rehash.

## Manuscript-ready wording

As an original-test negative control, we replayed the inverse of a documented Requests authentication fix in a pinned v2.32.5 checkout while retaining the entire unchanged upstream utility-test module. All 205 applicable tests passed at baseline, with 13 upstream platform skips. Native testmon executed two tests, including the original security assertion, and detected its failure; independent execution of the same 205-test oracle on identical candidate bytes exposed the same assertion failure. Three clean-baseline repetitions agreed. This validates the detecting oracle and ordinary-change control but does not establish a nonempty false pass with original upstream security tests.
