# Independent audit of the completed local study

Audit date: 2026-11-10. Result: **no discrepancy found in the reviewed execution counts, raw execution evidence, recorded hashes, or reported discrete outcomes**. Interpret the findings within the limits below.

This audit read the existing scripts, per-run JSON, raw JUnit output, testmon JUnit XML, stored metadata, source snapshots, and configuration evidence. It did not rerun the experiments or add new fault cases. `audit.json` contains the machine-readable findings and hashes of the reviewed scripts.

## Verified results

| Study component | Existing executions audited | Verified outcome |
| --- | ---: | --- |
| Core Ekstazi synthetic fixture | 4 controls and 72 comparisons | All 72 comparisons completed with both intended arithmetic assertion failures. No relevant oracle-failing test was omitted. No comparison returned a successful exit. |
| Supplemental local Maven integration | 4 checks | Cold, warm, ordinary-change, and changed full-suite runs executed 4, 0, 3, and 4 methods respectively; failures were 0, 0, 2, and 2. |
| pytest-testmon synthetic fixture | 4 controls and 45 comparisons | 39 comparisons completed and exposed both intended failures. Six standard-RTS comparisons stopped with runner error, exit code 3. No comparison returned a successful exit. |
| Five synthetic Java library wrappers | 15 controls and 45 comparisons | All 45 comparisons executed the relevant synthetic test and exposed its intended assertion failure. |
| Static repository configuration audit | 20 pinned repository snapshots; 156 configuration files | Retained configuration and archive hashes matched their manifests. Two inspected root POMs declared optional Ekstazi profiles. |

The 189 formally analyzed process invocations comprise 162 matrix comparisons and 27 controls/supplemental integration checks. The matrix comparisons contain 156 completed executions exposing the expected assertion failures and six testmon runner errors. Setup probes and aborted harness preparation are separate from these totals. These totals describe execution records. They must not become independent statistical sample sizes for attack success, security failure prevalence, or general RTS reliability.

### Ekstazi controls and invariants

- The 72 comparisons are eight fixed conditions, three strategies, and three technical repeats. One condition is the intact-metadata normal-change control.
- All comparisons used the same candidate source inventory. All controls and comparisons used the same test-source inventory.
- Comparing baseline and changed snapshots independently confirmed unchanged compiled test bytecode.
- The raw listener start/failure events and JUnit summaries matched each aggregate and per-run record.
- Every stored injected metadata inventory matched the metadata inventory recorded immediately before execution.
- Every half-truncation copy retained exactly the first `floor(original_length / 2)` bytes of the baseline target record.
- The verification strategy fell back to agent-free execution in 21 comparisons: seven simulated fault conditions, repeated three times. Its three intact-metadata comparisons used native selection.
- The `wrong_baseline_id` condition preserved metadata bytes. It changed only a synthetic provenance label supplied to the guard.

The obtained evidence supports the claim that **these fixed simulations did not produce an omitted failing test or false-green result in this native engine fixture**. It does not establish that every malformed state is safe or that Ekstazi is immune to omitted dependencies.

### Testmon controls and invariants

- The 45 comparisons are five fixed conditions, three strategies, and three technical repeats. One condition has intact metadata.
- All comparison executions used one candidate source inventory; tests were unchanged throughout.
- Fresh XML counts and identities matched stored result records. Per-run pre-state hashes matched the result hashes.
- Half-truncated and garbage databases caused the standard selector to stop before normal test execution in all three repeats each.
- The separately verified strategy invoked the full suite for all 12 faulted comparisons and exposed both expected assertion failures.

The raw `relevant_omitted_nodeids` field contains a set difference even for runner errors. The subsequent `derived_results.json` and `.csv` correctly mark those six executions `omission_assessable=false` and `selection_omission_count=null`. This audit confirmed that the derived records preserve the original measurements. The correct publication interpretation is **omission not evaluable / runner error**, because there was no completed selection/execution outcome. Use the derived classification in publication tables; do not present these rows as successful omissions or false greens.

With an ordinary CI policy that rejects a nonzero test-process exit, both the original runner error and the full-suite fallback reject the candidate. The observed benefit of fallback here is successful test execution and explicit regression diagnosis. The experiment did not show a reduction in successful bypasses.

## Distinctions required in the report

1. **Native engine versus Maven/CI integration.** The Ekstazi fault matrix invokes the published Java agent in JUnit mode through an observation-only runner. Four separate, audited offline Maven controls establish basic integration with Maven 3.8.8 and Surefire 2.22.2 using Ekstazi 5.3.0 `select` plus `restore` with an explicit excludes file. Fresh XML matched all four records and test sources remained unchanged. No metadata-fault matrix was run through Maven, and hosted CI remains untested.

2. **Provenance-label mismatch versus stale native state.** `wrong_baseline_id` is a guard-level simulation. No alternate native dependency snapshot was restored in this condition. Actual stale-cache restoration remains untested by this case.

3. **Synthetic wrappers versus project regression suites.** The five wrappers call real, unmodified released Java libraries. The mutations and tests belong to generated wrappers. No upstream regression suite was executed, and no upstream implementation was mutated. This supports a small library-integration feasibility claim, not a five-project regression-selection evaluation.

4. **Released artifacts versus inspected commits.** The wrappers use pinned releases. The configuration audit uses separately pinned default-branch commits. Results from one must not be attributed to the version used by the other.

5. **Configuration presence versus deployed usage.** Optional Ekstazi profiles were found in two of the 20 inspected repositories. No explicit Ekstazi reference appeared in the inspected workflow text. This does not show that those profiles are unused everywhere, that runtime workflows ran, or that checks were mandatory. Branch protection and required checks remain unobserved.

6. **Primary-workflow indicators versus repository-wide guarantees.** The reported read-only content permission, action pins, credential persistence, and Maven dependency cache indicators refer to each inspected `maven.yml` workflow. They do not establish safeguards in every possible workflow, shared service, or organization setting. Maven dependency caching is not evidence of RTS metadata caching.

7. **Descriptive case counts versus population inference.** The repository sample is purposive, consists of one organization’s projects, and was not blinded to previously known RTS mentions. The fault corpus is hand-designed. Neither supports a population prevalence estimate or a confidence interval for real-world attack success.

## Guard scope and limitations

The three prototype guards have different predicates:

| Component | Inputs actually checked before selection |
| --- | --- |
| Core Ekstazi fixture | Cache file inventory and content hashes, test-source hashes, agent hash, synthetic baseline identifier |
| Testmon fixture | Cache file names, sizes and hashes; test-source hashes |
| Java wrapper pilot | Cache file inventory and content hashes |

These are local trusted-manifest simulations. They assume that the manifest and baseline snapshot remain outside the fault injector’s control. They do not implement authenticated storage, signing, protected CI provenance, complete build-context binding, source-to-cache semantic validation, or verification/use race prevention. Testmon records package versions in its manifest but does not compare those versions in the guard predicate.

A correct digest establishes equality to a reference. It cannot establish that the reference captured every dependency. A self-consistent but incomplete trusted snapshot could pass these checks. That hypothesis was not exercised.

## Timing limits

Ekstazi’s main fixture reports JVM process time plus measured verifier time, excluding reset, compilation, and setup. Testmon and wrapper timing fields primarily measure runner subprocess execution; verifier work is outside their timed regions. The testmon pilot also uses fixed condition order, and the research processes share a machine.

Therefore:

- Do not compare reported times across the three components as equal-scope costs.
- Do not label these measurements end-to-end CI speedups.
- Do not claim that the verified strategy is faster or cheaper based on this tiny corpus.
- Report timings as descriptive diagnostics with their scope, or omit them from the main publication tables.

## Defensible conclusion

In the executed synthetic corpus, ordinary source changes were detected by the native selectors when execution completed. The tested Ekstazi metadata faults did not suppress the relevant failing tests. Testmon database damage sometimes caused runner errors; the trusted-manifest fallback converted those error outcomes into completed full-suite executions that exposed the intended regressions. The work provides a reproducible local integrity-fault pilot and a static configuration sample. It does not demonstrate an adversarial bypass, deployed exploitability, or population deployment prevalence.
