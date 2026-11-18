# Private disposable research validation

This repository contains isolated copies of three published Python libraries with research-injected source revisions and unchanged security tests. It is used only to measure test selection and protected-PR behavior.

The original libraries are not asserted to contain these injected regressions. No production application, production repository, or deployment credential is involved. Keep the repository and its artifacts private.

The initial setup PR runs the complete baseline suites. Later experimental PRs change exactly one application source file from that frozen baseline. `testmon-required` is the required native selective check; `full-suite-diagnostic` records the independent full-suite outcome on the identical head revision.

The independent-selector workflow runs published pytest-depper with fresh Git histories and baseline, benign-comment, ordinary-change and collision-change controls. A result must be interpreted from actual logs and selected tests, including negative comparisons.
Disposable private research validation. No production data.
