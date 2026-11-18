"""Three fresh baseline Git/DB runs per genuine codebase, source-only PR."""
from run_protected_ci import CASES,OUT,FIX,make_case,cli,git,h
import csv,hashlib,json,os,shutil,sys

rows=[]
for seed in (0,1,42):
 for name,(path,security) in CASES.items():
  src,p,_=make_case(name,f'repeat_seed_{seed}')
  env={'PYTHONHASHSEED':str(seed)}
  base=cli(p,[sys.executable,'-m','pytest','-p','testmon.pytest_testmon','--testmon','-vv'],f'single_repeats/seed_{seed}/{name}/baseline',env=env)
  assert base['exit']==0
  trusted=OUT/'trusted_main_artifacts'/name/f'seed_{seed}'/'baseline.db'
  trusted.parent.mkdir(parents=True,exist_ok=True)
  shutil.copyfile(p/'.testmondata',trusted)
  trusted_sha=h(trusted)
  git(p,'checkout','-qb','pr/single-source')
  shutil.copyfile(src/'snapshots/collision.py',p/path)
  git(p,'add',path);git(p,'commit','-qm','only application source is changed')
  changed=git(p,'diff','--name-only','main...HEAD').splitlines()
  assert changed==[path]
  shutil.copyfile(trusted,p/'.testmondata')
  assert h(p/'.testmondata')==trusted_sha
  selected=cli(p,[sys.executable,'-m','pytest','-p','testmon.pytest_testmon','--testmon','-vv'],f'single_repeats/seed_{seed}/{name}/native',env=env)
  full=cli(p,[sys.executable,'-m','pytest','-vv'],f'single_repeats/seed_{seed}/{name}/full',env=env)
  good=selected['exit']==0 and selected['collect_count']==0 and full['exit']==1 and full['collect_count']==3 and security in full['stdout']
  rows.append({'seed':seed,'case':name,'changed_files':len(changed),
       'native_exit':selected['exit'],'native_collected':selected['collect_count'],
       'full_exit':full['exit'],'full_collected':full['collect_count'],
       'full_security_failure':security in full['stdout'],
       'trusted_baseline_sha256':trusted_sha,'experiment_pass':good,
       'native_duration_s':selected['seconds'],'full_duration_s':full['seconds']})
  print(seed,name,'native',selected['exit'],'full',full['exit'],'assertions',good,flush=True)
with (OUT/'single_file_repeats.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
(OUT/'single_file_repeats.json').write_text(json.dumps(rows,indent=2))
assert all(x['experiment_pass'] for x in rows)
