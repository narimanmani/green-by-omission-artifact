#!/usr/bin/env python3
"""Supplemental Maven integration controls, separate from the native fault corpus."""
import argparse, hashlib, json, os, shutil, subprocess, time
from pathlib import Path
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent

def hashes(path):
    return {str(p.relative_to(path)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(path.rglob('*')) if p.is_file()}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--toolchain',type=Path,default=HERE.parent/'toolchain');args=ap.parse_args()
    tc=args.toolchain.resolve(); work=HERE/'maven_validation_work';out=HERE/'maven_validation'
    out.mkdir(exist_ok=True)
    if work.exists():shutil.rmtree(work)
    shutil.copytree(HERE/'fixture',work)
    env=os.environ.copy();env['JAVA_HOME']=str(tc/'jdk8u432-b06');env['PATH']=env['JAVA_HOME']+'/bin:'+env['PATH']
    # Offline: dependency preparation happens separately, before any measured run.
    base=[str(tc/'apache-maven-3.8.8/bin/mvn'),'-o','-B','-ntp','-Dmaven.repo.local='+str(tc/'m2')]
    def run(name,select):
        reports=work/'target/surefire-reports'
        if reports.exists():shutil.rmtree(reports)
        cmd=base+(['-Pekstazi'] if select else [])+['test']
        start=time.perf_counter();p=subprocess.run(cmd,cwd=work,env=env,capture_output=True,text=True,timeout=90)
        (out/(name+'.log')).write_text(p.stdout+p.stderr)
        tests=[];failures=[]
        if reports.exists():
            dest=out/(name+'_xml');dest.mkdir(exist_ok=True)
            for f in sorted(reports.glob('TEST-*.xml')):
                shutil.copy2(f,dest/f.name)
                for test in ET.parse(f).getroot().iter('testcase'):
                    key=test.get('classname')+'.'+test.get('name');tests.append(key)
                    if test.find('failure') is not None or test.find('error') is not None: failures.append(key)
        row={'case':name,'strategy':'standard_rts' if select else 'full_suite','exit_code':p.returncode,
             'tests_executed':tests,'tests_failed':failures,'seconds':time.perf_counter()-start,
             'source_hashes':hashes(work/'src/main'),'test_hashes':hashes(work/'src/test'),
             'metadata_hashes':hashes(work/'.ekstazi'),'command':cmd}
        print(json.dumps({'case':name,'exit_code':p.returncode,'tests':len(tests),'failed':len(failures)}),flush=True)
        return row
    rows=[run('cold',True)]
    if rows[0]['exit_code']!=0 or len(rows[0]['tests_executed'])!=4:raise RuntimeError('Cold Maven control failed')
    snapshot=out/'baseline_snapshot'
    if snapshot.exists():shutil.rmtree(snapshot)
    shutil.copytree(work,snapshot)
    rows.append(run('warm',True))
    if rows[-1]['exit_code']!=0 or rows[-1]['tests_executed']:raise RuntimeError('Warm Maven control failed')
    for name,select in [('ordinary_change',True),('changed_full',False)]:
        shutil.rmtree(work);shutil.copytree(snapshot,work)
        p=work/'src/main/java/lab/Arithmetic.java';p.write_text(p.read_text().replace('return left + right;','return left + right + 1;'))
        p=work/'src/main/java/lab/Label.java';p.write_text(p.read_text().replace('return "ready";','return new String("ready");'))
        # Explicitly remove compiled application classes to avoid timestamp-only build cache decisions.
        shutil.rmtree(work/'target/classes')
        rows.append(run(name,select))
    if [len(r['tests_executed']) for r in rows]!=[4,0,3,4] or [len(r['tests_failed']) for r in rows]!=[0,0,2,2]:
        raise RuntimeError('Unexpected integration outcomes; inspect logs, do not infer success')
    (out/'results.json').write_text(json.dumps(rows,indent=2)+'\n')
    (out/'protocol.json').write_text(json.dumps({'scope':'supplemental integration controls only; no Maven fault matrix',
      'maven':'3.8.8','surefire':'2.22.2','ekstazi':'5.3.0','mode':'select + restore; explicit local excludesFile',
      'network':'Maven offline -o for all four measured runs','setup_failures_retained_separately':True},indent=2)+'\n')

if __name__=='__main__':main()
