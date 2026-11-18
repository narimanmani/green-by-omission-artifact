"""Controlled native Ekstazi canonical-fingerprint study. No production targets."""
import csv, hashlib, json, os, shutil, subprocess, sys, tempfile, time
import xml.etree.ElementTree as ET
from pathlib import Path
R=Path(__file__).resolve().parents[1]
OUT=Path(sys.argv[1]).resolve(); OUT.mkdir(parents=True,exist_ok=True)
P=R/'src/main/java/lab/ExpiryGate.java'
U=R/'src/main/java/lab/Unrelated.java'
CF=R/'target/classes/lab/ExpiryGate.class'
JAR=Path.home()/'.m2/repository/org/ekstazi/org.ekstazi.core/5.3.0/org.ekstazi.core-5.3.0.jar'
RUNNER=Path(__file__).resolve().parent
CP=os.pathsep.join([str(RUNNER),str(JAR)])
PAD='0000000000000000'
T='''package lab;
public final class ExpiryGate {{
    public static final String PAD = "{pad}";
    private ExpiryGate() {{}}
    public static boolean accept(int issued, int now, int maxAge) {{
        return (now - issued) <= maxAge{suffix};
    }}
}}
'''
rows=[]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def cmd(args,check=True,timeout=180):
    x=subprocess.run(args,cwd=R,capture_output=True,text=True,timeout=timeout)
    if check and x.returncode: raise RuntimeError(str(args)+'\n'+x.stdout+'\n'+x.stderr)
    return x

def save_metadata(label):
    d=OUT/(label+'-metadata');
    if d.exists(): shutil.rmtree(d)
    if (R/'.ekstazi').is_dir(): shutil.copytree(R/'.ekstazi',d)

def run(label,profile=True):
    reports=R/'target/surefire-reports'
    if reports.exists(): shutil.rmtree(reports)
    args=['mvn','-B','-ntp']+(['-Pekstazi'] if profile else [])+['test']
    start=time.perf_counter();x=cmd(args,check=False)
    (OUT/(label+'.log')).write_text(x.stdout+'\n'+x.stderr)
    tests=[]
    if reports.exists():
        shutil.copytree(reports,OUT/(label+'-surefire'))
        for f in reports.glob('TEST-*.xml'):
            for c in ET.parse(f).getroot().findall('testcase'):
                outcome='failed' if c.find('failure') is not None else 'error' if c.find('error') is not None else 'skipped' if c.find('skipped') is not None else 'passed'
                tests.append({'class':c.get('classname'),'name':c.get('name'),'outcome':outcome})
    row={'condition':label,'exit':x.returncode,'seconds':round(time.perf_counter()-start,4),'tests':tests}
    rows.append(row); (OUT/'outcomes.json').write_text(json.dumps(rows,indent=2));save_metadata(label)
    print('OBSERVED '+json.dumps(row),flush=True)
    return row

def fingerprint(data):
    with tempfile.NamedTemporaryFile(suffix='.class') as f:
        f.write(data);f.flush()
        return int(cmd(['java','-cp',CP,'HashProbe',f.name]).stdout.strip(),16)

def compile_source(pad=PAD,suffix=''):
    P.write_text(T.format(pad=pad,suffix=suffix))
    cmd(['mvn','-B','-ntp','-DskipTests','compile'])
    return CF.read_bytes()

def collision(target_crc):
    start=time.perf_counter();raw=compile_source(suffix=' + 10')
    marker=PAD.encode();assert raw.count(marker)==1
    offset=raw.index(marker);raw_crc=fingerprint(raw)
    columns=[]
    for i in range(16):
        for b in range(4):
            changed=bytearray(raw);changed[offset+i]^=1<<b
            columns.append(fingerprint(changed)^raw_crc)
    basis={}
    for i,value in enumerate(columns):
        v=value;m=1<<i
        while v:
            pivot=v.bit_length()-1
            if pivot not in basis: basis[pivot]=(v,m);break
            x,y=basis[pivot];v^=x;m^=y
    assert len(basis)==32, ('insufficient controllable fingerprint bits',len(basis))
    v=target_crc^raw_crc;answer=0
    while v:
        x,y=basis[v.bit_length()-1];v^=x;answer^=y
    chars=[0]*16
    for bit in range(64):
        if answer>>bit&1: chars[bit//4]^=1<<(bit%4)
    padding=''.join(chr(ord('0')^n) for n in chars)
    final=compile_source(padding,' + 10')
    assert fingerprint(final)==target_crc
    (OUT/'collision.java').write_bytes(P.read_bytes());(OUT/'collision.class').write_bytes(final)
    proof={'baseline_canonical_crc32':target_crc,'candidate_canonical_crc32':fingerprint(final),'ordinary_canonical_crc32':raw_crc,'padding':padding,'seconds':round(time.perf_counter()-start,4),'rank':len(basis),'candidate_class_sha256':hashlib.sha256(final).hexdigest()}
    (OUT/'collision-proof.json').write_text(json.dumps(proof,indent=2));print('CANONICAL_COLLISION '+json.dumps(proof),flush=True)
    return final

def restore():
    if (R/'.ekstazi').exists(): shutil.rmtree(R/'.ekstazi')
    shutil.copytree(OUT/'trusted-baseline-metadata',R/'.ekstazi')

def tests_hash(): return {str(p.relative_to(R)):sha(p) for p in (R/'src/test').rglob('*.java')}

for d in ['target','.ekstazi']:
    if (R/d).exists(): shutil.rmtree(R/d)
P.write_text(T.format(pad=PAD,suffix=''))
protected=tests_hash();original_other=U.read_bytes()
(OUT/'java-version.log').write_text(cmd(['java','-version']).stderr)
(OUT/'maven-version.log').write_text(cmd(['mvn','-version']).stdout)
a=run('baseline');assert a['exit']==0 and len(a['tests'])==3
baseline=CF.read_bytes();(OUT/'baseline.class').write_bytes(baseline);(OUT/'baseline.java').write_bytes(P.read_bytes())
shutil.copytree(R/'.ekstazi',OUT/'trusted-baseline-metadata')
assert JAR.is_file();cmd(['javac','-cp',str(JAR),'-d',str(RUNNER),str(RUNNER/'HashProbe.java')])
base_crc=fingerprint(baseline)
b=run('nochange');assert b['exit']==0 and len(b['tests'])==0
compile_source(suffix=' + 10')
c=run('ordinary');assert c['exit']!=0 and any(t['name']=='rejectsExpired' and t['outcome']=='failed' for t in c['tests'])
restore();collided=collision(base_crc)
assert hashlib.sha256(collided).digest()!=hashlib.sha256(baseline).digest()
d=run('collision')
f=run('collision_full',False);assert f['exit']!=0 and any(t['name']=='rejectsExpired' and t['outcome']=='failed' for t in f['tests'])
# Nonzero variant changes a separate harmless production class; tests stay fixed.
restore();U.write_text(original_other.decode().replace('return v * v;', 'return (v * v) + 0;'))
g=run('collision_nonzero')
h=run('collision_nonzero_full',False)
assert tests_hash()==protected
summary={'native_collision_missed':d['exit']==0 and not d['tests'],'native_nonzero_missed':g['exit']==0 and any(t['outcome']=='passed' for t in g['tests']) and not any(t['class']=='lab.ExpiryGateTest' for t in g['tests']),'full_detected':f['exit']!=0 and h['exit']!=0,'tests_unchanged':True,'baseline_class_sha256':hashlib.sha256(baseline).hexdigest(),'baseline_crc32':base_crc,'core_jar_sha256':sha(JAR),'note':'Controlled Java fixture; PAD present before baseline; nonzero condition may need non-constant benign refactor.'}
(OUT/'summary.json').write_text(json.dumps(summary,indent=2));print('RESEARCH_RESULT '+json.dumps(summary),flush=True)
