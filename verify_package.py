"""Offline, standard-library integrity check. Does not import or run subject code."""
from pathlib import Path, PurePosixPath
import hashlib, json, sys

root = Path(__file__).resolve().parent
manifest = json.loads((root / 'MANIFEST.json').read_text(encoding='utf-8'))
expected = set()
for item in manifest['files']:
    relative = PurePosixPath(item['path'])
    assert not relative.is_absolute() and '..' not in relative.parts
    assert item['path'] not in expected
    expected.add(item['path'])
    path = root / relative
    assert path.is_file() and not path.is_symlink(), item['path']
    payload = path.read_bytes()
    assert len(payload) == item['bytes'], item['path']
    assert hashlib.sha256(payload).hexdigest() == item['sha256'], item['path']
actual = {p.relative_to(root).as_posix() for p in root.rglob('*')
          if p.is_file() and '.git' not in p.relative_to(root).parts}
assert actual == expected | {'MANIFEST.json', 'SHA256SUMS.txt'}, sorted(actual - expected)
for line in (root / 'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
    digest, name = line.split('  ', 1)
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest, name
print(json.dumps({'status':'PASS', 'payload_files':len(expected),
                  'all_packaged_sha256_verified':True,
                  'unexpected_files':0,
                  'subject_code_executed':False}, indent=2))
