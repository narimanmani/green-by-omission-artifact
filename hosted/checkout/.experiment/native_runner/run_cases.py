"""Run exact recovered case snapshots; refuses absent inputs or dirty histories.

Manifest: {'cases':[{'name':..., 'baseline_dir':..., 'source_relative':...,
                   'ordinary_source':..., 'collision_source':...,
                   'security_nodeids': [...], 'expected_import_origins': [...]}]}.
Paths are relative to manifest parent. Use only original recovered snapshots.
"""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import zlib

HOME = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def inventory(repo):
    return {p.relative_to(repo).as_posix(): sha(p) for p in repo.rglob('*') if p.is_file() and '.git' not in p.relative_to(repo).parts and '__pycache__' not in p.parts and '.pytest_cache' not in p.parts}

def passed_security(row, expected):
    reports = row['observer'].get('reports',[])
    return all(any(r['nodeid'] == node and r['when'] == 'call' and r['outcome'] == 'passed' for r in reports) for node in expected)

def failed_security(row, expected, patterns):
    return [r['nodeid'] for r in row['observer'].get('reports',[]) if r['nodeid'] in expected and r['when'] == 'call' and r['outcome'] == 'failed' and any(re.search(pattern, r.get('failure_text','')) for pattern in patterns)]

def usable(row):
    observed = row['observer']
    return bool(observed) and observed.get('import_origins_valid',False) and not row['analysis_error'] and not row['clean_status_after'] and not observed.get('collection_errors') and not any(r['outcome'] == 'failed' and r['when'] != 'call' for r in observed.get('reports',[]))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--output', type=Path, default=HOME / 'case_results')
    args = parser.parse_args()
    manifest = args.manifest.resolve()
    spec = json.loads(manifest.read_text(encoding='utf-8'))
    for case in spec['cases']:
        if not case.get('security_nodeids') or not all(isinstance(n,str) and '::' in n for n in case['security_nodeids']):
            raise ValueError('Each case requires exact security_nodeids from the original tests')
        rules = case.get('expected_import_origins',[])
        if not rules or any(not rule.get('module') or (('relative_path' in rule) == ('relative_prefix' in rule)) for rule in rules):
            raise ValueError('Each case requires module names and exactly one relative_path or relative_prefix per import-origin rule')
        if not any(rule.get('relative_path') == case['source_relative'] for rule in rules):
            raise ValueError('An exact import-origin rule must cover the changed source file')
        for rule in rules:
            relative = Path(rule.get('relative_path',rule.get('relative_prefix','')))
            if relative.is_absolute() or '..' in relative.parts:
                raise ValueError('Import-origin expectations must stay within the copied case repository')
        for pattern in case.get('expected_security_failure_patterns',['AssertionError','DID NOT RAISE']):
            re.compile(pattern)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    shutil.copy2(manifest, output / 'input-manifest.json')
    results = []
    validations = []
    for case in spec['cases']:
        name = case['name']
        base = (manifest.parent / case['baseline_dir']).resolve()
        ordinary = (manifest.parent / case['ordinary_source']).resolve()
        collision = (manifest.parent / case['collision_source']).resolve()
        assert base.is_dir() and ordinary.is_file() and collision.is_file(), f'Missing exact case inputs: {name}'
        repo = output / name / 'repo'
        repo.parent.mkdir(parents=True)
        shutil.copytree(base, repo, ignore=shutil.ignore_patterns('.git','__pycache__','.pytest_cache','.testmondata*'))
        log = []
        def command(cmd, *, env=None):
            start = time.time()
            p = subprocess.run(cmd, cwd=repo, env=env, capture_output=True, text=True, encoding='utf-8', errors='replace')
            log.append({'command':cmd, 'returncode':p.returncode, 'stdout':p.stdout, 'stderr':p.stderr, 'seconds':time.time()-start})
            (repo.parent/'commands.json').write_text(json.dumps(log,indent=2),encoding='utf-8')
            return p
        def git(*argv):
            p = command(['git',*argv])
            assert p.returncode == 0, p.stderr
            return p.stdout.strip()
        git('init','-b','main')
        git('config','user.name','Private native selector research')
        git('config','user.email','research@example.invalid')
        git('config','core.autocrlf','false')
        # Ignore generated execution state without changing case source or tests.
        (repo/'.git/info/exclude').write_text('__pycache__/\n.pytest_cache/\n.testmondata*\n',encoding='utf-8')
        git('add','.')
        git('commit','-m','Exact recovered trusted baseline')
        baseline_sha = git('rev-parse','HEAD')
        git('update-ref','refs/remotes/origin/main',baseline_sha)
        source = repo / case['source_relative']
        assert source.is_file()
        baseline_source = source.read_bytes()
        baseline_inventory = inventory(repo)
        first_case_result = len(results)
        for condition in ['baseline_nochange','benign_comment','ordinary','collision']:
            git('switch','--detach',baseline_sha)
            if condition != 'baseline_nochange':
                git('switch','-c',condition)
                payload = baseline_source + b'\n# Benign comment-only control.\n' if condition == 'benign_comment' else (ordinary if condition == 'ordinary' else collision).read_bytes()
                source.write_bytes(payload)
                git('add','--',case['source_relative'])
                git('commit','-m',f'Original {condition} source snapshot' if condition != 'benign_comment' else 'Benign comment control')
            changed = git('diff','--name-only','main...HEAD').splitlines()
            assert changed == ([] if condition == 'baseline_nochange' else [case['source_relative']]), changed
            assert not git('status','--porcelain=v1'), 'Dirty input checkout'
            current_inventory = inventory(repo)
            unchanged = all(current_inventory.get(p) == digest for p,digest in baseline_inventory.items() if p != case['source_relative'])
            assert unchanged, 'Non-source case files changed'
            revision = git('rev-parse','HEAD')
            for mode in ['native_default','native_fallback','full_suite']:
                stem = f'{condition}-{mode}'
                evidence = repo.parent / f'{stem}.json'
                env = dict(os.environ)
                for key in ['PYTEST_ADDOPTS','PYTEST_PLUGINS','GITHUB_EVENT_NAME']:
                    env.pop(key,None)
                env.update(PYTHONPATH=str(SCRIPTS), PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1', NATIVE_EVIDENCE_JSON=str(evidence), PYTHONHASHSEED='0', NATIVE_CASE_ROOT=str(repo), NATIVE_EXPECTED_IMPORT_ORIGINS=json.dumps(case['expected_import_origins']))
                cmd = [sys.executable,'-m','pytest','-p','native_capture','-vv','-s','--color=no']
                if mode != 'full_suite':
                    cmd += ['--depper','--depper-base-branch=main','--depper-debug']
                    if mode == 'native_fallback': cmd += ['--depper-run-all-on-error']
                p = command(cmd, env=env)
                (repo.parent/f'{stem}.log').write_text(p.stdout+p.stderr, encoding='utf-8')
                observed = json.loads(evidence.read_text(encoding='utf-8')) if evidence.exists() else {}
                result = {'case':name,'condition':condition,'mode':mode,'exit':p.returncode,'baseline_sha':baseline_sha,'head_sha':revision,'changed_files':changed,'non_source_files_unchanged':unchanged,'clean_status_after':git('status','--porcelain=v1'),'source_sha256':sha(source),'source_crc32':f'{zlib.crc32(source.read_bytes()):08x}','observer':observed,'native_plugin_loaded':'depper-0.2.0' in p.stdout,'log':f'{name}/{stem}.log'}
                result['analysis_error'] = any(s in p.stdout+p.stderr for s in ['Warning: Git command failed','Warning: Git diff failed','Error during dependency analysis','INTERNALERROR','ERROR collecting'])
                result['changed_source_detected'] = condition == 'baseline_nochange' or f"  - {case['source_relative']}" in p.stdout
                result['fallback_reported'] = 'Running all tests' in p.stdout
                result['valid_execution'] = usable(result) and (mode == 'full_suite' or result['native_plugin_loaded']) and p.returncode in [0,1,5]
                results.append(result)
                (output/'results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
        git('switch','--detach',baseline_sha)
        git('bundle','create',str(repo.parent/'history.bundle'),'--all')
        case_rows = results[first_case_result:]
        by_key = {(r['condition'],r['mode']):r for r in case_rows}
        security = case['security_nodeids']
        patterns = case.get('expected_security_failure_patterns',['AssertionError','DID NOT RAISE'])
        controls = {}
        for condition in ['baseline_nochange','benign_comment']:
            row = by_key[(condition,'full_suite')]
            controls[f'{condition}_full_suite_passes_security'] = usable(row) and row['exit'] == 0 and passed_security(row,security)
        for condition in ['ordinary','collision']:
            row = by_key[(condition,'full_suite')]
            controls[f'{condition}_full_suite_fails_security_assertion'] = usable(row) and row['exit'] == 1 and bool(failed_security(row,security,patterns))
        controls['all_runs_have_valid_execution_and_import_origins'] = all(r['valid_execution'] for r in case_rows)
        controls['native_changed_source_detected'] = all(r['changed_source_detected'] for r in case_rows if r['mode'] != 'full_suite')
        valid = all(controls.values())
        interpretations = {}
        for condition in ['ordinary','collision']:
            row = by_key[(condition,'native_default')]
            failed = failed_security(row,security,patterns)
            executed = set(row['observer'].get('executed_tests',[]))
            full_failed = set(failed_security(by_key[(condition,'full_suite')],security,patterns))
            if not valid:
                interpretation = 'INVALID_CONTROLS_OR_EXECUTION: no research conclusion'
            elif row['fallback_reported']:
                interpretation = 'FALLBACK_EXECUTION: inspect logs; not native selective-bypass evidence'
            elif failed and row['exit'] == 1:
                interpretation = 'DETECTED: native selector executed and failed a security assertion'
            elif row['exit'] == 0 and full_failed.isdisjoint(executed):
                interpretation = 'CANDIDATE_OMISSION: successful native process omitted full-suite-failing security tests; inspect platform and dependency evidence'
            else:
                interpretation = 'OTHER_NATIVE_OUTCOME: inspect recorded security-test outcomes and exit status'
            interpretations[condition] = interpretation
        validations.append({'case':name,'status':'CONTROLS_PASSED_REVIEW_REQUIRED' if valid else 'INVALID','controls':controls,'native_interpretations':interpretations,'fingerprint_validation':'NOT_PERFORMED: whole-file CRC32 does not establish testmon fingerprint preservation'})
        (output/'validation.json').write_text(json.dumps(validations,indent=2),encoding='utf-8')
    with (output/'results.csv').open('w',newline='',encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['case','condition','mode','exit','baseline_sha','head_sha','native_plugin_loaded','analysis_error','non_source_files_unchanged','source_sha256','source_crc32','log'])
        writer.writeheader()
        writer.writerows({k:r[k] for k in writer.fieldnames} for r in results)
    print(json.dumps({'runs':len(results),'output':str(output),'validations':validations},indent=2))
    if any(v['status'] == 'INVALID' for v in validations):
        raise SystemExit(2)

if __name__ == '__main__': main()
