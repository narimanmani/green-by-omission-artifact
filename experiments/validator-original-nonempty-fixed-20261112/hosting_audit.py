"""Independently summarize three fixed container outcomes from retained JSON."""

import hashlib
import json
import sys
from pathlib import Path


root = Path(sys.argv[1])
rows = []
for n in range(1, 4):
    folder = root / f"repetition-{n}"
    result = json.loads((folder / "result.json").read_text())
    arms = json.loads((folder / "arms.json").read_text())
    identity = json.loads((folder / "candidate-identity.json").read_text()) if (folder / "candidate-identity.json").exists() else None
    rows.append({"repetition": n, "result": result, "arms": arms, "identity": identity, "raw_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(folder.glob("*.json"))}})

summary = {
    "repetitions": 3,
    "statuses": [r["result"]["status"] for r in rows],
    "joint_observations": [r["result"].get("joint_observation") for r in rows],
    "baseline_counts": [r["result"].get("baseline_test_count") for r in rows],
    "native_counts": [r["result"].get("native_test_count") for r in rows],
    "independent_counts": [r["result"].get("independent_test_count") for r in rows],
    "raw_records": rows,
}
(root / "AUDIT.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps({k: v for k, v in summary.items() if k != "raw_records"}, indent=2))
