from pathlib import Path
import csv,json,re,hashlib
from run_protected_ci import ROOT,OUT,CASES,git,h
rows=[]
for case,(path,security) in CASES.items():
 for variant in ['ordinary','collision']:
  base=OUT/'logs'/case/variant
  data={}
  for label,f in {'baseline':'base.log','required':'required_selective.log','full':'independent_full_suite.log','noselect':'defense_noselect.log'}.items():
   s=(base/f).read_text()
   ex=int(re.search(r'EXIT: (-?\d+)',s).group(1))
   m=re.search(r'collected (\d+) item',s)
   secs=float(re.search(r'SECONDS: ([\d.]+)',s).group(1))
   data[label]={'exit':ex,'collected':int(m.group(1)) if m else -1,'seconds':secs,
                'security_test_in_log':security in s}
  trust=OUT/'trusted_main_artifacts'/case/variant/'baseline.testmondata'
  p=OUT/'workspaces'/case/variant
  changed=git(p,'diff','--name-only','main...HEAD').splitlines()
  checks={'baseline_pass':data['baseline']['exit']==0,'expected_required':data['required']['exit']==(0 if variant=='collision' else 1),
          'full_detect':data['full']['exit']==1 and data['full']['security_test_in_log'],
          'noselect_detect':data['noselect']['exit']==1 and data['noselect']['security_test_in_log'],
          'modified_paths_correct':set(changed)=={path,'build_meta.py'},
          'trusted_db_exists':trust.exists(), 'native_scope':data['required']['collected']==(1 if variant=='collision' else 3)}
  row={'case':case,'variant':variant,'pr_changed_paths':'|'.join(changed),
       'required_exit':data['required']['exit'],'required_status':'PASS' if data['required']['exit']==0 else 'FAIL',
       'native_tests_collected':data['required']['collected'],'full_exit':data['full']['exit'],
       'full_tests_collected':data['full']['collected'],'noselect_exit':data['noselect']['exit'],
       'trusted_base_sha256':h(trust),'all_checks':all(checks.values()),'checks':json.dumps(checks),
       'native_duration_s':round(data['required']['seconds'],3),
       'full_duration_s':round(data['full']['seconds'],3)}
  rows.append(row)
with (OUT/'protected_ci_results.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
(OUT/'protected_ci_results.json').write_text(json.dumps(rows,indent=2))
print('COLLECTED',len(rows),'ALL_OK',all(x['all_checks'] for x in rows));print(*[(x['case'],x['variant'],x['required_exit'],x['full_exit']) for x in rows],sep='\n')
assert all(x['all_checks'] for x in rows)
