"""Trusted, protected-main-owned research CI runner.

The executable runner and tests are loaded ONLY from the checked-out PR base.
The candidate must match the exact reviewed fixture before any test execution.
Only a fixture constructed from protected-base bytes is executed.
The main-generated testmon database is immutable and SHA-256 authenticated.

Private reproducibility study, not a production security solution.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from fixture_policy import validate_candidate

CASE = 'requests_crlf_header'
TARGET = 'requests/utils.py'
SECURITY = 'tests/test_security.py::test_security_rejects_header_injection'
POSITIVE = 'tests/test_security.py::test_valid_header_passes'
META = 'tests/test_meta.py::test_metadata_build_positive'
WS = Path(os.environ['GITHUB_WORKSPACE']).resolve()
BASE = WS / 'trusted'
ROOT = BASE / 'cases' / CASE
OUT = Path(os.environ['EVIDENCE_DIR']).resolve()
OUT.mkdir(parents=True, exist_ok=True)
BASE_SHA = os.environ['BASE_SHA']


def must(ok: bool, reason: str) -> None:
    if not ok:
        raise RuntimeError(reason)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_head(path: Path) -> str:
    return subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=path, text=True).strip()


def check_base() -> dict:
    must(git_head(BASE) == BASE_SHA, 'trusted checkout does not match PR base')
    manifest = json.loads((BASE / '.experiment' / 'manifest.json').read_text(encoding='utf-8'))
    case = next(c for c in manifest['cases'] if c['name'] == CASE)
    for relative, expected in case['baseline_files'].items():
        must(digest(ROOT / relative) == expected, 'untrusted baseline file: ' + relative)
    return case


def pytest_env(label: str, db: Path | None = None) -> dict:
    env = {name: os.environ[name] for name in
           ('PATH', 'SystemRoot', 'WINDIR', 'TEMP', 'TMP', 'HOME', 'LANG', 'LC_ALL')
           if name in os.environ}
    env.update(PYTEST_DISABLE_PLUGIN_AUTOLOAD='1', PYTHONDONTWRITEBYTECODE='1',
               PYTHONHASHSEED='0', OBSERVER_OUTPUT=str(OUT / (label + '-tests.json')),
               OBSERVER_TARGET_MODULE='requests.utils',
               PYTHONPATH=os.pathsep.join([str(BASE / '.experiment' / 'runtime'), str(ROOT)]))
    if db is not None:
        env['TESTMON_DATAFILE'] = str(db)
    else:
        env.pop('TESTMON_DATAFILE', None)
    return env


def pytest_run(label: str, *, db: Path | None = None, use_testmon: bool = False,
               noselect: bool = False) -> dict:
    cmd = [sys.executable, '-m', 'pytest', '-p', 'observer', '-p', 'no:cacheprovider',
           '-vv', '-s', '--color=no']
    if use_testmon:
        cmd += ['-p', 'testmon.pytest_testmon', '--testmon']
    if noselect:
        cmd.append('--testmon-noselect')
    started = time.perf_counter()
    process = subprocess.run(cmd, cwd=ROOT, env=pytest_env(label, db), capture_output=True,
                             text=True, encoding='utf-8', errors='replace', timeout=180)
    (OUT / (label + '.log')).write_text(process.stdout + '\n' + process.stderr, encoding='utf-8')
    observer_file = OUT / (label + '-tests.json')
    must(observer_file.is_file(), 'missing native pytest observer: ' + label)
    observation = json.loads(observer_file.read_text(encoding='utf-8'))
    called = [{'id': r['nodeid'], 'outcome': r['outcome']}
              for r in observation['reports'] if r['when'] == 'call']
    # Skipped call reports are not evidence of a real passing/failing test.
    executed = [r for r in called if r['outcome'] in ('passed', 'failed')]
    passed = [r for r in executed if r['outcome'] == 'passed']
    must(observation['final_exitstatus'] == process.returncode, 'pytest exitcode discrepancy')
    must(not observation['collection_errors'], 'pytest collection failure')
    must(not any(r['outcome'] == 'failed' and r['when'] != 'call'
                 for r in observation['reports']), 'pytest setup/teardown failure')
    must(observation['initial_exitstatus'] in (0, 1, 5), 'pytest infrastructure failure')
    return {'exit': process.returncode, 'selected_count': len(executed),
            'call_report_count': len(called), 'passed_count': len(passed),
            'called': called, 'initial_exit': observation.get('initial_exitstatus'),
            'elapsed_seconds': round(time.perf_counter() - started, 6),
            'log': label + '.log'}


def generate() -> int:
    case = check_base()
    cache = OUT / 'main.testmondata'
    obs = pytest_run('baseline', db=cache, use_testmon=True, noselect=True)
    must(obs['exit'] == 0 and obs['selected_count'] == 3 and obs['passed_count'] == 3,
         'trusted baseline failed')
    must(all(x['outcome'] == 'passed' for x in obs['called']), 'failing baseline test')
    must(cache.is_file() and cache.stat().st_size > 5000, 'no native testmon DB')
    manifest = {'base_sha': BASE_SHA, 'case': CASE, 'target': TARGET,
                'target_sha256': case['baseline_files'][TARGET],
                'requirements_sha256': digest(BASE / '.experiment' / 'requirements.lock'),
                'database_sha256': digest(cache), 'baseline': obs}
    (OUT / 'cache-manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps({'result': 'protected-main-baseline-generated',
                      'base_sha': BASE_SHA, 'database_sha256': manifest['database_sha256']}))
    return 0


def load_candidate() -> tuple[dict, bytes, bytes, Path]:
    case = check_base()
    candidate_repo = WS / 'candidate'
    source = ROOT / TARGET
    original = source.read_bytes()
    altered = validate_candidate(BASE, candidate_repo, BASE_SHA, os.environ['HEAD_SHA'],
                                 original, BASE / 'research_20261107' / 'reviewed_fixture.json')
    # Do not execute bytes read from the PR worktree. The validator returns the
    # protected-base fixture after proving exact parity with the candidate blob.
    return case, original, altered, source


def evaluate(mode: str) -> int:
    case, original, altered, source = load_candidate()
    result = {'mode': mode, 'base_sha': BASE_SHA, 'head_sha': os.environ['HEAD_SHA'],
              'target': TARGET, 'baseline_source_sha256': hashlib.sha256(original).hexdigest(),
              'candidate_source_sha256': hashlib.sha256(altered).hexdigest(),
              'baseline_generated_in_this_job': False,
              'execution_source': 'protected-base reviewed fixture; candidate Git blob byte-identical',
              'threat_model': 'fixed reviewed fixture; arbitrary candidate Python rejected'}
    if mode == 'validate':
        (OUT / 'source-policy.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        print(json.dumps(result))
        return 0
    source.write_bytes(altered)
    if mode == 'selective':
        artifact = Path(os.environ['CACHE_DIR']).resolve()
        manifest = json.loads((artifact / 'cache-manifest.json').read_text(encoding='utf-8'))
        baseline_db = artifact / 'main.testmondata'
        must(manifest['base_sha'] == BASE_SHA, 'cache belongs to another main revision')
        must(manifest['target_sha256'] == case['baseline_files'][TARGET], 'cache source mismatch')
        must(manifest['requirements_sha256'] == digest(BASE / '.experiment' / 'requirements.lock'),
             'cache dependency lock mismatch')
        must(manifest['database_sha256'] == digest(baseline_db), 'cache SHA-256 mismatch')
        db = OUT / 'working.testmondata'
        shutil.copyfile(baseline_db, db)
        must(digest(db) == manifest['database_sha256'], 'cache restore mismatch')
        obs = pytest_run('selective', db=db, use_testmon=True)
        expected_calls = [{'id': POSITIVE, 'outcome': 'passed'}]
        accepted = obs['exit'] == 0 and obs['called'] == expected_calls
        result.update(native_testmon=obs, trusted_cache_sha256=manifest['database_sha256'],
                      accepted=accepted)
        (OUT / 'result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        print(json.dumps({'result': 'native-testmon-selection', 'exit': obs['exit'],
                          'selected_count': obs['selected_count'], 'calls': obs['called'],
                          'cache_sha256': manifest['database_sha256']}))
        # Reject zero-test and skip-only passes. Require a passing call report.
        return 0 if accepted else 1
    if mode == 'full':
        obs = pytest_run('full')
        result.update(full_suite=obs, security_test_failed=any(
            x['id'] == SECURITY and x['outcome'] == 'failed' for x in obs['called']))
        must({x['id'] for x in obs['called']} == {META, POSITIVE, SECURITY},
             'full diagnostic did not execute the complete trusted test set')
        must(obs['exit'] == 1 and result['security_test_failed'],
             'reviewed fixture did not produce the expected security failure')
        (OUT / 'result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        print(json.dumps({'result': 'full-suite-diagnostic', 'exit': obs['exit'],
                          'security_test_failed': result['security_test_failed']}))
        return obs['exit']
    if mode == 'guard':
        started = time.perf_counter()
        changed = ast.dump(ast.parse(original), include_attributes=False) != ast.dump(
            ast.parse(altered), include_attributes=False)
        seconds = round(time.perf_counter() - started, 6)
        result.update(ast_change=changed, ast_scan_seconds=seconds)
        obs = pytest_run('guarded_full') if changed else {'exit': 0, 'selected_count': 0, 'called': []}
        must(changed and obs['exit'] == 1 and
             {x['id'] for x in obs['called']} == {META, POSITIVE, SECURITY} and
             any(x['id'] == SECURITY and x['outcome'] == 'failed' for x in obs['called']),
             'AST diagnostic did not detect the reviewed security regression')
        result['guarded_full'] = obs
        (OUT / 'result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        print(json.dumps({'result': 'fail-closed-ast-check', 'ast_change': changed,
                          'scan_seconds': seconds, 'exit': obs['exit']}))
        return obs['exit']
    raise RuntimeError('invalid mode: ' + mode)


if __name__ == '__main__':
    action = sys.argv[1] if len(sys.argv) > 1 else ''
    try:
        status = generate() if action == 'generate' else evaluate(action)
    except Exception as e:
        print('TRUSTED_CI_FAIL_CLOSED: ' + str(e), file=sys.stderr)
        status = 2
    raise SystemExit(status)
