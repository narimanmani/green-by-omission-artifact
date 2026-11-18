# Original upstream security-guard result

**The requested original-test/nonempty false-pass criterion is met in all three fresh repetitions:** the original unit baseline passes 8,173 cases; native Jest selection passes eight original cases; independent execution on the identical candidate passes 8,172 cases and fails one unchanged original security-source guard. Actual exits are **0 / 0 / 1**. There are **zero skipped, pending or todo cases**.

| Repetition | Original baseline | Native selection | Independent same candidate | Exits (baseline/native/full) |
| --- | --- | --- | --- | --- |
| 1 | 8,173 pass | 8 pass | 8,172 pass; 1 original guard fail | 0 / 0 / 1 |
| 2 | 8,173 pass | 8 pass | 8,172 pass; 1 original guard fail | 0 / 0 / 1 |
| 3 | 8,173 pass | 8 pass | 8,172 pass; 1 original guard fail | 0 / 0 / 1 |

Counts denote **Jest test cases**, not individual `expect` assertions. All repetitions execute one fixed case in fresh isolated containers; they are not three independent vulnerabilities.

## Original tests and exact omission

The eight actually executed native cases are the unchanged upstream tests in `tests/unit/auth/account-setup.test.ts`. They exercise account-setup token creation, expiry/redirect overrides, email success/failure and mint/send ordering. Their exact case names are preserved in `RESULTS.json` and the raw Jest reports.

The omitted detecting case is `auth.definition.ts cookie configuration should not use sameSite: none (weakens CSRF protection)` in `tests/unit/authentication/cookie-config.test.ts`. Its original expectation at **line 14**, `expect(source).not.toMatch(hardcodedNone);`, fails under independent execution. The whole guard file is absent from native execution. The case and its original blob `5c14cd837a04880807d3ef4f643da64cbdf6a552` are unchanged. The failure is tied to that expectation line, not setup, import or runtime-test errors.

The full oracle is all **471 original unit-test files / 8,173 cases** under the unchanged `jest.unit.config.ts`; it is not the integration suite. Complete case identities match across baseline and independent execution. All 1,869 tracked source/configuration/test/lock files and all 49,661 installed dependency entries are verified at the required checkpoints. The same frozen candidate bytes occur before/after native and independent arms. Separate fresh independent caches and hash-bound raw exports are verified.

## Controlled public-fix reversion

Repository: `WXYC/Backend-Service`; baseline `b86530c6c656b7a8f72d42145e9d46995c7ab53d`. The candidate changes only `shared/authentication/src/auth.definition.ts`, using the exact inverse of the production-line hunk in public fix `8e2fc5f320633ddec0e99e05b65b21682ed3ccda`: the configurable/default-lax expression becomes the prior hardcoded `sameSite: 'none'` line. Later original upstream tests are retained unchanged. This is a controlled historical-fix reversion, **not an authentic historical buggy/fixed revision pair**.

The final frozen protocol uses native `--changedSince=origin/main`, coverage and the original unit configuration, with original worker semantics bounded to `--maxWorkers=2`. Jest's own small-selection serial fallback remains intact. No test, gate, selector implementation or candidate was optimized after a candidate outcome.

## Retained ineligible preflights

| Version | Original case results | Actual Jest exit | Candidate applied or executed? | Disposition |
| --- | --- | --- | --- | --- |
| V1 | 8,169 pass; 4 fail | 1 | No | Original cron-script tests require missing OS utility `jq`; explicit platform-only probe confirms absence. |
| V2 | 8,173 pass; 0 fail; JSON success true | 1 | No | Researcher-added serial execution exposed shared process exit-state contamination. Original Node/Jest sources support restoring upstream worker semantics. |

The outer harness exits **2** for each ineligible preflight and correctly stops before applying the candidate. These are retained separately with their freezes, images, raw logs and audit verdicts; neither is counted as a qualifying repetition. V1 planned three repetitions but stopped after its first ineligible baseline; V2 likewise stopped after one. The final version was separately frozen before any candidate observation and ran three fresh repetitions.

The platform correction adds only `jq`/`libjq1` 1.6-2.1+deb12u3 and `libonig5` 6.9.8-1; no existing OS package version changes. The later mode correction replaces only the researcher-added serial CLI literal with the bounded worker flag. No exit code is reset or failure suppressed by the research harness. The exact dependency package reconstruction matches the complete original lockfile SHA-512; the original lock remains unchanged.

## Claim boundary

The literal requested observation is established: unchanged original tests pass at baseline; nonempty native execution passes; independent execution on the same candidate fails an original security-policy test that native selection omitted. The following limits describe stronger claims that were not measured; they are not new eligibility rules that negate this result:

- The detecting oracle enforces **static security source policy**. Runtime cookie behavior, CSRF exploitability and production compromise were not tested.
- This is a **Jest dependency-graph omission**. It does not establish an original-test/nonempty CRC-collision conjunction for testmon or Ekstazi.
- This local isolated study does not establish independent external-contributor protected-baseline hosted validation.
- No deployment-prevalence or population-level inference follows from one fixed case repeated three times.

## Audit and private evidence

The independent raw audit passes **245/245 checks**: 79 per repetition and eight global correspondence checks. See `native-parallel-correction/INDEPENDENT_OUTCOME_AUDIT.json` and `.md`, plus each raw `results/repetition-N/evidence.json` and the original host receipts. Earlier input, package, seed, protocol and correction audits are retained.

This is a **private local research deliverable**. The evidence ZIP is not uploaded, published, anonymized or claimed to be a turnkey public artifact. No subject tests were rerun while preparing these reports or packaging the evidence.
