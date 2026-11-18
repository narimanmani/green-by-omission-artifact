"""Execute private hosted baseline and original source-only PR experiments.

Run this script and observer.py from a trusted copy outside the Git checkout.
Requires MODE, BASE_SHA, HEAD_SHA, FROZEN_BOOTSTRAP_BASE and EVIDENCE_DIR.
REPO_DIR optionally identifies the checkout (otherwise the current Git root).
The caller must install the trusted dependency lock before invocation.
"""
from contextlib import closing
import hashlib
import importlib.metadata as metadata
import json
import os
from pathlib import Path, PurePosixPath
import platform
import shutil
import sqlite3
import subprocess
import sys
import time

RUNTIME = Path(__file__).resolve().parent
EVIDENCE = Path(os.environ['EVIDENCE_DIR']).resolve()
EVIDENCE.mkdir(parents=True,exist_ok=True)
MODE = os.environ['MODE']
BASE = os.environ['BASE_SHA']
HEAD = os.environ['HEAD_SHA']
REPO = Path(os.environ.get('REPO_DIR') or subprocess.check_output(
    ['git','rev-parse','--show-toplevel'],text=True).strip()).resolve()
SUMMARY = {'status':'NOT_RUN','mode':MODE,'base_sha':BASE,'head_sha':HEAD,
           'cases':[],'commands':[]}

def save():
    (EVIDENCE/'summary.json').write_text(json.dumps(SUMMARY,indent=2),encoding='utf-8')

def require(condition,message):
    if not condition:
        raise RuntimeError(message)

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def safe(parent,value):
    path = PurePosixPath(value)
    require(not path.is_absolute() and bool(path.parts) and '..' not in path.parts
            and '.git' not in path.parts,'Unsafe manifest path')
    actual = (parent/str(path)).resolve()
    require(actual.is_relative_to(parent.resolve()),'Manifest path leaves trusted root')
    return actual

def git(*args):
    command = ['git',*args]
    p = subprocess.run(command,cwd=REPO,text=True,capture_output=True,encoding='utf-8')
    SUMMARY['commands'].append({'args':command,'exit':p.returncode,
                                 'stdout':p.stdout,'stderr':p.stderr})
    save()
    require(p.returncode == 0,f'Git command failed: {command}: {p.stderr}')
    return p.stdout.strip()

def verify_inventory(case,source_hash=None):
    root = safe(REPO,case['dir'])
    require(root.is_dir(),'Case directory missing')
    files = {p.relative_to(root).as_posix():p for p in root.rglob('*') if p.is_file()}
    require(set(files) == set(case['baseline_files']),
            f"Case inventory changed: {case['name']}")
    for relative,path in files.items():
        require(not path.is_symlink(),'Symlink in original case')
        expected = source_hash if relative == case['target'] and source_hash else case['baseline_files'][relative]
        require(digest(path) == expected,f'Unexpected case bytes: {relative}')
    return root

def calls(observed):
    return [r for r in observed['reports'] if r['when'] == 'call']

def validate_observation(observed,case,case_root,must_import=False):
    require(not observed['collection_errors'],'Pytest collection error')
    require(not [r for r in observed['reports'] if r['when'] != 'call' and r['outcome'] == 'failed'],
            'Pytest setup/teardown failure')
    origin = observed['target_module']
    if must_import:
        require(origin['loaded'],'Security application module was not imported')
    if origin['loaded']:
        require(origin['file'] is not None and Path(origin['file']).resolve() == safe(case_root,case['target']),
                'Application imported from unexpected source')

def pytest_run(case,case_root,label,output,working_db,kind):
    env = dict(os.environ)
    for key in ('PYTEST_ADDOPTS','PYTEST_PLUGINS'):
        env.pop(key,None)
    env.update(PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',PYTHONDONTWRITEBYTECODE='1',
               PYTHONHASHSEED='0',PYTHONIOENCODING='utf-8',
               PYTHONPATH=os.pathsep.join([str(RUNTIME),str(case_root)]),
               TESTMON_DATAFILE=str(working_db),
               OBSERVER_OUTPUT=str(output/f'{label}-tests.json'),
               OBSERVER_TARGET_MODULE=case['module'])
    args = [sys.executable,'-m','pytest','-p','observer','-p','no:cacheprovider',
            '-vv','-s','--color=no']
    if kind in ('baseline','selective'):
        args += ['-p','testmon.pytest_testmon','--testmon']
        if kind == 'baseline':
            args += ['--testmon-noselect']
    start = time.monotonic()
    p = subprocess.run(args,cwd=case_root,env=env,text=True,capture_output=True,
                       encoding='utf-8',errors='replace',timeout=300)
    (output/f'{label}.log').write_text(p.stdout+p.stderr,encoding='utf-8')
    observation_path = output/f'{label}-tests.json'
    require(observation_path.is_file(),'Pytest observer evidence missing')
    observed = json.loads(observation_path.read_text(encoding='utf-8'))
    require(observed['final_exitstatus'] == p.returncode,'Observer/process exit mismatch')
    validate_observation(observed,case,case_root,must_import=(kind in ('baseline','full')))
    require(p.returncode in (0,1),'Invalid pytest outcome (interruption/configuration/no-tests error)')
    return {'exit':p.returncode,'seconds':time.monotonic()-start,'args':args,
            'log':str((output/f'{label}.log').relative_to(EVIDENCE)), 'tests':observed}

def baseline(case):
    case_root = verify_inventory(case)
    output = EVIDENCE/case['name']
    output.mkdir(parents=True,exist_ok=False)
    working_db = output/'working.testmondata'
    result = pytest_run(case,case_root,'baseline',output,working_db,'baseline')
    require(result['exit'] == 0,'Trusted baseline failed')
    called = calls(result['tests'])
    require(len(called) == case['expected_test_count'] == 3,'Baseline did not execute all three tests')
    require(all(r['outcome'] == 'passed' for r in called),'Baseline call was not passing')
    require(case['security_nodeid'] in {r['nodeid'] for r in called},'Baseline security test missing')
    require(working_db.is_file(),'Native testmon baseline database missing')
    snapshot = output/'trusted-baseline.testmondata'
    with closing(sqlite3.connect(working_db)) as src, closing(sqlite3.connect(snapshot)) as dst:
        src.backup(dst)
    snapshot_hash = digest(snapshot)
    snapshot.chmod(0o444)
    verify_inventory(case)
    return case_root,output,working_db,snapshot,snapshot_hash,result

def main():
    require(MODE in ('bootstrap','selective','full'),'Unsupported mode')
    require(not RUNTIME.is_relative_to(REPO),'Runtime must be copied outside checkout')
    require(not EVIDENCE.is_relative_to(REPO),'Evidence must be outside checkout')
    require((RUNTIME/'observer.py').is_file(),'Trusted external observer missing')
    versions = {name:metadata.version(name) for name in ['pytest','pytest-testmon','coverage',
                                                       'itsdangerous','starlette','requests','httpx']}
    require(versions['pytest']=='9.0.2' and versions['pytest-testmon']=='2.3.0','Wrong native selector versions')
    SUMMARY.update(versions=versions,python=sys.version,platform=platform.platform(),
                   repo_dir=str(REPO),runtime_sha256=digest(Path(__file__)),
                   runner_environment={key:os.environ.get(key) for key in (
                       'ImageOS','ImageVersion','RUNNER_OS','GITHUB_RUN_ID',
                       'GITHUB_RUN_ATTEMPT','GITHUB_WORKFLOW_REF','GITHUB_WORKFLOW_SHA',
                       'GITHUB_SHA','GITHUB_REF')})
    require(not git('status','--porcelain=v1','--untracked-files=no'),'Dirty tracked checkout')
    initial = git('rev-parse','HEAD')
    require(initial == (HEAD if MODE == 'bootstrap' else BASE),'Unexpected initial checkout SHA')
    spec = json.loads((REPO/'.experiment/manifest.json').read_text(encoding='utf-8'))
    require(spec.get('status')=='EXACT_ARCHIVE_VERIFIED','Original archive status is not verified')
    archive_hash = spec.get('original_archive_sha256','')
    require(isinstance(archive_hash,str) and len(archive_hash)==64
            and all(character in '0123456789abcdef' for character in archive_hash),
            'Original archive SHA256 must be 64 lowercase hexadecimal characters')
    SUMMARY['original_archive_sha256'] = archive_hash
    require(len(spec['cases']) == 3,'Expected exactly three recovered original cases')
    SUMMARY['manifest'] = spec
    if MODE == 'bootstrap':
        require(BASE == os.environ['FROZEN_BOOTSTRAP_BASE'],'Bootstrap allowed only for immutable initial base')
        for case in spec['cases']:
            _,_,_,snapshot,snapshot_hash,result = baseline(case)
            SUMMARY['cases'].append({'case':case['name'],'baseline':result,
                                      'baseline_database_sha256':snapshot_hash,
                                      'baseline_snapshot_unchanged':digest(snapshot)==snapshot_hash})
            save()
        SUMMARY.update(status='VALID_BOOTSTRAP_BASELINES',actual_exit=0)
        save()
        return 0
    require(BASE != os.environ['FROZEN_BOOTSTRAP_BASE'],'Experiment cannot use pre-bootstrap base')
    require(git('merge-base',BASE,HEAD) == BASE,'PR is not based on trusted baseline')
    require(git('rev-list','--count',f'{BASE}..{HEAD}') == '1','Require exactly one committed source change')
    changes = git('diff','--name-status','--no-renames',BASE,HEAD).splitlines()
    require(len(changes)==1 and changes[0].startswith('M\t'),'Require exactly one modified source file')
    changed_path = changes[0].split('\t',1)[1]
    matching = [c for c in spec['cases'] if str(PurePosixPath(c['dir'])/c['target']) == changed_path]
    require(len(matching)==1,'Modified source is not allowlisted')
    case = matching[0]
    for revision in (BASE,HEAD):
        entry = git('ls-tree',revision,'--',changed_path).split()
        require(entry[:2]==['100644','blob'],'Source type or mode changed')
    case_root,output,working_db,snapshot,snapshot_hash,base_result = baseline(case)
    (EVIDENCE/'pr.diff').write_text(git('diff','--binary',BASE,HEAD),encoding='utf-8')
    git('checkout','--detach',HEAD)
    source_hash = digest(safe(case_root,case['target']))
    conditions = [name for name,value in case['revision_source_sha256'].items() if value==source_hash]
    require(len(conditions)==1,'Candidate is not a recorded original revision/control')
    condition = conditions[0]
    require(condition in ('ordinary','collision','benign_comment'),'Unsupported original revision')
    verify_inventory(case,source_hash)
    for entry in spec['cases']:
        if entry['name'] != case['name']:
            verify_inventory(entry)
    working_db.unlink()
    for suffix in ('-wal','-shm'):
        sidecar = Path(str(working_db)+suffix)
        if sidecar.exists():
            sidecar.unlink()
    shutil.copyfile(snapshot,working_db)
    require(digest(working_db)==snapshot_hash,'Trusted baseline restore hash mismatch')
    result = pytest_run(case,case_root,MODE,output,working_db,MODE)
    require(digest(snapshot)==snapshot_hash,'Trusted snapshot changed')
    require(not git('status','--porcelain=v1','--untracked-files=no'),'Tracked inputs mutated')
    verify_inventory(case,source_hash)
    called = calls(result['tests'])
    security_failed = any(r['nodeid']==case['security_nodeid'] and r['outcome']=='failed' for r in called)
    if MODE=='full':
        require(len(called)==case['expected_test_count']==3,'Full suite did not execute all three tests')
        if condition in ('ordinary','collision'):
            require(result['exit']==1 and security_failed,'Full security oracle did not detect original regression')
        else:
            require(result['exit']==0 and all(r['outcome']=='passed' for r in called),'Benign control full suite failed')
    SUMMARY['cases'].append({'case':case['name'],'condition':condition,'changed_files':[changed_path],
                              'source_sha256':source_hash,'baseline':base_result,'result':result,
                              'baseline_database_sha256':snapshot_hash,
                              'baseline_snapshot_unchanged':True,'security_failed':security_failed,
                              'security_executed':case['security_nodeid'] in {r['nodeid'] for r in called},
                              'non_source_files_unchanged':True})
    SUMMARY.update(status='VALID_EXECUTION',actual_exit=result['exit'])
    save()
    return result['exit']

if __name__=='__main__':
    try:
        exitcode = main()
    except Exception as error:
        SUMMARY.update(status='INVALID_OR_NOT_RUN',error=str(error),actual_exit=2)
        save()
        raise
    sys.exit(exitcode)
