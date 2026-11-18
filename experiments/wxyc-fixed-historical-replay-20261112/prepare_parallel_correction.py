"""Prospectively restore native worker mode; keep both earlier baseline preflights."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parent
PREV=ROOT/'platform-correction-jq'
OUT=ROOT/'native-parallel-correction'
assert not OUT.exists()
e=json.loads((PREV/'results/repetition-1/evidence.json').read_bytes())
assert set(e['arms'])=={'baseline'} and not e['qualifying_joint_witness']
a=e['arms']['baseline']
assert a['process']['exit_code']==1 and a['summary']['success'] is True
assert a['summary']['counts']['passed']==8173 and a['summary']['counts']['failed']==0
OUT.mkdir()
unchanged={}
for name in ['INPUT_IDENTITY.json','input/baseline-source-manifest.json','input/candidate-source-manifest.json','input/original-unit-test-manifest.json','input/fixed-candidate/shared/authentication/src/auth.definition.ts']:
    target=OUT/name
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(PREV/name,target)
    unchanged[name]=hashlib.sha256(target.read_bytes()).hexdigest()
runner=(PREV/'run_replay.mjs').read_text(encoding='utf-8')
assert runner.count("'--runInBand'")==1
runner=runner.replace("'--runInBand'","'--maxWorkers=2'")
(OUT/'run_replay.mjs').write_text(runner,encoding='utf-8',newline='\n')
host=(PREV/'lab.py').read_text(encoding='utf-8')
renames={'sp2027-wxyc-fixed-history-jq:20261112':'sp2027-wxyc-fixed-history-parallel:20261112','sp2027-wxyc-final-assembly-jq-20261112':'sp2027-wxyc-final-assembly-parallel-20261112','sp2027-wxyc-fixed-replay-jq-20261112-r':'sp2027-wxyc-fixed-replay-parallel-20261112-r','sp2027.study=wxyc-fixed-history-jq-20261112':'sp2027.study=wxyc-fixed-history-parallel-20261112'}
for before,after in renames.items():
    assert host.count(before)==1
    host=host.replace(before,after)
assert host.count('study_test_executions_before_freeze=0')==1
host=host.replace('study_test_executions_before_freeze=0','this_protocol_version_test_executions_before_freeze=0')
(OUT/'lab.py').write_text(host,encoding='utf-8',newline='\n')
p=json.loads((PREV/'PROTOCOL_PREDECLARATION.json').read_bytes())
assert p['common_arguments'].count('--runInBand')==1
p['common_arguments']=['--maxWorkers=2' if x=='--runInBand' else x for x in p['common_arguments']]
p['status']='SEPARATELY_PREDECLARED_NATIVE_PARALLEL_MODE_CORRECTION_BEFORE_ANY_CANDIDATE_OUTCOME'
p['previous_all_assertions_pass_but_process_failure']={'freeze_sha256':hashlib.sha256((PREV/'EXECUTION_FREEZE.json').read_bytes()).hexdigest(),'evidence_sha256':hashlib.sha256((PREV/'results/repetition-1/evidence.json').read_bytes()).hexdigest(),'cases_passed':8173,'cases_failed':0,'report_success':True,'actual_exit_code':1,'candidate_applied':False,'candidate_arms_executed':False,'retained_at':'../platform-correction-jq/results/repetition-1'}
p['execution_mode_correction']={'old_researcher_added_flag':'--runInBand','new_flag':'--maxWorkers=2','reason':'Restore original upstream CI worker execution mode, bounded to two workers. Exact Node/Jest sources explain that successful reports do not clear an imported job exitCode in serial execution.','native_auto_serial_behavior':'Unmodified; Jest may still choose serial execution for a small selection.','unchanged':'Project/test/config/lock/candidate bytes, entire oracle scope, coverage, selection flags, dependency versions, eligibility rules and isolation controls.','prior_baseline_preflights_retained':2,'candidate_outcomes_observed':0}
(OUT/'PROTOCOL_PREDECLARATION.json').write_text(json.dumps(p,indent=2)+'\n',encoding='utf-8')
record={'status':'PARALLEL_CORRECTION_INPUTS_PREPARED_NO_TEST_RUN','unchanged_subject_inputs_sha256':unchanged,'runner_delta':"Only '--runInBand' to '--maxWorkers=2'",'host_delta':'Resource namespace strings and per-version freeze field name only','namespace_changes':renames,'prior_versions_retained':True}
(OUT/'CORRECTION_IDENTITY.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':record['status'],'unchanged_subject_inputs':len(unchanged)}))
