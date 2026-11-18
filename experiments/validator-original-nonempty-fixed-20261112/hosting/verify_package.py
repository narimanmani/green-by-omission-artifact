"""Verify all immutable package members before building the lab image."""
import hashlib, json
from pathlib import Path
root = Path(__file__).resolve().parent
expected = json.loads((root / "PACKAGE_MANIFEST.json").read_text())["sha256"]
for name, digest in expected.items():
    actual = hashlib.sha256((root / name).read_bytes()).hexdigest()
    assert actual == digest, name
print(f"Verified {len(expected)} frozen package members")
