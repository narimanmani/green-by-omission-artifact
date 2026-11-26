"""Verify the static guard decisions from their recorded comparison predicates."""
from collections import Counter
import json
from pathlib import Path


def main():
    evidence = json.loads(Path(__file__).with_name("output.txt").read_text(encoding="utf-8"))
    if evidence["evidence_type"] != "static guard decisions" or evidence["subject_code_executed"] is not False:
        raise SystemExit("The record must describe static decisions on saved cases.")

    expected = {
        "empty-selection": (3, 3, 3),
        "ordinary-regression": (3, 0, 0),
        "comment-only": (3, 0, 0),
        "hosted-nonempty": (1, 0, 1),
    }
    case_counts = Counter()
    file_flags = Counter()
    block_flags = Counter()
    case_ids = set()
    for row in evidence["rows"]:
        case_id = row["case"]
        if case_id in case_ids:
            raise SystemExit(f"Duplicate case ID: {case_id}")
        case_ids.add(case_id)

        file_flag = row["file_checksums_equal"] and row["module_ast_differs"]
        block_flag = any(
            block["representation_changed"] and block["crc32_equal"]
            for block in row["changed_blocks"]
        )
        if (file_flag, block_flag) != (row["file_level_flags"], row["block_level_flags"]):
            raise SystemExit(f"Saved flags disagree with the predicates for {case_id}.")

        category = row["category"]
        case_counts[category] += 1
        file_flags[category] += file_flag
        block_flags[category] += block_flag

    observed = {
        category: (count, file_flags[category], block_flags[category])
        for category, count in case_counts.items()
    }
    if observed != expected:
        raise SystemExit(f"Unexpected case and flag counts: {observed}")

    print(json.dumps({
        "status": "PASS",
        "saved_static_decisions_verified": len(case_ids),
        "counts": {
            category: {"cases": count, "file_level_flags": file, "block_level_flags": block}
            for category, (count, file, block) in observed.items()
        },
    }, indent=2))


if __name__ == "__main__":
    main()
