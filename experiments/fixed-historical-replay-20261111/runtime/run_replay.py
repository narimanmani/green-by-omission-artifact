"""Replay one fixed public historical change in a network-disabled container."""
import difflib
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path('/opt/replay')
SECURITY = 'tests/test_utils.py::TestGetNetrcAuth::test_not_vulnerable_to_bad_url_parsing'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def tree(work, names):
    return {name: digest((work / name).read_bytes()) for name in names}


def tree_digest(files):
    return digest(json.dumps(files, sort_keys=True, separators=(',', ':')).encode())


def database_state(work):
    return {p.name: digest(p.read_bytes()) for p in sorted(work.glob('.testmondata*')) if p.is_file()}


def run_arm(work, evidence, name, native):
    out = evidence / (name + '.json')
    env = {'PATH': '/usr/local/bin:/usr/bin:/bin', 'HOME': '/tmp', 'LANG': 'C.UTF-8',
           'PYTHONPATH': str(work / 'src') + ':/opt/replay/runtime',
           'PYTHONDONTWRITEBYTECODE': '1', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1',
           'STUDY_OBSERVER_OUTPUT': str(out)}
    args = [sys.executable, '-B', '-m', 'pytest', '-p', 'evidence_observer']
    if native:
        args += ['-p', 'testmon.pytest_testmon', '--testmon']
    args += ['tests/test_utils.py', '-q', '-ra', '--tb=short']
    result = subprocess.run(args, cwd=work, env=env, text=True, capture_output=True, timeout=90)
    require(out.is_file(), name + ' did not produce an observer report: ' + result.stderr[:1200])
    obs = json.loads(out.read_text())
    require(obs['exit_status'] == result.returncode, name + ' exit mismatch')
    require(obs['requests_import'] == str(work / 'src/requests/__init__.py'), name + ' imported the wrong Requests')
    obs.update({'process_exit': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr, 'command': args})
    obs['counts'] = {outcome: sum(r['outcome'] == outcome for r in obs['calls']) for outcome in ['passed', 'failed', 'skipped']}
    obs['noncall_errors'] = sum(r['outcome'] == 'failed' for r in obs['other_reports']) + len(obs['collection_errors']) + len(obs['internal_errors'])
    obs['infrastructure_eligible'] = result.returncode in (0, 1) and obs['noncall_errors'] == 0
    obs['setup_skips'] = sum(r['when'] == 'setup' and r['outcome'] == 'skipped' for r in obs['other_reports'])
    return obs


def main():
    status = dict(line.split(':', 1) for line in Path('/proc/self/status').read_text().splitlines() if ':' in line)
    runtime = {'uid': os.getuid(), 'gid': os.getgid(), 'cap_eff': status['CapEff'].strip(),
               'no_new_privs': status['NoNewPrivs'].strip(), 'seccomp': status['Seccomp'].strip(),
               'interfaces': sorted(p.name for p in Path('/sys/class/net').iterdir())}
    require(runtime == {'uid': 10001, 'gid': 10001, 'cap_eff': '0000000000000000', 'no_new_privs': '1', 'seccomp': '2', 'interfaces': ['lo']}, 'Runtime isolation mismatch')
    manifest = json.loads((ROOT / 'input-manifest.json').read_text())
    require(digest((ROOT / 'upstream.zip').read_bytes()) == manifest['upstream_archive_sha256'], 'Archive hash mismatch')
    require(digest((ROOT / 'PROTOCOL.md').read_bytes()) == manifest['protocol_sha256'], 'Protocol hash mismatch')
    report = {'schema_version': 1, 'subject': 'psf/requests v2.32.5',
              'upstream_commit': 'b25c87d7cb8d6a18a37fa12442b5f883f9e41741',
              'public_fix_replayed_in_reverse': '96ba401c1296ab1dda74a2365ef36d88f7d144ef',
              'evaluation_set': 'entire unchanged tests/test_utils.py; not entire project suite',
              'security_nodeid': SECURITY, 'python': platform.python_version(), 'runtime': runtime,
              'input_manifest': manifest, 'repetitions': []}
    for repeat in range(1, 4):
        case = Path('/tmp') / ('repeat-' + str(repeat))
        case.mkdir()
        evidence = case / 'evidence'
        evidence.mkdir()
        work = case / 'project'
        work.mkdir()
        with zipfile.ZipFile(ROOT / 'upstream.zip') as archive:
            prefix = archive.namelist()[0].split('/')[0] + '/'
            names = sorted(n[len(prefix):] for n in archive.namelist() if n.startswith(prefix) and not n.endswith('/'))
            for name in names:
                require(not Path(name).is_absolute() and '..' not in Path(name).parts, 'Unsafe archive path')
                target = work / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(prefix + name))
        initial = tree(work, names)
        baseline = run_arm(work, evidence, 'baseline', True)
        require(tree(work, names) == initial, 'Baseline altered original inputs')
        baseline_finished = {r['nodeid'] for r in baseline['calls']} | {r['nodeid'] for r in baseline['other_reports'] if r['when'] == 'setup' and r['outcome'] == 'skipped'}
        require(set(baseline['selected_items']) == baseline_finished and not baseline['deselected'] and not baseline['synthetic_deselected_items'], 'Baseline did not evaluate all original collected tests')
        baseline_ok = baseline['process_exit'] == 0 and baseline['noncall_errors'] == 0 and not baseline['counts']['failed'] and any(r['nodeid'] == SECURITY and r['outcome'] == 'passed' for r in baseline['calls'])
        if not baseline_ok:
            report['repetitions'].append({'repeat': repeat, 'baseline': baseline, 'baseline_eligible': False})
            report['status'] = 'BASELINE_NOT_ELIGIBLE'
            break
        before_db = database_state(work)
        require(before_db, 'Native baseline database missing')
        snapshot = evidence / 'baseline-state'
        snapshot.mkdir()
        for db in work.glob('.testmondata*'):
            if db.is_file():
                shutil.copyfile(db, snapshot / db.name)
        connection = sqlite3.connect(str(work / '.testmondata'))
        require(connection.execute('PRAGMA quick_check').fetchone()[0] == 'ok', 'Invalid baseline database')
        connection.close()
        source = work / 'src/requests/utils.py'
        fixed = b'        host = ri.hostname\n'
        historical = (b'\n        # Strip port numbers from netloc. This weird `if...encode`` dance is\n'
                      b"        # used for Python 3.2, which doesn't support unicode literals.\n"
                      b'        splitstr = b":"\n        if isinstance(url, str):\n'
                      b'            splitstr = splitstr.decode("ascii")\n'
                      b'        host = ri.netloc.split(splitstr)[0]\n')
        original = source.read_bytes()
        require(original.count(fixed) == 1, 'Public historical change does not apply exactly once')
        candidate = original.replace(fixed, historical)
        source.write_bytes(candidate)
        candidate_tree = tree(work, names)
        changes = [name for name in names if candidate_tree[name] != initial[name]]
        require(changes == ['src/requests/utils.py'], 'Candidate changed an unauthorized input')
        require(database_state(work) == before_db, 'Candidate preparation changed baseline state')
        selective = run_arm(work, evidence, 'selective', True)
        require(tree(work, names) == candidate_tree, 'Selective run altered original candidate inputs')
        after_selective_db = database_state(work)
        full = run_arm(work, evidence, 'independent-full', False)
        require(set(full['selected_items']) == set(baseline['selected_items']), 'Independent full test set differs from original baseline')
        require(tree(work, names) == candidate_tree, 'Independent run altered candidate inputs')
        require(database_state(work) == after_selective_db, 'Independent run changed selector state')
        require(database_state(snapshot) == before_db, 'Preserved baseline state changed')
        failing_original = [r for r in full['calls'] if r['nodeid'] == SECURITY and r['outcome'] == 'failed']
        selective_calls = {r['nodeid'] for r in selective['calls']}
        conditions = {'baseline_original_tests_pass': baseline_ok,
                      'nonempty_native_selection_passes': selective['process_exit'] == 0 and selective['noncall_errors'] == 0 and selective['counts']['failed'] == 0 and selective['counts']['passed'] > 0,
                      'independent_original_security_assertion_fails': len(failing_original) == 1 and full['noncall_errors'] == 0,
                      'security_assertion_omitted_by_selection': selective['infrastructure_eligible'] and SECURITY not in selective_calls,
                      'native_selection_has_no_infrastructure_error': selective['infrastructure_eligible'],
                      'candidate_identical_across_selective_and_full': True,
                      'all_original_tests_and_configuration_unchanged': True}
        report['repetitions'].append({'repeat': repeat, 'baseline_eligible': True, 'conditions': conditions,
          'qualifying_joint_witness': all(conditions.values()), 'baseline': baseline, 'selective': selective, 'independent_full': full,
          'baseline_source_tree_sha256': tree_digest(initial), 'candidate_source_tree_sha256': tree_digest(candidate_tree),
          'original_test_file_sha256': initial['tests/test_utils.py'], 'baseline_source_hashes': initial,
          'candidate_changed_hashes': {name: candidate_tree[name] for name in changes},
          'candidate_diff': ''.join(difflib.unified_diff(original.decode().splitlines(keepends=True), candidate.decode().splitlines(keepends=True), fromfile='a/src/requests/utils.py', tofile='b/src/requests/utils.py')),
          'baseline_database_hashes': before_db, 'post_selective_database_hashes': after_selective_db,
          'independent_run_did_not_modify_selector_database': True})
    if 'status' not in report:
        report['status'] = 'INELIGIBLE_SELECTOR_INFRASTRUCTURE_ERROR' if any(not r['selective']['infrastructure_eligible'] for r in report['repetitions']) else ('QUALIFYING_ORIGINAL_TEST_WITNESS' if all(r['qualifying_joint_witness'] for r in report['repetitions']) else 'COMPLETED_NO_QUALIFYING_WITNESS')
    print(json.dumps(report, sort_keys=True))


if __name__ == '__main__':
    main()
