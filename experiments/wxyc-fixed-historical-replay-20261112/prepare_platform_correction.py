"""Prepare a separate prospectively frozen OS correction; preserve every v1 artifact."""
from pathlib import Path
import hashlib, json, shutil
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'platform-correction-jq'
assert not OUT.exists(), 'Refusing to overwrite correction evidence.'
first=json.loads((ROOT/'results/repetition-1/evidence.json').read_bytes())
assert set(first['arms'])=={'baseline'} and not first['qualifying_joint_witness']
assert first['arms']['baseline']['summary']['counts']['failed']==4
assert first['arms']['baseline']['summary']['designated_guard_results'][0]['status']=='passed'
OUT.mkdir()
files=['run_replay.mjs','INPUT_IDENTITY.json','input/baseline-source-manifest.json','input/candidate-source-manifest.json','input/original-unit-test-manifest.json','input/fixed-candidate/shared/authentication/src/auth.definition.ts']
hashes={}
for name in files:
    target=OUT/name
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(ROOT/name,target)
    hashes[name]=hashlib.sha256(target.read_bytes()).hexdigest()
replacements={'sp2027-wxyc-fixed-history:20261112':'sp2027-wxyc-fixed-history-jq:20261112','sp2027-wxyc-replay-seed:20261112':'sp2027-wxyc-replay-seed-jq:20261112','sp2027-wxyc-final-assembly-20261112':'sp2027-wxyc-final-assembly-jq-20261112','sp2027-wxyc-fixed-replay-20261112-r':'sp2027-wxyc-fixed-replay-jq-20261112-r','sp2027.study=wxyc-fixed-history-20261112':'sp2027.study=wxyc-fixed-history-jq-20261112'}
host=(ROOT/'lab.py').read_text(encoding='utf-8')
for before,after in replacements.items():
    assert host.count(before)==1
    host=host.replace(before,after)
(OUT/'lab.py').write_text(host,encoding='utf-8',newline='\n')
protocol=json.loads((ROOT/'PROTOCOL_PREDECLARATION.json').read_bytes())
protocol['status']='SEPARATELY_PREDECLARED_OS_PREREQUISITE_CORRECTION_BEFORE_ANY_CANDIDATE_OUTCOME'
protocol['previous_ineligible_baseline']={'freeze_sha256':hashlib.sha256((ROOT/'EXECUTION_FREEZE.json').read_bytes()).hexdigest(),'evidence_sha256':hashlib.sha256((ROOT/'results/repetition-1/evidence.json').read_bytes()).hexdigest(),'counts':first['arms']['baseline']['summary']['counts'],'security_guard':'passed','candidate_applied':False,'candidate_arms_executed':False,'retained_at':'../results/repetition-1'}
protocol['os_prerequisite_correction']={'tool':'jq','basis':'Unchanged original script requires jq; explicit preserved-image probe confirms absent in v1.','packages':{'jq':'1.6-2.1+deb12u3','libjq1':'1.6-2.1+deb12u3','libonig5':'6.9.8-1'},'receipts':'../backend-provisioning/jq-prerequisite-correction','changes':'Only the missing OS utility and necessary libraries; zero existing OS version changes. Original project, Node dependencies, test scope, candidate, flags and isolation unchanged.'}
(OUT/'PROTOCOL_PREDECLARATION.json').write_text(json.dumps(protocol,indent=2)+'\n',encoding='utf-8')
record={'status':'CORRECTION_INPUTS_PREPARED_NO_STUDY_RUN','unchanged_files_sha256':hashes,'host_namespace_replacements':replacements,'v1_artifacts_untouched':True,'candidate_outcomes_observed':0}
(OUT/'CORRECTION_IDENTITY.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':record['status'],'unchanged_files':len(files)}))
