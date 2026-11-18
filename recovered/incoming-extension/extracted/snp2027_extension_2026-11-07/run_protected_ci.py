#!/usr/bin/env python3
"""Isolated, honest emulation of a protected-main PR required CI status.

Uses untouched release-tagged upstream testmon and real pytest executions.
Does NOT execute hosted GitHub Actions or assert hosted branch protection was configured.
"""
from __future__ import annotations
import csv, hashlib, importlib.metadata, json, os, platform, re, shutil, subprocess, sys, time
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent
FIX = ROOT/'fixtures'; SOURCE = ROOT/'upstream'; OUT = ROOT/'outputs'
CASES = {
 'itsdangerous_expiry':('itsdangerous/timed.py','test_security_rejects_expired'),
 'starlette_trusted_host':('starlette/middleware/trustedhost.py','test_security_rejects_untrusted_host'),
 'requests_crlf_header':('requests/utils.py','test_security_rejects_header_injection'),
}
VERSIONS = ['ordinary','collision']

def h(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def cli(cwd,args,tag,env=None,timeout=180):
    t=time.monotonic(); e={**os.environ,'PYTHONPATH':str(cwd)+os.pathsep+str(SOURCE),
     'PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1','PYTHONDONTWRITEBYTECODE':'1','CI':'true',
     'GITHUB_EVENT_NAME':'pull_request','GITHUB_BASE_REF':'main','GITHUB_HEAD_REF':'contributor-security-fix'}
    if env:e.update(env)
    cmd=[str(x) for x in args]
    p=subprocess.run(cmd,cwd=cwd,capture_output=True,text=True,timeout=timeout,env=e)
    path=OUT/'logs'/f'{tag}.log';path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(f'COMMAND: {cmd!r}\nEXIT: {p.returncode}\nSECONDS: {time.monotonic()-t:.6f}\n--- stdout ---\n{p.stdout}\n--- stderr ---\n{p.stderr}')
    return {'exit':p.returncode,'seconds':round(time.monotonic()-t,4),'stdout':p.stdout,
           'stderr':p.stderr,'log':str(path.relative_to(ROOT)),
           'collect_count':int((re.findall(r'collected (\d+) item',p.stdout) or ['-1'])[-1])}

def git(cwd,*args):
    p=subprocess.run(['git',*args],cwd=cwd,capture_output=True,text=True)
    if p.returncode:raise RuntimeError(f'git {args} failed {p.stderr}')
    return p.stdout.strip()

def make_case(name,variant):
    src=FIX/f'{name}_copy_';p=OUT/'workspaces'/name/variant
    if p.exists():shutil.rmtree(p)
    p.parent.mkdir(parents=True,exist_ok=True)
    shutil.copytree(src,p,ignore=shutil.ignore_patterns('snapshots','*.pyc','__pycache__','.coverage','.pytest_cache','.testmondata','*.db','result.json'))
    target, _=CASES[name]
    shutil.copyfile(src/'snapshots/baseline.py',p/target)
    (p/'build_meta.py').write_text('def version():\n    return 1\n')
    (p/'pytest.ini').write_text('[pytest]\ntestpaths = tests\naddopts = -rA\n')
    git(p,'init','-q','-b','main');git(p,'config','user.name','Local PR researcher');git(p,'config','user.email','notreal@example.invalid')
    git(p,'add','.');git(p,'commit','-qm','trusted main baseline')
    return src,p, target

def execute():
    OUT.mkdir(parents=True,exist_ok=True)
    steps=yaml.safe_load((ROOT/'ci_workflows/required-tests.yml').read_text())['jobs']['affected-tests']['steps']
    trusted_command=next(s['run'] for s in steps if s['name']=='Required impacted-tests check')
    assert trusted_command=='python -m pytest -p testmon.pytest_testmon --testmon -vv'
    hashes={p.name:git_hash(p) for p in (SOURCE/'testmon').glob('*.py')}
    assert hashes['__init__.py']=='5f1916b599db224d364f97b4ed84568f45898fcd'
    rows=[]
    for name in ([os.environ["CASE_FILTER"]] if os.environ.get("CASE_FILTER") else CASES):
      for variant in VERSIONS:
        src,p,target=make_case(name,variant)
        label=f'{name}/{variant}'
        baseline=cli(p,[sys.executable,'-m','pytest','-p','testmon.pytest_testmon','--testmon','-vv'],label+'/base')
        assert baseline['exit']==0,(label,baseline['log'])
        # Only trusted main stage can store this artifact. Attacker has no writable path to it.
        trust=OUT/'trusted_main_artifacts'/name/variant/'baseline.testmondata';trust.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(p/'.testmondata',trust)
        stored_hash=h(trust)
        # Create PR branch: modifies app and the same harmless metadata used in prior experiments.
        git(p,'checkout','-qb','pr/candidate');shutil.copyfile(src/f'snapshots/{variant}.py',p/target)
        (p/'build_meta.py').write_text('def version():\n    return 2\n')
        git(p,'add',target,'build_meta.py');git(p,'commit','-qm','PR candidate source-only modification')
        changed=git(p,'diff','--name-only','main...HEAD').splitlines()
        allowed=set((target,'build_meta.py'))
        policy=bool(changed) and set(changed)<=allowed and all(not c.startswith('tests/') for c in changed)
        tests_identical=all(h(src/'tests'/fn.name)==h(fn) for fn in (p/'tests').glob('test_*.py'))
        upstream_original=all(git_hash(SOURCE/'testmon'/fn)==gid for fn,gid in hashes.items())
        assert policy and tests_identical and upstream_original
        # The PR checkout is not permitted to contribute/rewrite the trusted baseline artifact.
        shutil.copyfile(trust,p/'.testmondata');attested=h(p/'.testmondata')==stored_hash
        assert attested
        selective=cli(p,[sys.executable,'-m','pytest','-p','testmon.pytest_testmon','--testmon','-vv'],label+'/required_selective')
        # Independent audit process evaluates complete, unchanged suite on exact PR commit.
        audit=cli(p,[sys.executable,'-m','pytest','-vv'],label+'/independent_full_suite')
        assert h(trust)==stored_hash
        shutil.copyfile(trust,p/'.testmondata')
        noselect=cli(p,[sys.executable,'-m','pytest','-p','testmon.pytest_testmon','--testmon-noselect','-vv'],label+'/defense_noselect')
        guard=dict(
          no_test_changes=tests_identical,
          trusted_baseline_attested=attested,
          immutable_source_plugin=upstream_original,
          pr_only_allowed_paths=policy,
          baseline_clean=baseline['exit']==0,
          full_security_oracle_fails=audit['exit']==1 and CASES[name][1] in audit['stdout'],
          full_suite_all_tests_collected=audit['collect_count']==3,
          defense_fails=noselect['exit']==1 and CASES[name][1] in noselect['stdout'],
          expected_required_result=(selective['exit']==(1 if variant=='ordinary' else 0)),
          expected_collected=(selective['collect_count']==(3 if variant=='ordinary' else 1)),
        )
        row={'case':name,'variant':variant,'baseline_exit':baseline['exit'],
             'required_check_exit':selective['exit'],
             'required_check_status':'PASS' if selective['exit']==0 else 'FAIL',
             'native_collected':selective['collect_count'],
             'post_pr_full_exit':audit['exit'],
             'full_collected':audit['collect_count'],
             'noselect_exit':noselect['exit'],
             'trusted_artifact_sha256':stored_hash,
             'pr_changed_paths':'|'.join(changed),
             'allowed_pr':policy,'tests_unchanged':tests_identical,
             'all_checks':all(guard.values()),
             'guard_json':json.dumps(guard,sort_keys=True),
             'required_seconds':selective['seconds'],
             'full_seconds':audit['seconds'],
             'required_log':selective['log'],
             'full_log':audit['log'],
             'noselect_log':noselect['log']}
        rows.append(row)
        print(label, row['required_check_status'], 'full',audit['exit'],'checks',row['all_checks'],flush=True)
    # Negative access-control check: purported PR modification to protected files must be blocked by policy.
    reject_tests=[]
    for disallowed in ['tests/test_security.py','.github/workflows/required-tests.yml','.testmondata']:
        reject_tests.append({'modified_path':disallowed,'accepted':set([disallowed])<=set(['build_meta.py'])})
    assert all(not r['accepted'] for r in reject_tests)
    with (OUT/'protected_ci_results.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
    (OUT/'protected_ci_results.json').write_text(json.dumps({'hosted_github_actions_executed':False,
      'event':'local reproduction of pull_request required-check semantics',
      'workflow_read_only':True,
      'trusted_source_ref':'main',
      'required_check_command':trusted_command,
      'software_versions':{'python':platform.python_version(),'pytest':importlib.metadata.version('pytest'),
            'coverage':importlib.metadata.version('coverage')},
      'original_plugin_git_blobs':hashes,
      'negative_policy_checks':reject_tests,
      'cases':rows},indent=2))
    if not all(x['all_checks'] for x in rows):return 1
    return 0

def git_hash(path):return subprocess.check_output(['git','hash-object',str(path)],text=True).strip()

if __name__=='__main__':raise SystemExit(execute())
