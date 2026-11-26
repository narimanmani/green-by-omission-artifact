# Green by Omission — Anonymous Reviewer Artifact

This package accompanies **Green by Omission: Subverting CI Security Gates Through Adversarial Test Selection**. It contains retained experimental inputs, source snapshots, reports, logs, native selection state, protocols, and verification scripts. It is an anonymous export of private research records, prepared for peer review. It is not a record of a new experiment, an independent reproduction, a published deposit, or completed maintainer disclosure.

## Start here

Use Python 3.10 or newer, from this directory:

```text
python verify_package.py
python verify_results.py
```

Both commands are offline and use only the Python standard library. They read evidence; they do not run application code, tests, containers, cloud workflows, or installation scripts. Expected failures inside recorded experimental logs are scientific outcomes, not a failure of package verification. See `REPRODUCE.md` for runtime entrypoints and prerequisites.

The same payload can be supplied as a Git repository or ZIP. The root `.gitattributes` preserves file bytes across operating systems; the integrity verifier ignores the enclosing repository's `.git` administrative directory. An anonymous sharing service should serve a frozen snapshot without further rewriting already anonymized contents: additional substitutions can invalidate source fingerprints and the supplied checksums. The paper should link to the anonymous snapshot rather than its source repository.

## Evidence map

| Paper evidence | Package location | Interpretation |
|---|---|---|
| Three Python constructions and nine baseline-restored technical repetitions | `recovered/incoming-extension/extracted/snp2027_extension_2026-11-07/` | Research-authored three-test oracles; empty-selection false passes; ordinary and comment controls retained |
| Six hosted ordinary/preserving conditions | `hosted/current-validation/` and `hosted/checkout/` | Required selective status differs from overall workflow outcome; no experimental pull request merged |
| Nonempty hosted replay with protected-main baseline | `experiments/hosted-verification-20261111/`, `hosted/protected-main-source/`, and `hosted/protected-candidate/` | Exact reviewed fixture; two accounts share an operator; code-owner approval still required; closed unmerged |
| Independent pytest-depper comparison | `native/current-validation/` and the two Linux native-depper runs under `hosted/current-validation/artifacts/` | 108 processes in three environments; ordinary omissions distinguish dependency limitations from fingerprint preservation |
| Canonical Ekstazi fixture and initial original Validator oracle | `artifacts/final-bounded-revision-2026-11-11/remote-java/canonical/` | Controlled fixture plus initial 40-test upstream oracle; earlier detecting extension and alternative fingerprint retained |
| Ineligible Java harness | `artifacts/final-bounded-revision-2026-11-11/remote-java/ineligible/` | Failed incremental-selection qualification, not positive omission evidence |
| Expanded original Validator case | `experiments/validator-original-nonempty-fixed-20261112/` | 60 original cases; 20 selected passes; two omitted original URL failures in three repetitions |
| Original Requests security-test control | `experiments/fixed-historical-replay-20261111/` | Detecting control; corrected observer results, original failed observer attempt, setup skips, and diagnosis retained separately |
| Original Jest cookie-configuration guard | `experiments/wxyc-fixed-historical-replay-20261112/` | 8,173 baseline passes; eight selected passes; 8,172 independent passes and one omitted failing guard in three repetitions |
| Separate metadata-fault campaign, Apache configuration frame | `artifacts/final-bounded-revision-2026-11-11/raw/integrity/extracted/rts_integrity_2026-11-10/` | 162 fault comparisons and 27 separate setup/control invocations; 156 detections, six explicit errors, no false pass |
| Static checksum–AST comparison audit | `experiments/guard-granularity-audit-20261123/` | Saved comparison predicates and flags for ten cases, including the file-level miss and block-level flag on the retained nonempty hosted case |
| Ten-project feasibility screen | `artifacts/final-bounded-revision-2026-11-11/raw/feasibility-42763093847/` | Two qualify under the frozen screen; nonqualifying cases retained; not a vulnerability prevalence estimate |
| 24-project configuration frame | `artifacts/final-bounded-revision-2026-11-11/raw/prevalence-d2c384c/` | Recorded convenience observations; historical response and per-repository binding limitations remain |

`CLAIMS.json` provides a compact machine-readable index. Earlier timestamps and historical reports describe the state at their creation; the current scope is summarized here. In particular, older audit statements that a nonempty original-test example had not been established precede the expanded Validator and Jest experiments. They must not override those later records.

## Boundaries that matter

The expanded Validator example deliberately adds a behavior-preserving credit-card edit to a known URL-regression candidate to make selection nonempty. Its oracle comprises three unchanged original test classes, not the full upstream suite. It lacks its own matched ordinary-change arm. Its three executions are technical repetitions of one constructed revision.

The Jest case replays a previously documented affected-test limitation: a test reads production source without importing it. Upstream maintainers documented the omission and moved continuous integration to the full unit suite. This case concerns a static cookie-configuration source guard, not a runtime cross-site request forgery exploit, and does not preserve fingerprints. Public upstream attribution and primary documentary snapshots are retained.

The hosted replay does not demonstrate unauthorized acceptance, independent human review, arbitrary-candidate isolation, or a production compromise. These experiments establish existence under the studied conditions, not discovery effort, deployment prevalence, or a comprehensive defense.

## Integrity, anonymization, and availability

`MANIFEST.json` records SHA-256 and size for each exported payload file. `source_sha256` refers to the retained input before anonymization; `sha256` refers to the bytes actually supplied here. `SHA256SUMS.txt` also covers the manifest. Historical embedded hashes are not silently rewritten when identifying metadata is removed. See `ANONYMIZATION.md` for the exact distinction.

Author/account identifiers, personal machine paths, private repository locations, and research Git histories are removed or replaced. Public upstream identities, commits, source attribution, licenses, and technical case identifiers are retained. The Jest upstream Git seed is a documented exception: public source objects and references are retained for its exact baseline, while machine-local reflogs and fetch metadata are removed.

Installed environments, Docker image layers, and complete package registries are not included. Some dependency wheels and the specific rebuilt locked Jest dependency are retained; runtime reconstruction can require external dependencies. Requests' temporary SQLite bytes were not originally exported. Hosted historical policies cannot be recreated by local execution. No claim of a fully offline runtime reproduction is made.

See `LICENSE_NOTES.md` before redistributing third-party material. Zenodo title, description, and upload guidance are supplied beside the ZIP, not hidden inside this package.
