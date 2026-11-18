# Read-only diagnosis of the serial baseline exit state

Date: 2026-11-12. Scope: inspect retained v2 baseline evidence, unchanged upstream source, and exact installed runner source. No subject tests, candidate arms, application probes, or source variants were executed for this diagnosis. Frozen v2 was not modified.

## Observed result

The retained v2 baseline is **ineligible**: the actual Jest process exited 1, although its JSON report records 471 passing suites, 8,173 passing assertions, zero failed/pending assertions, zero runtime-error suites, `success: true`, and a passing designated original cookie-policy guard. Only the baseline arm exists. Before/after tracked source and installed dependencies match. A successful JSON report does not override the nonzero process result.

Input: `../platform-correction-jq/results/repetition-1/evidence.json`. `BASELINE_FACTS.json` binds its SHA256 and extracts the reported totals, process result, command, state identities, designated guard, and relevant raw stderr excerpt. The independent raw-outcome audit is retained separately under `../platform-correction-jq/INDEPENDENT_V2_BASELINE_VERDICT.json`.

The raw stderr records the imported library ETL job's catch path: `run().catch(...)` at `jobs/library-etl/job.ts:1414`, a logged TypeError at line 1415, and the displayed following assignment `process.exitCode = 1` at line 1416. The error is `tx.select(...).from(...).innerJoin is not a function`, in the test's mocked database context. All assertions in that test file nevertheless pass. This log is direct evidence that the catch path ran; it is not a timestamped trace of every exitCode write.

## Exact-source explanation

All installed-source snapshots in `installed-source/` were copied with `docker cp` from the unstarted immutable assembly container `sp2027-wxyc-final-assembly-jq-20261112` (ID `0c03ce01e3e2f2cf1680d814167970995622e71f5f9d397b6b0e6da64768c00a`, image `sha256:36222dd77240e20948861c15d9e80b5940ef034e6130333019344815797b99ea`). The container was not started. Each copied file SHA256 matches its entry in the previously frozen `../backend-provisioning/seed-installed-manifest.json`; `SOURCE_IDENTITY.json` records the mapping and checks. Installed versions are Node 24.19.0 and Jest 30.4.2.

1. `jest-environment-node-index.js:183` installs common globals. `jest-util-index.js:705-706` sets the test global `process` to `createProcessObject()`. Its blacklist at line 161 contains `env`, `mainModule`, and `_events`; it does not exclude `exitCode`.
2. `jest-util-index.js:220-225` clones the real Node process. Its `deepCyclicCopyObject` at lines 316-334 copies property descriptors, recursively copies their data values, and retains accessor functions. Thus this is not evidence that every process property is independently isolated.
3. The official Node v24.19.0 bootstrap source, saved as `node-v24.19.0-bootstrap-node.js`, defines `exitCode` at lines 92-128 using getter/setter closures over `const fields = process[exit_info_private_symbol]`. The copied accessor therefore still refers to the original process's captured exit-state fields; it does not become a clone-local ordinary value. Primary source: https://github.com/nodejs/node/blob/v24.19.0/lib/internal/bootstrap/node.js ; official Git blob `2fafdb92a78e04fcfa73339b576444a48f8b9488`. The original connector response is retained as `node-v24.19.0-primary-response.json`.
4. `jest-runner-index.js:490-502` calls `runTest` directly in the enclosing process for serial execution. Consequently, a test environment's copied `exitCode` accessor can affect that CLI process's eventual status.
5. `jest-cli-index.js:719-739` computes code 0 when the result succeeds, but its normal exit hook assigns `process.exitCode` only when that computed code is nonzero. It does not clear an already nonzero process exit state on success. No force-exit option was present in v2.

These sources explain how serial execution can produce the observed combination of all passing assertions and process exit 1. They support the library job's logged catch as a concrete plausible writer. They do **not** establish that line 1416 was the sole or final writer. The job also sets exitCode at line 1063, and original `reportStrandedResurrections` tests assert that state and reset it to undefined in `afterEach` at lines 1012-1014. The retained run has no setter chronology. No additional instrumented execution was performed.

## Assessment of a pre-candidate scheduling correction

Replacing our added `--runInBand` with native `--maxWorkers=2` in a separately frozen protocol version is a defensible environment correction **before any candidate result**. The original upstream unit CI and package scripts do not request `--runInBand`; v2 introduced that serial scheduling choice for the local lab. A two-worker cap fits the declared two-CPU lab and restores Jest's ordinary worker architecture for the full 471-suite baseline while keeping the original source, tests, configuration, scope, prepared candidate, and dependencies unchanged. It does not reproduce the exact hosted machine or its default worker count.

The installed runner creates a worker pool at `jest-runner-index.js:504-530`; the default is process workers, with `workerThreads: false` in `jest-config-index.js:127`. The unchanged unit config does not override this. A child process's exit state cannot directly share the parent process's exit-state fields, so the serial exit-state propagation described above does not apply across those processes. This is a source-based explanation, not a guarantee that a parallel run will pass. Worker failures, retries, shutdown effects, or application side effects can still produce an ineligible run; preserve their actual results.

`--maxWorkers=2` is **not** force-parallel. The native scheduler in `jest-core-index.js:3574-3609` can run in-band for one selected suite, or for at most 20 previously timed fast suites, and also respects other native serial conditions. Baseline/full scope of 471 suites with two workers does not meet the small-scope fallback, but a selective arm may. Preserve this native behavior and record the exact command in every arm.

Keep v2 and its nonzero baseline result. Freeze any new version, use the same scheduling choice across its three arms, and require the actual baseline process exit 0, passing original guard, complete original case universe, and exact source/dependency identities before attempting the already frozen candidate. If qualification fails, preserve it and stop. Do not add `--forceExit`, reset exitCode, suppress the error, change the original job/tests/configuration, or accept JSON success as a process pass.

A later qualifying parallel baseline would establish a passing native Jest unit run under that declared configuration. It would not show that the imported ETL job itself had no logged operational failure, and this retained side effect should remain visible in raw evidence and limitations.

## Limits of this diagnosis

This is a static source and retained-log diagnosis. It does not prove the precise final exitCode writer, predict the outcome of a future run, establish a false pass, or execute the candidate. A correction must be judged from its actual process statuses and unchanged original assertions. The intended security outcome remains a source-policy guard, not runtime CSRF exploitation or a fingerprint-preserving mechanism.
