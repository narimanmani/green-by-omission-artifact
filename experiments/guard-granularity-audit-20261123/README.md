# Static audit of checksum–AST comparison granularity

The local mismatch guard compares checksums at file granularity. This audit compares its decisions on ten retained case conditions with a comparison at block granularity. The audit used the archived testmon 2.3.0 comparison predicates on the retained inputs. This release records those predicates and decisions using case IDs within each condition.

| Case condition | Cases | File-level flags | Block-level flags |
| --- | ---: | ---: | ---: |
| Local empty-selection cases | 3 | 3 | 3 |
| Ordinary-regression controls | 3 | 0 | 0 |
| Comment-only controls | 3 | 0 | 0 |
| Reviewed nonempty hosted case | 1 | 0 | 1 |

The three local flags agree with the separately recorded local experiment in which all three complete-oracle fallbacks rejected their candidates. The earlier hosted run used a separate AST-change diagnostic. The hosted row above records static guard decisions on that retained case. End-to-end effectiveness, fallback frequency, and operational cost of the per-block comparison remain unmeasured.

## Verify the saved audit

Run `python guard_check.py` in this directory. It reads the saved decision predicates in `output.txt`, recomputes the flags, checks the case counts, and verifies that they match the table above. The verification operates solely on the saved record. Its result covers consistency of the recorded decisions.
