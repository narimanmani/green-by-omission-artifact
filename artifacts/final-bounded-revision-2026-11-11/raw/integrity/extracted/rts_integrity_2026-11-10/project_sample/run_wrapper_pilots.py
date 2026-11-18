#!/usr/bin/env python3
"""Offline native Ekstazi 5.3.0 feasibility pilot on synthetic Java wrappers.

Only generated synthetic code and its generated cache are mutated. Upstream
jars remain untouched. Faults are fixed deletion or 50% byte truncation, never
adaptively chosen. This is NOT an upstream regression-suite experiment.
"""
import argparse
import csv
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

ROOT=Path(__file__).resolve().parent
CASES={
 'cli': {'jar':'commons-cli-1.6.0.jar',
         'imports':'import org.apache.commons.cli.*;',
         'body':'Options options = new Options(); options.addOption("v", false, "verbose"); String value = String.valueOf(new DefaultParser().parse(options, new String[]{"-v"}).hasOption("v"));',
         'expected':'true'},
 'csv': {'jar':'commons-csv-1.10.0.jar',
         'imports':'import org.apache.commons.csv.*; import java.io.StringReader;',
         'body':'String value; try (CSVParser parser = CSVFormat.DEFAULT.parse(new StringReader("a,b\\n"))) { value = parser.getRecords().get(0).get(1); }',
         'expected':'b'},
 'codec': {'jar':'commons-codec-1.16.0.jar',
           'imports':'import org.apache.commons.codec.binary.Hex;',
           'body':'String value = Hex.encodeHexString(new byte[]{0x0a});',
           'expected':'0a'},
 'io': {'jar':'commons-io-2.15.0.jar',
        'imports':'import org.apache.commons.io.FilenameUtils;',
        'body':'String value = FilenameUtils.getExtension("report.csv");',
        'expected':'csv'},
 'lang': {'jar':'commons-lang3-3.14.0.jar',
          'imports':'import org.apache.commons.lang3.StringUtils;',
          'body':'String value = StringUtils.reverse("abc");',
          'expected':'cba'},
}
HARNESS='''package harness;
import org.junit.runner.JUnitCore;
import org.junit.runner.Result;
import org.junit.runner.Description;
import org.junit.runner.notification.RunListener;
import org.junit.runner.notification.Failure;
public class Main {
 public static void main(String[] args) throws Exception {
  JUnitCore core = new JUnitCore();
  core.addListener(new RunListener() {
   public void testStarted(Description d) { System.out.println("@@START " + d.getClassName() + "#" + d.getMethodName()); }
   public void testFailure(Failure f) { System.out.println("@@FAIL " + f.getDescription().getClassName() + "#" + f.getDescription().getMethodName() + " " + f.getMessage()); }
  });
  Class<?>[] cs = new Class<?>[args.length];
  for (int i=0;i<args.length;i++) cs[i]=Class.forName(args[i]);
  Result result=core.run(cs);
  System.out.println("@@RESULT run="+result.getRunCount()+" failures="+result.getFailureCount()+" ignored="+result.getIgnoreCount());
  System.exit(result.wasSuccessful()?0:1);
 }
}
'''
TESTS=['pilot.SubjectTest','pilot.ControlTest','pilot.UntouchedTest']

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def manifest(directory):
    return {str(p.relative_to(directory)):sha(p) for p in sorted(directory.rglob('*')) if p.is_file()} if directory.exists() else {}

def copy_metadata(source,target):
    if target.exists():shutil.rmtree(target)
    shutil.copytree(source,target)

def write_fixture(work,case,mutate=False):
    src=work/'src'/'pilot';src.mkdir(parents=True,exist_ok=True)
    suffix=' + "!"' if mutate else ''
    (src/'Subject.java').write_text('package pilot;\n'+case['imports']+'\npublic class Subject { public static String value() throws Exception { '+case['body']+' return value'+suffix+'; } }\n')
    control='"CONTROL".toLowerCase(java.util.Locale.ROOT)' if mutate else '"control"'
    (src/'Control.java').write_text('package pilot;\npublic class Control { public static String value() { return '+control+'; } }\n')
    (src/'Untouched.java').write_text('package pilot;\npublic class Untouched { public static String value() { return "untouched"; } }\n')
    for cls,expected in [('Subject',case['expected']),('Control','control'),('Untouched','untouched')]:
        (src/(cls+'Test.java')).write_text('package pilot;\nimport org.junit.Test; import static org.junit.Assert.assertEquals;\npublic class '+cls+'Test { @Test public void valueMatches() throws Exception { assertEquals("'+expected+'", '+cls+'.value()); } }\n')

def compile_fixture(work,javac,cp):
    output=work/'classes';output.mkdir(exist_ok=True)
    cmd=[str(javac),'-source','1.8','-target','1.8','-encoding','UTF-8','-cp',cp,'-d',str(output)]+[str(p) for p in sorted((work/'src').rglob('*.java'))]
    p=subprocess.run(cmd,capture_output=True,text=True,timeout=60)
    (work/'compile.log').write_text(p.stdout+p.stderr)
    if p.returncode:raise RuntimeError('javac failed for '+str(work)+': '+p.stderr)

def invoke(work,java,agent,cp,selective,log):
    cmd=[str(java),'-Duser.home='+str(work/'home')]
    if selective:cmd+=['-javaagent:'+str(agent)+'=mode=junit']
    cmd+=['-cp',str(work/'classes')+os.pathsep+cp,'harness.Main']+TESTS
    start=time.perf_counter()
    p=subprocess.run(cmd,cwd=work,capture_output=True,text=True,timeout=90)
    elapsed=time.perf_counter()-start
    combined=p.stdout+p.stderr
    log.write_text(combined)
    counts=re.search(r'@@RESULT run=(\d+) failures=(\d+) ignored=(\d+)',p.stdout)
    return {'command':cmd,'returncode':p.returncode,'elapsed_seconds':elapsed,
            'run_count':int(counts[1]) if counts else None,
            'failure_count':int(counts[2]) if counts else None,
            'ignored_count':int(counts[3]) if counts else None,
            'executed_tests':re.findall(r'^@@START (.+)$',p.stdout,re.M),
            'failed_tests':re.findall(r'^@@FAIL (\S+)',p.stdout,re.M),
            'stdout_sha256':hashlib.sha256(combined.encode()).hexdigest(),
            'log':str(log.relative_to(ROOT)),
            'parse_status':'parsed' if counts else 'missing_result'}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--toolchain',type=Path,default=ROOT.parent/'toolchain')
    ap.add_argument('--artifact-dir',type=Path,default=ROOT/'pilot_artifacts')
    args=ap.parse_args();tc=args.toolchain.resolve();ad=args.artifact_dir.resolve()
    java=tc/'jdk8u432-b06/bin/java';javac=tc/'jdk8u432-b06/bin/javac'
    agent=tc/'org.ekstazi.core-5.3.0.jar';junit=tc/'junit-4.13.2.jar';hamcrest=tc/'hamcrest-core-1.3.jar'
    out=ROOT/'wrapper_pilot';out.mkdir(exist_ok=True)
    (out/'protocol.json').write_text(json.dumps({
       'created_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
       'scope':'Five synthetic wrappers calling unmodified published Java artifacts; generated JUnit fixtures, not upstream suites.',
       'selectors':'Ekstazi native 5.3.0 agent, mode=junit',
       'tests':TESTS,
       'scenarios':['ordinary_change','target_metadata_missing','target_metadata_truncated_50pct'],
       'fault_rule':'Fixed deletion or first floor(n/2) bytes retained in the generated SubjectTest metadata; no adaptive byte search.',
       'regression':'Synthetic Subject output receives !; independent Control method changes to a semantically equivalent computation.',
       'arms':['standard_rts','fail_closed','full_suite'],
       'integrity_defense':'Out-of-cache trusted SHA256 manifest over all native metadata files; mismatch selects agent-free full suite.',
       'repetitions':1,
       'safety':'No upstream jar/source edits; no network access in experiment commands; no exploit or security-sensitive code.',
       'timing':'Descriptive wall-clock timings in shared environment, not performance benchmarks.',
    },indent=2)+'\n')
    hsrc=out/'harness'/'src'/'harness';hsrc.mkdir(parents=True,exist_ok=True)
    (hsrc/'Main.java').write_text(HARNESS)
    hclasses=out/'harness'/'classes';hclasses.mkdir(exist_ok=True)
    basecp=os.pathsep.join(map(str,[junit,hamcrest]))
    p=subprocess.run([str(javac),'-source','1.8','-target','1.8','-cp',basecp,'-d',str(hclasses),str(hsrc/'Main.java')],capture_output=True,text=True,timeout=60)
    if p.returncode:raise RuntimeError(p.stderr)
    environment={'java_version':subprocess.run([str(java),'-version'],capture_output=True,text=True).stderr,
                 'toolchain_sha256':{p.name:sha(p) for p in [agent,junit,hamcrest]},
                 'library_sha256':{c['jar']:sha(ad/c['jar']) for c in CASES.values()}}
    (out/'environment.json').write_text(json.dumps(environment,indent=2)+'\n')
    results=[]
    for name,case in CASES.items():
        work=out/'work'/name;work.mkdir(parents=True,exist_ok=True)
        (work/'.synthetic-rts-pilot').write_text('generated synthetic fixture\n')
        metadata=work/'.ekstazi'
        if metadata.exists():shutil.rmtree(metadata)
        logs=out/'logs'/name;logs.mkdir(parents=True,exist_ok=True)
        trusted=out/'trusted'/name;trusted.mkdir(parents=True,exist_ok=True)
        cp=os.pathsep.join(map(str,[hclasses,junit,hamcrest,ad/case['jar']]))
        write_fixture(work,case);compile_fixture(work,javac,cp)
        oracle_hashes=manifest(work/'src')
        baseline_class_hashes=manifest(work/'classes')
        for stage,sel in [('cold_baseline',True),('warm_baseline',True),('full_baseline',False)]:
            rr=invoke(work,java,agent,cp,sel,logs/(stage+'.log'))
            rr.update(project=name,artifact=case['jar'],scenario=stage,arm='standard_rts' if sel else 'full_suite',integrity_valid=True,fallback=False)
            results.append(rr)
            print(name,stage,rr['returncode'],rr['run_count'],rr['failure_count'],flush=True)
        if not metadata.exists():raise RuntimeError('Native metadata not generated for '+name)
        baseline=trusted/'metadata'
        if baseline.exists():shutil.rmtree(baseline)
        shutil.copytree(metadata,baseline)
        expected=manifest(baseline)
        (trusted/'sha256_manifest.json').write_text(json.dumps(expected,indent=2)+'\n')
        (trusted/'baseline_source_hashes.json').write_text(json.dumps(oracle_hashes,indent=2)+'\n')
        write_fixture(work,case,mutate=True);compile_fixture(work,javac,cp)
        changed_class_hashes=manifest(work/'classes')
        unchanged_test_sources=all(sha(work/'src'/p)==digest for p,digest in oracle_hashes.items() if p.endswith('Test.java'))
        unchanged_test_classes=all(changed_class_hashes[p]==digest for p,digest in baseline_class_hashes.items() if p.endswith('Test.class'))
        if not unchanged_test_sources or not unchanged_test_classes:raise RuntimeError('Oracle changed')
        target=next((p for p in expected if p=='pilot.SubjectTest.clz'),None)
        if not target:raise RuntimeError('Expected generated target metadata filename absent: '+str(list(expected)))
        for scenario in ['ordinary_change','target_metadata_missing','target_metadata_truncated_50pct']:
            for arm in ['standard_rts','fail_closed','full_suite']:
                copy_metadata(baseline,metadata)
                f=metadata/target;before_size=f.stat().st_size
                if scenario=='target_metadata_missing':f.unlink()
                elif scenario=='target_metadata_truncated_50pct':f.write_bytes(f.read_bytes()[:before_size//2])
                observed=manifest(metadata);valid=observed==expected
                fallback=arm=='fail_closed' and not valid
                sel=arm=='standard_rts' or (arm=='fail_closed' and valid)
                rr=invoke(work,java,agent,cp,sel,logs/(scenario+'__'+arm+'.log'))
                rr.update(project=name,artifact=case['jar'],scenario=scenario,arm=arm,
                          integrity_valid=valid,fallback=fallback,
                          metadata_before_bytes=before_size,
                          target_metadata_fault_bytes=before_size if scenario=='target_metadata_missing' else (before_size-before_size//2 if scenario.endswith('50pct') else 0),
                          input_metadata_manifest=observed,
                          unchanged_test_sources=unchanged_test_sources,
                          unchanged_test_bytecode=unchanged_test_classes,
                          expected_relevant_test='pilot.SubjectTest#valueMatches',
                          relevant_test_executed='pilot.SubjectTest#valueMatches' in rr['executed_tests'],
                          expected_relevant_failure_observed='pilot.SubjectTest#valueMatches' in rr['failed_tests'])
                results.append(rr)
                print(name,scenario,arm,rr['returncode'],rr['run_count'],rr['failure_count'],flush=True)
        (out/'results.json').write_text(json.dumps(results,indent=2)+'\n')
    (out/'results.json').write_text(json.dumps(results,indent=2)+'\n')
    columns=['project','artifact','scenario','arm','run_count','failure_count','returncode','integrity_valid','fallback','relevant_test_executed','expected_relevant_failure_observed','unchanged_test_sources','unchanged_test_bytecode','elapsed_seconds','log']
    with (out/'results.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=columns,extrasaction='ignore');w.writeheader();w.writerows(results)
    print('Completed',len(results),'actual executions.',flush=True)

if __name__=='__main__':main()
