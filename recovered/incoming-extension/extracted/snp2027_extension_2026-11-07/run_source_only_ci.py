#!/usr/bin/env python3
"""Single-file source-only adversarial PR, no unrelated metadata changes."""
from run_protected_ci import ROOT,OUT,FIX,CASES,make_case,cli,git,h
import csv,hashlib,os,json,shutil,sys

def run():
 rows=[]
 for name,(target,security) in CASES.items():
  src,p,_=make_case(name,'single_file_collision')
  base=cli(p,[sys.executable,'-m','pytest','-p','testmon.pytest_testmon','--testmon','-vv'],f'single_source_only/{name}/baseline')
  assert base['exit']==0
  trusted=OUT/'trusted_main_artifacts'/name/'single_file'/'baseline.testmondata'
  trusted.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p/'.testmondata',trusted)
  trust_hash=h(trusted)
  git(p,'checkout','-qb','pr/source-only');shutil.copyfile(src/'snapshots/collision.py',p/target)
  git(p,'add',target);git(p,'commit','-qm','source-only security regression')
  changed=git(p,'diff','--name-only','main...HEAD').splitlines()
  assert changed==[target],(name,changed)
  shutil.copyfile(trusted,p/'.testmondata');assert h(trusted)==h(p/'.testmondata')
  selected=cli(p,[sys.executable,'-m','pytest','-p','testmon.pytest_testmon','--testmon','-vv'],f'single_source_only/{name}/selective')
  full=cli(p,[sys.executable,'-m','pytest','-vv'],f'single_source_only/{name}/full')
  rows.append({'case':name,'modified_files':len(changed),'changed_only_path':changed[0],
               'baseline_exit':base['exit'],'native_exit':selected['exit'],
               'native_collected':selected['collect_count'],'native_stdout_tail':selected['stdout'][-500:],
               'full_exit':full['exit'],'full_collected':full['collect_count'],
               'security_test_failed':security in full['stdout'],
               'trusted_db_hash':trust_hash,
               'bypass_confirmed':selected['exit']==0 and full['exit']==1 and security in full['stdout']})
  print(name, 'native',selected['exit'],'collected',selected['collect_count'],'full',full['exit'],'bypass',rows[-1]['bypass_confirmed'],flush=True)
 with (OUT/'source_only_results.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
 (OUT/'source_only_results.json').write_text(json.dumps(rows,indent=2))
 assert all(x['bypass_confirmed'] for x in rows)
 return 0

if __name__=='__main__':raise SystemExit(run())
