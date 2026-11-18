"""Actual Git-commit attempts to modify files outside the allowed PR source surface.
This measures the local protected-policy gate, NOT GitHub's branch protection.
"""
import csv,json,shutil
from pathlib import Path
from run_protected_ci import OUT,CASES,make_case,git

def execute():
 rows=[]
 base_name='itsdangerous_expiry';target=CASES[base_name][0]
 for label,path in [('test_tamper','tests/test_security.py'),
                    ('workflow_tamper','.github/workflows/required-tests.yml'),
                    ('baseline_artifact_tamper','.testmondata')]:
  src,p,_=make_case(base_name,'policy_'+label)
  # Explicitly make the trusted CI definition available as part of baseline.
  workfile=p/'.github/workflows/required-tests.yml'
  workfile.parent.mkdir(parents=True,exist_ok=True)
  workfile.write_text('name: protected-ci\non: pull_request\n')
  git(p,'add','.github/workflows/required-tests.yml')
  git(p,'commit','-qm','trusted workflow definition')
  git(p,'checkout','-qb','pr/policy-test')
  dest=p/path;dest.parent.mkdir(parents=True,exist_ok=True)
  with dest.open('a') as f:f.write('\n# attempted untrusted PR modification\n')
  git(p,'add','-f',path)
  git(p,'commit','-qm','malicious path modification attempt')
  changed=git(p,'diff','--name-only','main...HEAD').splitlines()
  accepted=bool(changed) and set(changed) <= set([target,'build_meta.py'])
  rows.append({'attempt':label,'modified_path':path,'actual_committed_change':path in changed,
               'policy_accepted':accepted,'policy_rejected':not accepted,'git_diff':changed})
  print(label,'actual git change',changed,'policy accepted?',accepted,flush=True)
 (OUT/'policy_tamper_attempts.json').write_text(json.dumps(rows,indent=2))
 with (OUT/'policy_tamper_attempts.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
 assert all(x['actual_committed_change'] and x['policy_rejected'] for x in rows)

if __name__=='__main__':execute()
