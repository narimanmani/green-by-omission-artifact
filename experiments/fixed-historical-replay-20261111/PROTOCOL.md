# Fixed historical regression replay

Frozen before execution. One fixed historical source change is evaluated; no candidate search or optimization is performed.

Subject: Requests v2.32.5, upstream b25c87d7cb8d6a18a37fa12442b5f883f9e41741.

Complete evaluation test set T: the entire unchanged upstream tests/test_utils.py, including its original platform skips. This is a defined evaluation oracle, not the entire Requests suite. Named original security assertion: TestGetNetrcAuth::test_not_vulnerable_to_bad_url_parsing. It uses temporary synthetic data and sends no network request.

Candidate: exact inverse of the single-file source change in official fix 96ba401c1296ab1dda74a2365ef36d88f7d144ef, applied once to the pinned source. Tests and configuration remain byte-identical. No fingerprint manipulation, forced selection, dummy tests, or outcome-dependent variants.

Three fresh repetitions. Each extracts pristine source, runs native testmon on baseline to establish passing tests and dependency state, snapshots the closed database, applies the fixed historical source change, runs native selection at the same absolute path, then independently runs all T without loading testmon on identical source bytes. The independent run cannot update selector state. Pytest 8.4.2 respects upstream pytest<9; testmon 2.3.0. Retain upstream doctest configuration. Pin all dependencies and retain wheel hashes.

Record actual call outcomes (collection is not execution), setup/teardown errors, skips, selected/deselected identities, process exits, import origin, source/test/configuration hashes and cache hashes. Qualifying joint result requires passing original baseline, at least one original selective call and selective success, plus an original security assertion failure omitted from selection in independent execution of identical candidate. Native detection is a valid negative result. Infrastructure errors are not security failures.

Separate image: pinned official Python base, offline wheel installation, no runtime network, no host mounts, sockets, devices, credentials or published ports. Non-root user, read-only root, dropped capabilities, no-new-privileges, bounded temporary storage and CPU/memory/PID limits. Inspect boundary before starting. No hosted CI or agent/model invocation occurs inside the image.

This is a local replay of a documented historical regression, not a new upstream vulnerability, prevalence estimate or validation of the paper's complete adversarial mechanism.

Public provenance: https://github.com/psf/requests/commit/96ba401c1296ab1dda74a2365ef36d88f7d144ef and https://github.com/psf/requests/security/advisories/GHSA-9hjg-9r4m-mvj7 .
