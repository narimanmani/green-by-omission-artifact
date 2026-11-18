"""Fail if any vendored testmon module differs from the official Git v2.3.0 tag.

Git commit: 86d43f1b5c4e0c4aca421658a61e707f0e224c45
Each checksum below is the original Git blob SHA-1 retrieved from that commit.
"""
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
EXPECTED={
  '__init__.py':'5f1916b599db224d364f97b4ed84568f45898fcd',
  'common.py':'8809e999fa594f917a13ee0d1a82fb22180d2202',
  'configure.py':'dc1c1dd130130785a3ca71b9fe1f6e4a490a7862',
  'db.py':'52e685c370cd75314eefb6732643cd4ac8e9f786',
  'process_code.py':'29427d7d7d40934d789521bd9ed152f3eff22556',
  'pytest_testmon.py':'34ed5146e933d64b4ffd78bea5989e65e7385090',
  'testmon_core.py':'699449a74038851d5c2a826c5a5f398fd0889cc4',
}
for filename, expected in EXPECTED.items():
 path=ROOT/'upstream'/'testmon'/filename
 assert path.is_file(),f'Missing {path}'
 actual=subprocess.check_output(['git','hash-object',str(path)],text=True).strip()
 assert actual==expected, f'Original upstream file modified: {filename} expected {expected}, actual {actual}'
 print('VERIFIED',filename,actual)
assert len(list((ROOT/'upstream'/'testmon').glob('*.py')))==7
print('PASS: 7/7 files match the release-tagged unmodified plugin')
