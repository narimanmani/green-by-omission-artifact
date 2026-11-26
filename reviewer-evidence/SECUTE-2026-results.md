# SECUTE reviewer evidence

This record summarizes retained outcomes for the 60-test Validator comparison, the hosted and controlled Java nonempty observations, and the metadata-fault campaign. The guard-granularity audit separately records static decisions on ten saved cases. These records support inspection of the reported outcomes and the scope of the controls.

## Scope of the nonempty comparisons

| Configuration | Native selection | Independent evaluation | Matched ordinary-change control |
| --- | --- | --- | --- |
| Apache Commons Validator, three upstream classes | 20 original tests executed and passed | 60 cases executed, with two original URL assertion failures | Outstanding in the 60-test configuration |
| Reviewed hosted fixture | One test executed and passed | Three cases executed, with one failure | Outstanding for the nonempty fixture under the protected-baseline setup |
| Controlled Java fixture | One test executed and passed | Three cases executed, with one failure | Outstanding for the nonempty revision |

For Validator, all 60 baseline tests passed and the unchanged rerun selected no tests. The same outcomes were retained across three technical repetitions. The earlier 40-test Validator configuration and the original nonempty replay have different protocol coverage. The hosted replay used a three-test research oracle and was limited to the reviewed fixture. Its selective status passed while code-owner approval remained required, and the pull request closed unmerged.

## Metadata-fault campaign

| Strategy | Comparisons | Detections | Explicit errors | False passes |
| --- | ---: | ---: | ---: | ---: |
| Standard RTS | 54 | 48 | 6 | 0 |
| Manifest-verified escalation | 54 | 54 | 0 | 0 |
| Unconditional complete oracle | 54 | 54 | 0 | 0 |
| Total | 162 | 156 | 6 | 0 |

Each strategy contributes 24 native Ekstazi, 15 native testmon, and 15 Java-wrapper comparisons. All six explicit errors occurred under standard RTS in the testmon fixture. The matched guarded runs completed the oracle and detected the regressions. The 27 setup and control runs have a separate denominator. The provenance-label condition changed a declaration. The results cover the recorded fault conditions and leave genuine stale-baseline restoration unevaluated.

The paper links the saved static-audit predicates and its verifier separately. Review access provided by this record covers observed outcomes and static decisions. Access arrangements for detailed runtime materials are part of the authors' disclosure coordination.
