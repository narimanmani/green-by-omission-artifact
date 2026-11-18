#!/usr/bin/env python3
"""Fixed synthetic integrity-fault experiment; no arbitrary target interface.

Runs the released Ekstazi 5.3.0 Java agent without modification. The fixed
faults act only on this script's generated synthetic fixture, never a user
repository. No fingerprint synthesis, checksum matching, or exploit mutation.
"""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import shutil
import subprocess
import time
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
CLASSES = ['lab.ArithmeticTest', 'lab.LabelTest', 'lab.UnrelatedTest']
FAULTS = ['none', 'missing_target', 'empty_target', 'half_truncated_target',
          'invalid_header', 'missing_cache', 'unexpected_file', 'wrong_baseline_id']
STRATEGIES = ['standard_rts', 'verified_rts', 'full_suite']

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def inventory(directory):
    return {str(p.relative_to(directory)): digest(p)
            for p in sorted(directory.rglob('*')) if p.is_file()} if directory.exists() else {}

def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + '\n')

def reset_directory(path):
    # Destructive operations are confined to this known generated directory.
    if path.parent != HERE or path.name != 'native_work':
        raise ValueError('Refusing to reset an arbitrary location')
    if path.exists(): shutil.rmtree(path)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--toolchain', type=Path, default=HERE.parent / 'toolchain')
    ap.add_argument('--repetitions', type=int, default=3)
    args = ap.parse_args()
    if args.repetitions < 1: raise ValueError('Repetitions must be positive')
    tc = args.toolchain.resolve()
    java, javac = tc/'jdk8u432-b06/bin/java', tc/'jdk8u432-b06/bin/javac'
    jars = [tc/'junit-4.13.2.jar', tc/'hamcrest-core-1.3.jar']
    agent = tc/'org.ekstazi.core-5.3.0.jar'
    expected_agent = 'baf7affe8fc42e12b382ec933f3572fce417e5e0d9a7ebab2902bc5c614cb749'
    if digest(agent) != expected_agent: raise RuntimeError('Published agent hash mismatch')
    work = HERE/'native_work'
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out = HERE/'results'/stamp
    out.mkdir(parents=True)
    plan = {'version':1,'frozen_at_utc':datetime.now(timezone.utc).isoformat(),
            'fixture':'synthetic arithmetic + independent passing control + untouched test',
            'faults':FAULTS, 'strategies':STRATEGIES, 'repetitions':args.repetitions,
            'shuffle_seed':20261110, 'truncation':'first floor(length/2) bytes; no adaptive adjustment',
            'oracle':'same compiled source and unchanged tests, no agent, reset independently',
            'unit':'fixed scenario; repetitions are technical repeatability checks',
            'scope':'local native engine, controlled integrity-fault simulation; no adversarial feasibility claim',
            'timing':'JVM process wall time + manifest verification, excludes reset/compile/setup'}
    write_json(out/'frozen_plan.json',plan)
    write_json(out/'environment.json',{'timestamp_utc':datetime.now(timezone.utc).isoformat(),
        'python':platform.python_version(),'platform':platform.platform(),
        'java':subprocess.run([str(java),'-version'],capture_output=True,text=True).stderr,
        'artifacts':{str(p):digest(p) for p in jars+[agent]},
        'runner_sha256':digest(HERE/'TraceRunner.java'),
        'script_sha256':digest(Path(__file__)),
        'isolation':'dedicated local directories; downloaded dependencies prepared separately; synthetic execution performs no network I/O; no OS network namespace claim'})

    def compile_sources(log):
        cp = os.pathsep.join(map(str,jars))
        cmd = [str(javac),'-g','-encoding','UTF-8','-cp',cp,'-d',str(work/'classes')]
        cmd += [str(p) for p in sorted((work/'src').rglob('*.java'))]
        cmd.append(str(HERE/'TraceRunner.java'))
        p = subprocess.run(cmd,capture_output=True,text=True,timeout=60)
        log.write_text(p.stdout+p.stderr)
        if p.returncode: raise RuntimeError('Compilation failed; see '+str(log))

    def run(run_id, use_agent, info):
        dest=out/'runs'/run_id; dest.mkdir(parents=True,exist_ok=True)
        cp=os.pathsep.join([str(work/'classes')]+list(map(str,jars)))
        cmd=[str(java)]
        if use_agent: cmd.append('-javaagent:'+str(agent)+'=mode=junit')
        cmd += ['-cp',cp,'TraceRunner']+CLASSES
        before=inventory(work/'.ekstazi')
        t=time.perf_counter()
        try:
            p=subprocess.run(cmd,cwd=work,capture_output=True,text=True,timeout=60)
            output=p.stdout+p.stderr; rc=p.returncode; timed_out=False
        except subprocess.TimeoutExpired as e:
            output=str(e);rc=None;timed_out=True
        elapsed=time.perf_counter()-t
        (dest/'stdout.log').write_text(output)
        started=[];failed=[];summary=None
        for line in output.splitlines():
            s=line.split('\t')
            if s[0]=='RESEARCH_START': started.append(s[1]+'.'+s[2])
            if s[0]=='RESEARCH_FAILURE': failed.append(s[1]+'.'+s[2])
            if s[0]=='RESEARCH_RESULT': summary={'run':int(s[1]),'failures':int(s[2]),'ignored':int(s[3]),'successful':s[4]=='true'}
        row={'run_id':run_id,**info,'agent_enabled':use_agent,'returncode':rc,'timed_out':timed_out,
             'execution_status':'completed' if summary is not None else 'infrastructure_error',
             'tests_executed':started,'tests_failed':failed,
             'test_classes_executed':sorted({x.rsplit('.',1)[0] for x in started}),
             'methods_executed':len(started),'failures':len(failed),'junit_summary':summary,
             'process_seconds':elapsed,'total_seconds':elapsed+info.get('verification_seconds',0),
             'metadata_before':before,'metadata_after':inventory(work/'.ekstazi'),
             'source_hashes':inventory(work/'src/main'), 'test_hashes':inventory(work/'src/test'),
             'command':cmd,'cwd':str(work)}
        write_json(dest/'result.json',row)
        if summary and (summary['run']!=len(started) or summary['failures']!=len(failed)):
            raise AssertionError('Observation count mismatch')
        return row

    reset_directory(work)
    shutil.copytree(HERE/'fixture',work)
    (work/'classes').mkdir()
    compile_sources(out/'baseline_compile.log')
    cold=run('control_cold',True,{'phase':'control','case_id':'cold','strategy':'standard_rts'})
    if cold['returncode']!=0 or cold['methods_executed']!=4: raise RuntimeError('Cold control failed')
    snapshot=out/'baseline_snapshot';shutil.copytree(work,snapshot)
    warm=run('control_warm',True,{'phase':'control','case_id':'warm','strategy':'standard_rts'})
    if warm['returncode']!=0 or warm['methods_executed']!=0: raise RuntimeError('Warm selection control failed')
    baseline_full=run('control_baseline_full',False,{'phase':'control','case_id':'baseline_full','strategy':'full_suite'})
    if baseline_full['returncode']!=0 or baseline_full['methods_executed']!=4: raise RuntimeError('Full baseline failed')
    target=snapshot/'.ekstazi/lab.ArithmeticTest.clz'
    if not target.exists(): raise RuntimeError('Target native dependency metadata missing')
    trusted={'baseline_id':'synthetic-v1','engine_sha256':digest(agent),
             'test_hashes':inventory(snapshot/'src/test'),
             'metadata_hashes':inventory(snapshot/'.ekstazi')}
    write_json(out/'trusted_manifest.json',trusted)

    def restore(change=True):
        reset_directory(work); shutil.copytree(snapshot,work)
        if change:
            p=work/'src/main/java/lab/Arithmetic.java'
            p.write_text(p.read_text().replace('return left + right;','return left + right + 1;'))
            p=work/'src/main/java/lab/Label.java'
            p.write_text(p.read_text().replace('return "ready";','return new String("ready");'))
            compile_sources(out/'changed_compile.log')

    restore()
    changed_snapshot=out/'changed_snapshot'; shutil.copytree(work,changed_snapshot)
    oracle=run('control_changed_full',False,{'phase':'control','case_id':'changed_full','strategy':'full_suite'})
    if oracle['methods_executed']!=4 or len(oracle['tests_failed'])!=2:
        raise RuntimeError('Changed full-suite oracle invalid')
    controls=[cold,warm,baseline_full,oracle]
    oracle_failing=set(oracle['tests_failed'])
    write_json(out/'controls.json',controls)
    print(json.dumps({'controls':[(r['case_id'],r['methods_executed'],r['failures']) for r in controls]}),flush=True)

    def inject(fault):
        cache=work/'.ekstazi';p=cache/'lab.ArithmeticTest.clz'
        before=p.read_bytes();baseline_id='synthetic-v1'
        if fault=='missing_target': p.unlink()
        elif fault=='empty_target': p.write_bytes(b'')
        elif fault=='half_truncated_target': p.write_bytes(before[:len(before)//2])
        elif fault=='invalid_header': p.write_bytes(b'INVALID-HEADER\n'+before.split(b'\n',1)[-1])
        elif fault=='missing_cache': shutil.rmtree(cache)
        elif fault=='unexpected_file': (cache/'synthetic-unexpected.txt').write_text('controlled integrity fixture\n')
        elif fault=='wrong_baseline_id': baseline_id='synthetic-v0'
        elif fault!='none': raise ValueError(fault)
        return baseline_id

    rows=[];order=[]
    for rep in range(1,args.repetitions+1):
        cells=[(f,s) for f in FAULTS for s in STRATEGIES]
        random.Random(20261110+rep).shuffle(cells)
        order.extend((rep,f,s) for f,s in cells)
    write_json(out/'execution_order.json',order)
    for rep,fault,strategy in order:
        reset_directory(work);shutil.copytree(changed_snapshot,work)
        provenance=inject(fault)
        run_id=f'{rep:02d}__{fault}__{strategy}'
        dest=out/'runs'/run_id;dest.mkdir(parents=True)
        if (work/'.ekstazi').exists():shutil.copytree(work/'.ekstazi',dest/'injected_metadata')
        t=time.perf_counter();reasons=[]
        if provenance!=trusted['baseline_id']:reasons.append('baseline_id_mismatch')
        if inventory(work/'.ekstazi')!=trusted['metadata_hashes']:reasons.append('metadata_inventory_or_hash_mismatch')
        if inventory(work/'src/test')!=trusted['test_hashes']:reasons.append('oracle_test_hash_mismatch')
        if digest(agent)!=trusted['engine_sha256']:reasons.append('engine_hash_mismatch')
        vt=time.perf_counter()-t
        verified=strategy=='verified_rts'
        fallback=verified and bool(reasons)
        use_agent=strategy!='full_suite' and not fallback
        row=run(run_id,use_agent,{'phase':'fault_corpus','case_id':fault,'strategy':strategy,'repetition':rep,
            'integrity_status':('rejected' if reasons else 'verified') if verified else 'not_enforced',
            'diagnostic_integrity_reasons':reasons,'fallback':fallback,
            'verification_seconds':vt if verified else 0,
            'finding_type':'native_observation_under_simulated_integrity_fault' if fault!='none' else 'native_normal_change_observation'})
        omitted=sorted(oracle_failing-set(row['tests_executed']))
        row.update({'oracle_failing_tests':sorted(oracle_failing),'relevant_tests_omitted':omitted,
                    'false_green':row['execution_status']=='completed' and row['returncode']==0 and bool(oracle_failing),
                    'regression_detected':row['execution_status']=='completed' and bool(set(row['tests_failed']) & oracle_failing)})
        if row['test_hashes']!=trusted['test_hashes']: raise AssertionError('Oracle changed')
        write_json(dest/'result.json',row);rows.append(row)
        print(json.dumps({k:row[k] for k in ['run_id','methods_executed','failures','false_green','fallback','relevant_tests_omitted']}),flush=True)
    write_json(out/'results.json',rows)
    columns=['run_id','case_id','strategy','repetition','finding_type','execution_status','returncode',
             'methods_executed','failures','integrity_status','fallback','regression_detected','false_green',
             'relevant_tests_omitted','test_classes_executed','process_seconds','verification_seconds','total_seconds']
    with (out/'results.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=columns);writer.writeheader()
        for row in rows:writer.writerow({k:json.dumps(row[k]) if isinstance(row[k],list) else row[k] for k in columns})
    write_json(HERE/'latest_result.json',{'path':str(out),'run_count':len(rows),'control_count':len(controls)})
    print('RESULT_DIRECTORY='+str(out),flush=True)

if __name__=='__main__':main()
