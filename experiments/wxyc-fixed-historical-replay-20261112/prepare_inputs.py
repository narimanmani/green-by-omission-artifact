"""Verify public Git bytes and pin one historical-fix reversion; run no subject code."""
from pathlib import Path
import hashlib, json, subprocess

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'input/upstream'
BASE = 'b86530c6c656b7a8f72d42145e9d46995c7ab53d'
AUTH = 'shared/authentication/src/auth.definition.ts'
GUARD = 'tests/unit/authentication/cookie-config.test.ts'
FIXED = b"      sameSite: (process.env.COOKIE_SAME_SITE as 'lax' | 'strict' | 'none') || 'lax',\n"
OLD = b"      sameSite: 'none',\n"
def git(*args):
    return subprocess.check_output(['git', *args], cwd=SOURCE)
def blob(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
def canonical(value):
    return (json.dumps(value, ensure_ascii=False, separators=(',', ':')) + '\n').encode()
def save(name, data):
    target = ROOT / name
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.read_bytes() != data:
        raise RuntimeError('Refusing to overwrite different evidence: ' + name)
    target.write_bytes(data)
def save_json(name, value):
    save(name, json.dumps(value, indent=2, ensure_ascii=False).encode() + b'\n')

assert git('rev-parse', 'HEAD').decode().strip() == BASE
assert git('rev-parse', 'refs/remotes/origin/main').decode().strip() == BASE
assert not git('status', '--porcelain=v1'), 'Baseline input must be pristine.'
rows = []
for entry in git('ls-files', '--stage', '-z').split(b'\0'):
    if not entry: continue
    head, name = entry.split(b'\t', 1)
    mode, expected, stage = head.decode().split()
    assert stage == '0' and mode in ('100644', '100755')
    name = name.decode('utf-8')
    data = (SOURCE / name).read_bytes()
    assert blob(data) == expected, 'Git-byte mismatch: ' + name
    rows.append(dict(path=name, mode=mode, git_blob=expected, size=len(data), sha256=hashlib.sha256(data).hexdigest()))
rows.sort(key=lambda row: row['path'])
original = (SOURCE / AUTH).read_bytes()
assert original.count(FIXED) == 1
candidate = original.replace(FIXED, OLD, 1)
candidate_rows = [dict(row) for row in rows]
for row in candidate_rows:
    if row['path'] == AUTH:
        row.update(git_blob=blob(candidate), size=len(candidate), sha256=hashlib.sha256(candidate).hexdigest())
unit = [row for row in rows if row['path'].startswith('tests/unit/') and row['path'].endswith('.test.ts')]
lock = json.loads((SOURCE / 'package-lock.json').read_bytes())
save('input/fixed-candidate/' + AUTH, candidate)
save_json('input/baseline-source-manifest.json', rows)
save_json('input/candidate-source-manifest.json', candidate_rows)
save_json('input/original-unit-test-manifest.json', unit)
receipt = dict(status='SUBJECT_INPUTS_PINNED_NO_TEST_EXECUTION', repository='https://github.com/WXYC/Backend-Service', baseline_revision=BASE,
    baseline_git_tree=git('rev-parse', 'HEAD^{tree}').decode().strip(), public_fix='8e2fc5f320633ddec0e99e05b65b21682ed3ccda',
    candidate_description='Exact inverse of the public SameSite production-line hunk only; later original tests retained.',
    authentic_historical_pair=False, changed_tracked_files=[AUTH], tracked_file_count=len(rows), original_unit_test_file_count=len(unit),
    baseline_manifest_sha256=hashlib.sha256(canonical(rows)).hexdigest(), candidate_manifest_sha256=hashlib.sha256(canonical(candidate_rows)).hexdigest(),
    guard_git_blob=next(row['git_blob'] for row in rows if row['path']==GUARD), guard_semantics='Static source-policy assertion; no runtime CSRF or exploitability conclusion.',
    locked_shared_package=lock['packages']['node_modules/@wxyc/shared'], upstream_tests_changed=False, test_config_changed=False,
    repetitions_executed=0, baseline_result=None, native_result=None, independent_result=None)
save_json('INPUT_IDENTITY.json', receipt)
print(json.dumps({key: receipt[key] for key in ('status','baseline_revision','tracked_file_count','original_unit_test_file_count','baseline_manifest_sha256','candidate_manifest_sha256','repetitions_executed')}, indent=2))
