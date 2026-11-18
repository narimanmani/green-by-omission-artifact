SP2027 10-project native RTS baseline eligibility pilot, preregistered prior to execution on 2026-11-09.

Five Python projects and five Java projects are purposefully selected (NOT a population sample). Immutable upstream commit SHAs are pinned in manifest.json. Each separate hosted runner clones only public upstream code into an isolated temporary directory. No public upstream PRs, no upstream CI edits, no production operations.

Python: Python 3.12, pytest 9.0.2, pytest-testmon 2.3.0. Use the lexicographically first 3 native test_*.py files to identify a test, install package editable, run native baseline and no-change. Java: Temurin 21, Maven, Ekstazi 5.3.0; insert Maven profile ONLY into isolated checkout, try first 3 native JUnit *Test classes. Record all failed installs, no-change executions, test outcomes and timings. Cap each step to 215 seconds; 25-min overall job.

This pilot establishes build and baseline feasibility ONLY. No attack generation, no behavioral regression injection, no full-suite oracle or defense claim is made for these 10 projects. Preserve raw artifacts, record failures, and continue only with eligible projects in a separately preregistered attack study. The independent prior Apache Commons Validator 1.7 experiment is distinct.


## Protocol amendment: zero-test acceptance bug (recorded before rerun)

The original 10-job run 42762237595 found that four Maven baselines were falsely classified as passing because Surefire exited zero with `Tests run: 0`, primarily on abstract test classes. These remain permanently recorded as invalid initial measurements. The amended runner excludes class names beginning `Abstract` or `Base`, deterministically tries the first 8 remaining lexicographically ordered original JUnit classes, and *requires* at least one non-skipped test and no test failures before declaring a valid baseline. The rerun retains the initial fixed upstream SHA and five-per-language cohort. This is a transparent bug fix and **changes the original first-three candidate budget**, so do not pool the two attempts as a pre-registered study without qualification. The No-change phase now records the exact count, treating zero selected tests as expected when test selection works. Provenance artifacts now exclude copied dependency environments/checkout bytes to avoid large archives; exact commit and logs remain.


## Second transparent amendment: explicit-test selection may prevent deselection

Review of initial and corrected runs showed the no-change step still ran its explicitly named tests: Python passed a specific `file::nodeid`, Java supplied `-Dtest=Class`. These forms may force execution and are invalid to establish native incremental selectivity. The amended Python diagnostic invokes `pytest --testmon` on the selected **whole file**; the amended Java runner uses the Maven Surefire profile `<includes>` and a custom property `-Dsp2027.test.class`, not `-Dtest`. We now require a nonzero passing baseline followed by zero passing tests on the unchanged step before calling the selector active. Persist all previous run artifacts and do not pool these changed procedures into an unqualified single preregistered statistical sample. This remains an isolated feasibility study, not an adversarial attack trial.
