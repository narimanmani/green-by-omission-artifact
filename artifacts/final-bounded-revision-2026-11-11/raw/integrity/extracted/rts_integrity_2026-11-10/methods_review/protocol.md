# Local RTS metadata-integrity study: protocol and interpretation

Status: protocol prepared on 2026-11-10. This document contains no experimental results. Native runs, if completed, must be reported from the accompanying execution records. The historical primary sources cited below explain the design; they do not establish the behavior of Ekstazi 5.3.0 under the proposed faults.

## 1. Scope and questions

All executable experiments use synthetic applications and fixtures in an isolated local environment. Source changes alter simple arithmetic or formatting behavior. They do not add security vulnerabilities. Metadata faults represent missing, damaged, incomplete, or incorrectly restored local cache state. No checksum collisions, fingerprint-preserving changes, exploit payloads, external service calls, or changes to third-party CI are needed.

- RQ1: Does the installed Ekstazi 5.3.0 select the expected tests after an ordinary harmless source change when its baseline metadata is intact?
- RQ2: Under named and recorded cache fault simulations, does native execution rerun relevant tests, omit them, or stop with an error?
- RQ3: Does an independently trusted metadata-integrity gate detect those injected faults and invoke the same full-suite oracle?
- RQ4: What is visible about RTS configuration and CI safeguards in a fixed repository sample? This is a separate observational question. Repository inspection alone does not establish deployed behavior.

An executable failure under a simulated condition is a measured observation of that simulation. It does not establish that an attacker can create that condition in a protected production environment.

## 2. Experimental units and immutable inputs

The primary unit is a unique tuple `(fixture, ordinary source modification, fault scenario)`. Strategy is paired within that tuple. Repeated executions of the same tuple assess repeatability and timing only; they are not independent application samples.

Pin and record:

- Ekstazi coordinates and the SHA-256 digest of the actual JAR used.
- JDK vendor/version, Java bytecode target, build tool/version, test engine/version, operating system, and complete invocation.
- Original and modified source hashes; test-source hashes before and after each case.
- Trusted baseline metadata snapshot, file names, sizes, and hashes.
- The configuration and dependency lock state, where available.
- Fault operation, relative target path, and before/after hash. These are fixture-scoped operations with no externally supplied target.
- Process return code, standard output/error, test execution evidence, and elapsed time.

Any unavailable dependency or incompatible runtime is a blocked execution, not evidence of test omission. Do not replace native Ekstazi with a home-written selector and label the result as native validation.

## 3. Fixture and oracle

Use at least two independent production classes and two separate test classes. Each test class should have a direct dependency on its intended production class. A third test can cover a shared dependency if desired.

The baseline suite passes. An ordinary source change changes a deterministic output, while all tests remain byte-for-byte unchanged. The independent full suite must then fail in the predeclared affected test class. An unaffected test class remains passing. A separate positive control can change another independent class in a harmless way to cause at least one passing test to execute when the affected test is omitted; do not confuse that optional control with a requirement for detecting omissions.

Avoid shared instrumentation inside tests: writing to a shared marker file can itself create dynamic dependencies. Prefer fresh runner-generated test reports or instrumentation outside the application’s observed dependencies. Record method-level and class-level counts separately.

The full-suite oracle executes without RTS in a fresh process and in an independent state. It must discover the same test universe, compile the same modified source, use the same test inputs, and preserve the same classpath and test options. A full-suite failure must be an assertion failure tied to the intended ordinary change, not an unrelated compilation failure, missing dependency, or test harness crash.

## 4. Required controls

| Control | Purpose | Evidence required |
| --- | --- | --- |
| Cold baseline, no metadata | Establish discovery and initial collection | Every expected test class executes and passes; metadata is generated |
| Warm unchanged baseline | Demonstrate that selection is active | Native RTS executes the observed reduced set; report actual classes |
| Ordinary change, intact metadata | Establish normal change detection | The unchanged affected test executes and exposes the intended assertion failure |
| Full suite, unchanged baseline | Establish oracle health | All expected tests pass without RTS |
| Full suite, ordinary change | Establish relevant failing tests | Same modified source produces intended failures without RTS |
| Integrity gate, intact metadata | Establish nonfallback path | Trusted snapshot and provenance verify; RTS executes normally |
| Integrity gate, corrupted metadata | Establish fallback path | Verification fails before selection; full-suite fallback actually runs |

Restore the identical successful baseline before every case. Do not let previous failed tests, automatic cache repair, or a full-suite run seed the next case. Keep the physical workspace path fixed where metadata may refer to absolute paths. If moving a snapshot is necessary, disclose it and use a relocation control. Do not silently rewrite native metadata merely to make paths portable.

## 5. Fault matrix

Select a small fixed set before observing outcomes. Report every executed case, including conservative reruns and crashes.

| Simulation | Definition | Interpretation boundaries |
| --- | --- | --- |
| Missing cache directory | Remove the synthetic fixture’s copied cache directory | Measures native behavior when state is absent; expected conservative behavior must still be verified |
| Missing per-test metadata | Remove one baseline record chosen by fixture identity | Measures behavior on absent test dependency state |
| Truncated record | Cut a copied record at a fixed byte offset or fraction, declared before execution | May produce unreadable or partially readable state; record exact bytes and parser response |
| Malformed record | Replace a copied record with a fixed inert invalid byte sequence | Measures malformed-input handling, including aborts |
| Incorrect snapshot restore | Restore a complete prior snapshot from a separately labeled fixture state | Describe the exact state mismatch. Ordinary older dependency state may still detect changes correctly |

Do not assume all missing or stale metadata produces omissions. The tool may rerun tests conservatively, reject state, or fail the build. Those outcomes are scientifically informative.

## 6. Three paired strategies

**Standard RTS.** Run the native tool against the specified source and metadata state. Do not intercept native decisions or modify selected-test lists.

**Integrity verification with full-suite fallback.** Before invoking RTS, compare the restored cache against a trusted manifest outside the faultable cache directory. Bind the manifest to the trusted baseline identifier, tool/version, test-discovery configuration, dependency/build context, and expected cache file inventory. Verify file content hashes and missing/extra files. If verification fails or context is ambiguous, run the unchanged full-suite oracle. Record verification failure separately from test failure and separately from a hard pipeline stop.

The trusted baseline identifier refers to the state from which dependencies were collected. It must not simply require that the current modified source equals the baseline: such a rule would rerun the full suite after every change and would erase the intended RTS comparison. The current source may differ; selection evaluates those differences.

**Full suite.** Run the same oracle for each paired case without RTS or dependence on the corrupted metadata.

A stored SHA-256 digest is an integrity reference only under a protected trust anchor. If an actor can replace both the metadata and the expected digest, this design does not authenticate the cache. The local simulation can test the protected-manifest assumption; it cannot demonstrate cache provenance, access controls, or attestation in a real CI service.

## 7. Outcomes and decision rules

Let `T` be the test classes discovered by the full suite, `S` the classes actually executed by RTS, and `F` the classes failing in the full-suite oracle for the same modified source. Keep method counts as a separate descriptive metric.

- Relevant omissions: `F ∖ S`.
- Oracle-failure coverage: `|F ∩ S| / |F|` when `F` is nonempty. This measures coverage of observed failing tests, not all semantically affected tests.
- Conditional omission indicator: `F ∖ S` is nonempty and selection/execution completed successfully enough to characterize the selected set.
- False-green indicator: native RTS completes successfully with no reported test failures/errors while `F` is nonempty and at least one failing test was omitted.
- Conservative rerun: all oracle-failing classes execute; may include the complete suite.
- Infrastructure or parse error: the process aborts or does not provide sufficient execution evidence. It is not a false green. An abort can still be a loss of availability.
- Integrity detection: verifier detects a named injected mismatch before native selection. Missing records, added records, content modifications, and provenance mismatch should have distinct reasons.
- Fallback coverage: the fallback executes every expected test and reproduces the oracle result.
- Test reduction: `1 - |S| / |T|`, interpreted only alongside failure coverage.

For a green unchanged baseline, `F` is empty; oracle-failure coverage is undefined, not 100%. A zero-test warm run is not automatically a defect. Conversely, a nonzero-test run does not establish safety.

## 8. Statistics and presentation

For the initial fixture, report exact case counts and paired outcomes in a table. Do not attach a population confidence interval to a deterministic, hand-selected fault set. Do not report a p-value for repeated copies of one scenario.

If runtime is measured repeatedly, disclose warm-up, run order, count, and machine-sharing conditions; summarize median and range or interquartile range. Include integrity verification and fallback time in end-to-end timing. An undersized fixture primarily validates behavior and cannot support general CI cost claims.

For a later multi-project study, prespecify selection and exclusions, and analyze paired outcomes by unique project/change/fault units. Keep project clustering in uncertainty estimates. A repository sample chosen because it uses RTS supports a conditional feasibility study, not RTS adoption prevalence. Population prevalence requires a defined sampling frame, eligibility rules, timestamp, reproducible sample selection, and treatment of inaccessible repositories.

Publication tables should include the actual denominator and a `basis` column with values such as `native_execution`, `native_execution_under_simulated_fault`, `source_inspection`, `blocked`, and `untested`. Use `NA` for unavailable measurements, not zero. Every result cell should trace to raw evidence.

## 9. Repository inspection boundaries

Separate these observable categories:

1. RTS dependency or plugin declaration.
2. An enabled/optional build profile.
3. A CI command that actually invokes that profile or selector.
4. Visible cache configuration and restore keys.
5. Visible full-suite scheduling, failure handling, and integrity verification.
6. Branch protection, required checks, code-owner enforcement, and cache permissions confirmed through authenticated settings or other direct evidence.

A plugin declaration is not proof of active CI usage. A code-owner file is not proof that review is required. A workflow file cannot establish the repository’s branch-protection settings. Inaccessible or incomplete configuration yields `unknown`, not `absent`. Retain immutable commit references whenever available; otherwise explicitly label the inspection as a dated mutable snapshot.

## 10. Validity threats

- **Construct validity:** failing-oracle coverage is narrower than semantic affectedness; synthetic arithmetic faults are not real vulnerabilities; deliberate incomplete metadata does not establish attacker access.
- **Internal validity:** cache repair, absolute paths, compilation timestamps, stale reports, framework configuration, previous failures, test discovery changes, and environmental dependencies can confound selection.
- **External validity:** one tiny fixture and one tool version cannot establish prevalence or behavior in multi-module, generated-code, reflection-heavy, or production CI settings.
- **Conclusion validity:** deterministic repetitions and multiple fault cases within one fixture are correlated; five purposively selected projects cannot establish population rates.
- **Defense validity:** the integrity gate assumes a trusted manifest and correct baseline generation; it cannot detect a dependency omission already present in a trusted snapshot unless there is an independent completeness oracle.
- **Implementation validity:** source-level expectations must be checked against the exact installed binary and effective configuration; historical documentation may differ from 5.3.0.

## 11. Primary sources consulted

1. Gligoric, Eloussi, and Marinov. *Practical Regression Test Selection with Dynamic File Dependencies*. ISSTA 2015. https://mir.cs.illinois.edu/marinov/publications/GligoricETAL15PracticalRTS.pdf . Consulted for dependency granularity and end-to-end RTS phases.
2. Gligoric, Eloussi, and Marinov. *Ekstazi: Lightweight Test Selection*. ICSE 2015 tool demonstration. https://mir.cs.illinois.edu/marinov/publications/GligoricETAL15EkstaziDemo.pdf . Consulted for historical integration, dependency collection, cold-start behavior, and full-execution options.
3. Maven Central package metadata for `org.ekstazi:org.ekstazi.parent`. https://central.sonatype.com/artifact/org.ekstazi/org.ekstazi.parent . Search retrieval showed version 5.3.0. This is package metadata, not executable validation.

No primary 5.3.0 Java parser source was retrieved by this reviewer: direct GitHub and raw-source fetches returned access errors, and the published sources JAR contained no Java sources. The published core JAR was subsequently inspected directly with `javap`; see `binary_inspection.md`. That evidence supports implementation-level expectations, while native selection behavior remains an empirical question.
