# Five-library feasibility pilot and repository-configuration audit

## Status and scope

This directory contains measurements obtained on 10 November 2026.

- **Executed:** 60 native JVM experiment runs using Ekstazi 5.3.0, JUnit 4.13.2, and JDK 8u432.
- **Executed:** Five isolated synthetic applications calling released, unmodified Apache Commons libraries.
- **Simulated:** Fixed deletion and fixed 50% byte truncation of each fixture's generated `SubjectTest` dependency metadata.
- **Inspected:** 20 immutable repository snapshots, 156 repository configuration files, and seven transitive Maven parent POMs.
- **Not executed:** The five upstream projects' own regression suites, historical upstream changes, live CI workflows, or security-control bypasses.
- **Not measured:** Population deployment prevalence, branch protection, required-check enforcement, or actual activation of optional RTS profiles.

The five-library experiment is a **synthetic wrapper feasibility pilot**. It is not equivalent to validating Ekstazi against each project's native regression suite. All source mutations concern generated wrappers and generated tests' dependency caches. Published library artifacts remain unchanged.

## Native experimental observations

Each fixture contains three one-method test classes: `SubjectTest`, `ControlTest`, and `UntouchedTest`.

| Library | Version | Cold baseline executed/failed | Warm baseline | Ordinary change RTS | Missing metadata RTS | 50%-truncated metadata RTS | Guard on either fault | Full suite after change |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Commons CLI | 1.6.0 | 3/0 | 0/0 | 2/1 | 2/1 | 2/1 | 3/1 | 3/1 |
| Commons CSV | 1.10.0 | 3/0 | 0/0 | 2/1 | 2/1 | 2/1 | 3/1 | 3/1 |
| Commons Codec | 1.16.0 | 3/0 | 0/0 | 2/1 | 2/1 | 2/1 | 3/1 | 3/1 |
| Commons IO | 2.15.0 | 3/0 | 0/0 | 2/1 | 2/1 | 2/1 | 3/1 | 3/1 |
| Commons Lang | 3.14.0 | 3/0 | 0/0 | 2/1 | 2/1 | 2/1 | 3/1 | 3/1 |

Entries show test methods executed/test methods failed. Each full baseline also executed three tests and passed. Every changed-case failure is the expected synthetic `SubjectTest#valueMatches` assertion failure. The semantically unchanged control mutation causes `ControlTest#valueMatches` to execute and pass. `UntouchedTest` is omitted by standard RTS in the changed cases.

Across the 15 project-by-scenario cases:

| Arm | Relevant failures detected | Relevant tests omitted | Integrity fallbacks | Test-method executions / opportunities |
| --- | --- | --- | --- | --- |
| Standard RTS | 15/15 | 0/15 | 0 | 30/45 |
| SHA-256 fail-closed guard | 15/15 | 0/15 | 10 | 40/45 |
| Full suite | 15/15 | 0/15 | 0 | 45/45 |

No false-passing result or relevant-test omission was observed in these fixed fault cases. The guard increased execution in ten faulted cases; this pilot did not demonstrate a detection improvement because unguarded Ekstazi also detected each seeded regression.

These counts describe a finite chosen corpus. They do not estimate the probability of omissions in production. The five wrappers share a test structure; their outcomes are not independent replications of varied real-project behavior. We therefore report no confidence intervals or significance tests.

### Protocol

1. Compile the generated wrapper, independent control, untouched class, and three unchanged JUnit tests.
2. Run the native Ekstazi agent with an empty dependency cache; then run unchanged to measure warm selection; run without the agent for the full baseline.
3. Freeze the generated metadata directory and an external SHA-256 manifest.
4. Change only the synthetic `Subject.value()` return value by appending `!`. Change the control's implementation while preserving its output. Recompile at the same absolute paths.
5. Verify that every test source and compiled test class has the same SHA-256 as before the change.
6. Before **every arm**, restore the identical trusted metadata snapshot. Apply either no fault, complete deletion of `pilot.SubjectTest.clz`, or retention of exactly the first floor(length/2) bytes of that generated file.
7. Run standard RTS; the manifest guard with full-suite fallback on any mismatch; and the agent-free full suite. Record exit code, actual executed/failed method identities, complete logs, and wall-clock duration.

Fault locations and truncation fractions are fixed before selection results. The scripts do not search for favorable faults, alter hash values to preserve fingerprints, modify upstream code, or attack a remote system.

The guard's manifest lives outside the metadata directory under a locally controlled trusted directory. This simulates a protected integrity record. No deployed signing, remote attestation, or immutable CI storage was evaluated. A digest manifest cannot establish that otherwise well-formed dependency metadata is semantically complete.

## Static repository-configuration observations

The predetermined sample contains these Apache Commons components: BCEL, BeanUtils, CLI, Codec, Collections, Compress, Configuration, Crypto, CSV, DBCP, DBUtils, Digester, Email, Exec, IO, Lang, Math, Numbers, Pool, and Text.

The sample is a purposive convenience sample. Its common organization and shared Maven parents limit diversity. Search results had already suggested Ekstazi references in Math and Numbers before the sample was frozen; the study does not claim blinded selection.

| Inspected indicator | Repositories |
| --- | --- |
| Root POM declares an optional Ekstazi profile | 2/20 |
| Any inspected workflow explicitly mentions Ekstazi | 0/20 |
| Primary Maven workflow declares a pull-request trigger | 20/20 |
| Primary workflow declares `contents: read` | 20/20 |
| All external actions in primary workflow use 40-hex commit pins | 20/20 |
| Primary checkout steps disable credential persistence | 20/20 |
| Primary workflow explicitly uses `actions/cache` for Maven dependencies | 16/20 |
| Actual RTS deployment or required status checks | Unmeasured |

The two optional declarations are:

- **Commons Math:** Ekstazi Maven plugin **4.4.0**, activated when property `ekstazi` is present; not active by default.
- **Commons Numbers:** Ekstazi Maven plugin **5.3.0**, activated when property `ekstazi` is present; not active by default.

The inspected workflows contain no explicit activation of those profiles. Seven transitive parent POMs contain none of the searched RTS signatures. This is not proof that RTS cannot be invoked through a local developer command, an uninspected script, an external workflow, or a different environment.

The primary CI workflows also invoke ordinary Maven lifecycle commands or their declared default goals. Configuration alone cannot show that these jobs ran, that every test was included, or that merging requires their success. Dependency caches do not imply that an RTS dependency database is cached.

### Immutable primary sources for the positive findings

- Commons Math POM: <https://github.com/apache/commons-math/blob/36cefd500d2b6a193bd81654665944db1bb1aaed/pom.xml>
- Commons Numbers POM: <https://github.com/apache/commons-numbers/blob/e6845beaca307b09bb02ae5ae625c63345bce130/pom.xml>
- The complete 20-repository source mapping is in `frozen_repository_manifest.json` and `repository_audit_summary.json`.

## Reproduction

The experiment itself makes no network requests. Its prerequisites are JDK 8u432-b06, `org.ekstazi.core-5.3.0.jar`, `junit-4.13.2.jar`, `hamcrest-core-1.3.jar`, and the five versioned library jars. Exact byte hashes are in `wrapper_pilot/environment.json` and `pilot_artifact_manifest.json`.

```bash
python3 run_wrapper_pilots.py --toolchain /absolute/path/to/toolchain --artifact-dir /absolute/path/to/pilot_artifacts
python3 analyze_results.py
```

Replaying the source audit requires read-only GitHub/Maven Central network access and Python `PyYAML` for the summarizer. The existing immutable manifest is reused unless `--refresh` is explicitly provided:

```bash
python3 audit_repositories.py --manifest frozen_repository_manifest.json
python3 summarize_audit.py
```

The audit downloads commit-pinned archives and inspects configuration text. It executes no downloaded project code, build script, repository hook, or workflow. Full upstream archives are intermediate data; extracted audited files, hashes, and source URLs are sufficient to check reported observations.

## Evidence map

| File or directory | Content |
| --- | --- |
| `run_wrapper_pilots.py` | Fixed synthetic fixtures, unchanged test oracle, fault definitions, native-agent runs, manifest defense |
| `wrapper_pilot/protocol.json` | Frozen experimental design and scope |
| `wrapper_pilot/results.json` | Detailed 60-run records, commands, actual test identities, input metadata hashes |
| `wrapper_pilot/results.csv` | Tabular run results |
| `wrapper_pilot/logs/` | Complete per-run stdout/stderr |
| `wrapper_pilot/trusted/` | Baseline dependency metadata and trusted manifest files |
| `wrapper_pilot/work/` | Final synthetic source/classes and generated cache state |
| `wrapper_pilot/statistics.json` | Computed finite-corpus counts and limitations |
| `wrapper_pilot/table_wrappers.tex` | Publication-ready LaTeX experiment table |
| `pilot_artifact_manifest.json` | Exact Maven coordinates, artifact/source hashes, release Git commits |
| `pilot_selection.csv` | Five-library selection table |
| `sampling_protocol.json` | Sampling scope, selection bias, and unmeasured quantities |
| `frozen_repository_manifest.json` | Immutable source commits and resolution evidence |
| `repository_audit_raw.json` | File hashes, matched lines, retrieval metadata, source/test file counts |
| `snapshots/` | Exact configuration files inspected |
| `parent_pom_manifest.json`, `parent_poms/` | Inspected transitive Maven parent POMs |
| `repository_audit_summary.json`, `.csv` | Parsed profile and workflow observations |
| `audit_totals.json` | Computed audit counts |
| `table_configuration_audit.tex` | Publication-ready LaTeX audit table |

## Validity limits and untested hypotheses

- **Application scope:** Library calls in small generated wrappers do not represent the libraries' native test suites, complex dependency graphs, multi-module builds, or real commit histories.
- **Tool integration:** The native JUnit agent was tested. Maven plugin behavior, JUnit 5 integration, other JDKs, and different Ekstazi options remain untested here.
- **Fault scope:** Only deletion and deterministic half-file truncation were injected in this pilot. Other malformed, stale, semantically incomplete, or internally inconsistent states could behave differently.
- **Repetitions:** One execution per case and arm supports feasibility observations, not flakiness estimates or performance inference. Timing is recorded for auditability and is not a speed benchmark.
- **Guard scope:** SHA-256 verification detected introduced byte changes under a simulated trusted-manifest assumption. Its production storage, freshness guarantees, race resistance, and semantic completeness are untested.
- **Sampling:** Twenty repositories from one organization with shared parents cannot support ecosystem-wide RTS deployment prevalence. Optional configuration is distinct from CI activation.
- **Observation scope:** Branch protection, required checks, actual workflow histories, private settings, and external workflow contents were not queried.
- **Temporal scope:** Static CI inspection uses contemporary pinned default-branch snapshots. Dynamic wrapper execution uses explicitly older Java-8-compatible published library versions. They are distinct evidence sets and must not be conflated.

The current evidence supports successful baseline operation, ordinary regression detection, and conservative behavior under the two chosen metadata faults in these wrappers. It does not establish a general soundness guarantee or an exploitable RTS weakness.
