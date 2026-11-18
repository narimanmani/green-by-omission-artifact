# Independent original-test outcome audit

**PASS_THREE_FRESH_QUALIFYING_REPETITIONS**.

| Repetition | Baseline passed/failed | Native passed/failed | Independent passed/failed | Process exits |
| --- | --- | --- | --- | --- |
| 1 | 8173/0 | 8/0 | 8172/1 | 0/0/1 |
| 2 | 8173/0 | 8/0 | 8172/1 | 0/0/1 |
| 3 | 8173/0 | 8/0 | 8172/1 | 0/0/1 |

The native cases are the original tests in tests/unit/auth/account-setup.test.ts. The omitted detecting case is auth.definition.ts cookie configuration should not use sameSite: none (weakens CSRF protection) at tests/unit/authentication/cookie-config.test.ts:14. Its failure is bound to the original not.toMatch expectation, not setup/runtime failure. All 471 original unit files and their full case identities remain present in each independent oracle. Source/config/lock/test/Git identities and all 49,661 installed dependency entries remain unchanged; the same frozen candidate bytes occur across selective and independent states.

Fresh separate containers, exact frozen image/context, empty initial caches, native/baseline cache continuity and a separate empty independent cache are verified. Raw JSON/log exports and supplementary cache/coverage inventories pass hash checks. V1 and v2 ineligible baselines are retained separately and are not qualifying repetitions.

This establishes the bounded missing joint observation for an upstream static security-source guard in this configured unit oracle. It does not establish runtime CSRF exploitability, CRC collision behavior, production prevalence or independent protected-branch contributor validity. The repetitions repeat one fixed case. No subject tests were rerun by this auditor.
