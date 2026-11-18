"""Read-only raw-evidence audit. Never launches subject, Jest, Docker or package code."""
from pathlib import Path
from collections import Counter
import json, hashlib, base64, gzip, datetime, re

ROOT=Path(__file__).resolve().parent.parent
STUDY=ROOT.parent
FREEZE=json.loads((ROOT/'EXECUTION_FREEZE.json').read_text(encoding='utf-8'))
BASE=json.loads((ROOT/'input/baseline-source-manifest.json').read_text(encoding='utf-8'))
CAND=json.loads((ROOT/'input/candidate-source-manifest.json').read_text(encoding='utf-8'))
SEED=json.loads((ROOT/'lab-image-context/seed-installed-manifest.json').read_text(encoding='utf-8'))
AUTH='shared/authentication/src/auth.definition.ts'
GUARD_FILE='tests/unit/authentication/cookie-config.test.ts'
GUARD='auth.definition.ts cookie configuration should not use sameSite: none (weakens CSRF protection)'
GUARD_BLOB='5c14cd837a04880807d3ef4f643da64cbdf6a552'
EXPECTED_FILES={x['path'] for x in BASE if x['path'].startswith('tests/unit/') and x['path'].endswith('.test.ts')}
def sha(b):return hashlib.sha256(b).hexdigest()
def jb(x):return json.dumps(x,ensure_ascii=False,separators=(',',':')).encode()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
SEED_ENTRIES_HASH=sha(jb(SEED['entries']))
def flattened(report):
    return [dict(file=s['name'].removeprefix('/work/project/'),full_name=a['fullName'],status=a['status'],
      failure_messages=a.get('failureMessages',[]),failure_details=a.get('failureDetails',[]))
      for s in report['testResults'] for a in s.get('assertionResults',[])]
def identities(rows):return Counter((x['file'],x['full_name']) for x in rows)
def audit(rep):
    folder=ROOT/'results'/('repetition-'+str(rep))
    evidence_bytes=(folder/'evidence.json').read_bytes();d=json.loads(evidence_bytes)
    checks=[]
    def ck(name,value,detail=None):checks.append(dict(name=name,passed=bool(value),detail=detail))
    before=load(folder/'before-start-inspect.json');after=load(folder/'after-execution-inspect.json')
    host=load(folder/'host-summary.json');boundary=load(folder/'host-boundary-checks.json')
    lines=[x for x in (folder/'execution.stdout').read_bytes().splitlines() if x.startswith(b'SP2027_EVIDENCE:')]
    ck('exactly one export envelope',len(lines)==1)
    envelope=json.loads(lines[0].split(b':',1)[1]);packed=base64.b64decode(envelope['payload_base64'],validate=True)
    ck('export gzip complete hash and length',sha(packed)==envelope['gzip_sha256'] and len(packed)==envelope['gzip_bytes'])
    plain=gzip.decompress(packed)
    ck('export uncompressed bytes exactly equal saved evidence',plain==evidence_bytes and sha(plain)==envelope['uncompressed_sha256'] and len(plain)==envelope['uncompressed_bytes'])
    ck('host summary and container exit statuses independently eligible',host['outer_container_eligible'] and host['process_exit']==0 and after['State']['ExitCode']==0 and not after['State']['OOMKilled'] and not after['State']['Error'])
    ck('actual image exactly matches final frozen image',before['Image']==after['Image']==FREEZE['final_image_id'])
    ck('actual19host boundary checks passed',boundary['all_pass'] and len(boundary['checks'])==19 and all(boundary['checks'].values()))
    h=before['HostConfig'];c=before['Config']
    ck('recorded actual isolation/resources agree',h['NetworkMode']=='none' and h['ReadonlyRootfs'] and c['User']=='10001:10001'
       and not h['Privileged'] and h['CapDrop']==['ALL'] and not h['CapAdd'] and not h['Binds'] and not before['Mounts']
       and not h['PortBindings'] and not h['PublishAllPorts'] and not h['Devices'] and not h['DeviceRequests']
       and h['Memory']==h['MemorySwap']==6*1024**3 and h['NanoCpus']==2000000000 and h['PidsLimit']==256
       and 'no-new-privileges:true' in h['SecurityOpt'])
    rt=d['runtime']
    ck('in-container runtime crosschecks agree',rt['uid']==rt['gid']==10001 and rt['capabilities']=='0000000000000000'
       and rt['no_new_privileges']=='1' and rt['seccomp']=='2' and rt['interfaces']==['lo']
       and 'ro' in rt['root_mount']['options'].split(',') and rt['work_mount']['filesystem']=='tmpfs'
       and 'noexec' not in rt['work_mount']['options'].split(',') and not rt['docker_socket_present'])
    ck('inner frozen protocol equals sealed predeclaration',d['protocol']==FREEZE['protocol']
       and d['protocol_file']['sha256']==FREEZE['context_files_sha256']['FROZEN_PROTOCOL.json'])
    ck('inner frozen input identity matches original hash',d['frozen_metadata']['INPUT_IDENTITY.json']['sha256']==FREEZE['context_files_sha256']['INPUT_IDENTITY.json'])
    ck('inner installed manifest is exact original',d['seed_installed_manifest']['sha256']==FREEZE['context_files_sha256']['seed-installed-manifest.json'])
    versions=d['versions']
    ck('runtime versions exact frozen versions',all(versions[k]==FREEZE['protocol']['runtime'][k] for k in ['node','npm','jest','ts_jest','typescript']) and versions['shared']=='4.1.0')
    ck('only three intended arms are present',set(d['arms'])=={'baseline','selective','independent_full'})
    if set(d['arms'])!={'baseline','selective','independent_full'}:
        available_rows={name:flattened(json.loads(arm['raw_jest_json'])) for name,arm in d['arms'].items() if arm.get('raw_jest_json')}
        return dict(repetition=rep,checks_passed=sum(x['passed'] for x in checks),checks_total=len(checks),
          independently_qualifying=False,checks=checks,evidence_sha256=sha(evidence_bytes),container_id=before['Id'],
          final_image_id=before['Image'],counts={name:dict(Counter(x['status'] for x in rows)) for name,rows in available_rows.items()},
          process_exits={name:arm['process']['exit_code'] for name,arm in d['arms'].items()},selected_original_cases=[],
          baseline_case_identity_sha256=sha(jb(sorted((file,name,count) for (file,name),count in identities(available_rows.get('baseline',[])).items()))),
          native_case_identity_sha256=sha(jb([])),retained_ineligible_status=d['status'])
    reports={};rows={};counts={};inventory=d['external_artifact_inventory']
    ck('complete external artifact inventory hash verifies',inventory['sha256']==sha(jb(inventory['entries'])))
    bypath={x['path']:x for x in inventory['entries']}
    for name,arm in d['arms'].items():
        reports[name]=json.loads(arm['raw_jest_json']);rows[name]=flattened(reports[name])
        counts[name]=Counter(x['status'] for x in rows[name]);p=arm['process'];raw=reports[name]
        ck(name+' raw JSON complete hash verifies',sha(arm['raw_jest_json'].encode())==arm['raw_jest_json_sha256'])
        ck(name+' raw per-case counts match report totals',len(rows[name])==raw['numTotalTests']
           and counts[name].get('passed',0)==raw['numPassedTests'] and counts[name].get('failed',0)==raw['numFailedTests'])
        ck(name+' no skips todos runtime suite errors interruption',raw['numPendingTests']==raw['numTodoTests']==raw['numRuntimeErrorTestSuites']==0
           and not raw['wasInterrupted'] and set(counts[name])<=set(['passed','failed'])
           and not any(s.get('testExecError') or not s.get('assertionResults') for s in raw['testResults']))
        ck(name+' process has no timeout signal spawn/output error',not p['timed_out'] and not p['signal']
           and not p['spawn_error'] and not p['output_limit_exceeded'] and not p['inherited_interruption'])
        for stream in ['stdout','stderr']:
            ck(name+' embedded '+stream+' matches raw-file hash',bypath[name+'/'+stream+'.txt']['sha256']==sha(arm[stream].encode()))
        ck(name+' raw JSON matches external-file hash',bypath[name+'/jest.json']['sha256']==arm['raw_jest_json_sha256'])
        for key in ['cache_before','cache_after','coverage_artifacts']:
            ck(name+' '+key+' inventory hash',arm[key]['sha256']==sha(jb(arm[key]['entries'])))
        args=arm['command']
        ck(name+' original CLI/config/selection/coverage worker flags',args[1:6]==['node_modules/jest/bin/jest.js','--config','jest.unit.config.ts','--coverage','--maxWorkers=2']
           and '--json' in args and '--runInBand' not in args
           and (('--changedSince=origin/main' in args and '--passWithNoTests' in args) if name=='selective'
                else not any(x.startswith('--changedSince') or x=='--passWithNoTests' for x in args)))
    baseline,selected,full=rows['baseline'],rows['selective'],rows['independent_full']
    ck('full original baseline8173cases actually pass and process0',counts['baseline']=={'passed':8173}
       and reports['baseline']['success'] is True and d['arms']['baseline']['process']['exit_code']==0)
    for name in ['baseline','independent_full']:
        files=[s['name'].removeprefix('/work/project/') for s in reports[name]['testResults']]
        ck(name+' all471original test files present exactly once',len(files)==len(set(files))==471 and set(files)==EXPECTED_FILES)
    ck('independent full case identities/multiplicities equal baseline',identities(full)==identities(baseline))
    ck('native has actual nonempty original passing case calls',len(selected)>0 and counts['selective']=={'passed':len(selected)}
       and not (identities(selected)-identities(baseline)) and reports['selective']['success'] is True
       and d['arms']['selective']['process']['exit_code']==0)
    target_base=[x for x in baseline if x['file']==GUARD_FILE and x['full_name']==GUARD]
    ck('designated original security guard passes baseline',len(target_base)==1 and target_base[0]['status']=='passed')
    ck('entire detecting security guard file absent from native actual execution',all(x['file']!=GUARD_FILE for x in selected)
       and all(s['name']!='/work/project/'+GUARD_FILE for s in reports['selective']['testResults']))
    failures=[x for x in full if x['status']=='failed']
    ck('independent sole failed original case is designated security guard',len(failures)==1
       and failures[0]['file']==GUARD_FILE and failures[0]['full_name']==GUARD and counts['independent_full']=={'passed':8172,'failed':1}
       and reports['independent_full']['success'] is False and d['arms']['independent_full']['process']['exit_code']==1)
    guard_bytes=(STUDY/'input/upstream'/GUARD_FILE).read_bytes()
    guard_lines=guard_bytes.decode().splitlines();line=next(i+1 for i,x in enumerate(guard_lines) if x.strip()=='expect(source).not.toMatch(hardcodedNone);')
    failed=failures[0];message='\n'.join(failed['failure_messages']);matcher=failed['failure_details'][0].get('matcherResult',{})
    ck('failure is exact original expectation line not setup or import',line==14 and 'not.toMatch' in message and 'sameSite' in message
       and re.search(r'cookie-config\.test\.ts:14:\d+',message) is not None and matcher.get('pass') is True)
    ck('guard blob/expectation provenance bound to original',d['guard']['blob']==GUARD_BLOB and d['guard']['expectation_line']==14)
    expected_labels=['before_baseline','after_baseline','before_selective','after_selective','before_independent','after_independent']
    ck('all six required state checkpoints present', [s['label'] for s in d['states']]==expected_labels)
    index_hashes=set()
    for i,state in enumerate(d['states']):
        expected=BASE if i<2 else CAND;candidate=i>=2;fs=state['files'];index_hashes.add(state['git']['index_sha256'])
        ck(state['label']+' all1869source bytes/blobs/modes match',len(fs)==1869 and not state['source_mismatches']
           and all(fs[x['path']]['sha256']==x['sha256'] and fs[x['path']]['git_blob']==x['git_blob']
               and fs[x['path']]['bytes']==x['size'] and fs[x['path']]['executable']==(x['mode']=='100755') for x in expected))
        gs=state['git'];expected_status=' M '+AUTH+'\0' if candidate else ''
        ck(state['label']+' exact Git identity and one-file worktree state',gs['head']==gs['origin_main']==FREEZE['protocol']['baseline']
           and gs['tree']=='cae8a86926869f4d8708ae17f19f5bf4ef4a6526' and gs['status_porcelain_z']==expected_status
           and gs['changed_from_base']==([AUTH] if candidate else []))
        dep=state['installed_identity']
        ck(state['label']+' complete original dependency bytes/links unchanged',dep['matches'] and dep['checked_entries']==dep['actual_dependency_entry_count']==49661
           and dep['actual_entries_sha256']==SEED_ENTRIES_HASH and not dep['mismatches'])
    ck('original Git index bytes constant throughout',len(index_hashes)==1)
    ck('baseline/native cache shared exactly and independent cache separate/fresh',
       d['arms']['baseline']['cache_directory']==d['arms']['selective']['cache_directory']!=d['arms']['independent_full']['cache_directory']
       and d['arms']['baseline']['cache_before']['entries']==[]
       and d['arms']['baseline']['cache_after']['sha256']==d['arms']['selective']['cache_before']['sha256']
       and d['arms']['independent_full']['cache_before']['entries']==[])
    ck('inner and host classification agree with independent raw observation',d['qualifying_joint_witness'] is True and host['qualifying_joint_witness'] is True
       and all(d['conditions'].values()) and d['status']=='QUALIFYING_ORIGINAL_SECURITY_SOURCE_GUARD_WITNESS')
    return dict(repetition=rep,checks_passed=sum(x['passed'] for x in checks),checks_total=len(checks),
       independently_qualifying=all(x['passed'] for x in checks),checks=checks,
       evidence_sha256=sha(evidence_bytes),container_id=before['Id'],final_image_id=before['Image'],
       baseline_case_identity_sha256=sha(jb(sorted((file,name,count) for (file,name),count in identities(baseline).items()))),
       native_case_identity_sha256=sha(jb(sorted((file,name,count) for (file,name),count in identities(selected).items()))),
       counts={k:dict(x) for k,x in counts.items()},process_exits={k:x['process']['exit_code'] for k,x in d['arms'].items()},
       selected_original_cases=[dict(file=x['file'],full_name=x['full_name']) for x in selected],
       original_guard_file=GUARD_FILE,original_guard_full_name=GUARD,original_guard_expectation_line=14,
       cache_before_counts={k:len(x['cache_before']['entries']) for k,x in d['arms'].items()})
def main():
    available=[i for i in [1,2,3] if (ROOT/'results'/('repetition-'+str(i))/'host-summary.json').exists()]
    results=[audit(i) for i in available]
    for result in results:
        (ROOT/'audit'/('repetition-'+str(result['repetition'])+'.independent.json')).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    static_checks=dict(
      frozen_hash_matches=sha((ROOT/'EXECUTION_FREEZE.json').read_bytes())=='eb3352984ea96a16ef28b2ded0a1f93612b09ee1473959a23fa6701f4cb4b8c7',
      frozen_host_code_matches=sha((ROOT/'lab.py').read_bytes())==FREEZE['host_orchestrator_sha256'],
      all_context_inputs_unchanged=all(sha((ROOT/'lab-image-context'/n).read_bytes())==h for n,h in FREEZE['context_files_sha256'].items()),
      v1_preserved=sha((STUDY/'EXECUTION_FREEZE.json').read_bytes())=='80173680cee88cf33b23d68cc8cec63f47f3ae0f82157089cf94631722b519bf'
       and sha((STUDY/'results/repetition-1/evidence.json').read_bytes())=='f63dfaea86563f1b1239959cc773234b1b255d1218d0359d2ace43323d68801e',
      v2_preserved=sha((STUDY/'platform-correction-jq/EXECUTION_FREEZE.json').read_bytes())=='44dccb97f84f3a57316ac6037ab21eb15c645658b4892c578fffdba29d28fb82'
       and sha((STUDY/'platform-correction-jq/results/repetition-1/evidence.json').read_bytes())=='913e23bc6e63ca27addedcefdd3d4e3170a13f60d7f1d8e0bae3e9513e184206',
      distinct_containers=len({x['container_id'] for x in results})==len(results),
      baseline_case_universes_consistent=len({x['baseline_case_identity_sha256'] for x in results})<=1,
      native_original_case_identities_consistent=len({x['native_case_identity_sha256'] for x in results})<=1)
    accepted=all(static_checks.values()) and all(x['independently_qualifying'] for x in results)
    complete=available==[1,2,3]
    status=('PASS_THREE_FRESH_QUALIFYING_REPETITIONS' if accepted and complete else
            'PARTIAL_QUALIFYING_REPETITIONS_PENDING_COMPLETION' if accepted else
            'COMPLETED_WITH_NONQUALIFYING_RESULT' if complete else 'PARTIAL_NONQUALIFYING_RESULTS')
    result=dict(audited_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status=status,
      completed_repetitions=len(results),predeclared_repetitions=3,static_checks=static_checks,
      repetitions=results,all_three_independently_qualify=accepted and complete,
      counts_are='Jest test-case results, not number of individual expect assertions.',
      scope='One fixed controlled reversion of a public production hunk with unchanged upstream original unit tests. Original static source-policy security guard; not runtime CSRF, CRC/fingerprint, production prevalence or hosted contributor validation.',
      technical_repetitions_not_independent_vulnerabilities=True,auditor_subject_execution=False)
    result['auditor_program_sha256']=sha(Path(__file__).read_bytes())
    name='INDEPENDENT_OUTCOME_AUDIT.json' if complete else 'INDEPENDENT_OUTCOME_AUDIT.partial.json'
    (ROOT/name).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    if complete:
        md='# Independent original-test outcome audit\n\n**'+status+'**.\n\n'
        md+='| Repetition | Baseline passed/failed | Native passed/failed | Independent passed/failed | Process exits |\n| --- | --- | --- | --- | --- |\n'
        for row in results:
            cells=[]
            for arm in ['baseline','selective','independent_full']:
                counts=row['counts'].get(arm)
                cells.append((str(counts.get('passed',0))+'/'+str(counts.get('failed',0))) if counts is not None else 'not run')
            exits='/'.join(str(row['process_exits'].get(arm,'not run')) for arm in ['baseline','selective','independent_full'])
            md+='| '+str(row['repetition'])+' | '+' | '.join(cells)+' | '+exits+' |\n'
        md+='\n'
        if accepted:
            md+='The native cases are the original tests in tests/unit/auth/account-setup.test.ts. The omitted detecting case is '+GUARD+' at '+GUARD_FILE+':14. Its failure is bound to the original not.toMatch expectation, not setup/runtime failure. All 471 original unit files and their full case identities remain present in each independent oracle. Source/config/lock/test/Git identities and all 49,661 installed dependency entries remain unchanged; the same frozen candidate bytes occur across selective and independent states.\n\n'
        else:
            md+='Not all predeclared repetitions independently qualify. No three-repetition witness is claimed. See the retained per-repetition checks and raw outcomes.\n\n'
        md+='Fresh separate containers, exact frozen image/context, empty initial caches, native/baseline cache continuity and a separate empty independent cache are verified. Raw JSON/log exports and supplementary cache/coverage inventories pass hash checks. V1 and v2 ineligible baselines are retained separately and are not qualifying repetitions.\n\n'
        md+=('This establishes the bounded missing joint observation for an upstream static security-source guard in this configured unit oracle. ' if accepted else '')
        md+='It does not establish runtime CSRF exploitability, CRC collision behavior, production prevalence or independent protected-branch contributor validity. The repetitions repeat one fixed case. No subject tests were rerun by this auditor.\n'
        (ROOT/'INDEPENDENT_OUTCOME_AUDIT.md').write_text(md,encoding='utf-8')
    print(json.dumps(dict(status=status,completed=len(results),static_checks=static_checks,
      repetitions=[dict(repetition=x['repetition'],checks=x['checks_passed'],total=x['checks_total'],qualifies=x['independently_qualifying'],
        failed=[z['name'] for z in x['checks'] if not z['passed']],counts=x['counts']) for x in results]),indent=2))
if __name__=='__main__':main()

