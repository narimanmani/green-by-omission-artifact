#!/usr/bin/env python3
"""Reproduce fixed synthetic experiments in a NEW local directory.

Preparation downloads public version-pinned dependencies. Experimental JVM/
pytest invocations use only local generated fixtures. No repository target or
fingerprint-forging interface is provided. Original evidence is never overwritten.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parent
PINNED={
 'jdk8.tar.gz':('https://github.com/adoptium/temurin8-binaries/releases/download/jdk8u432-b06/OpenJDK8U-jdk_x64_linux_hotspot_8u432b06.tar.gz','abaaa90deadf51bd28921453baf2992b3dff6171bb7142f5bdd14ef269f7b245'),
 'maven.tar.gz':('https://repo.maven.apache.org/maven2/org/apache/maven/apache-maven/3.8.8/apache-maven-3.8.8-bin.tar.gz','17811e108701af5985bf5167abbd47c06e92c6c6bd1c13a1a1c095c9b4ecc32a'),
 'org.ekstazi.core-5.3.0.jar':('https://repo.maven.apache.org/maven2/org/ekstazi/org.ekstazi.core/5.3.0/org.ekstazi.core-5.3.0.jar','baf7affe8fc42e12b382ec933f3572fce417e5e0d9a7ebab2902bc5c614cb749'),
 'junit-4.13.2.jar':('https://repo.maven.apache.org/maven2/junit/junit/4.13.2/junit-4.13.2.jar','8e495b634469d64fb8acfa3495a065cbacc8a0fff55ce1e31007be4c16dc57d3'),
 'hamcrest-core-1.3.jar':('https://repo.maven.apache.org/maven2/org/hamcrest/hamcrest-core/1.3/hamcrest-core-1.3.jar','66fdef91e9739348df7a096aa384a5685f4e875584cce89386a7a47251c4d8e9'),
}

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def run(cmd,**kwargs):
    print('Running:', ' '.join(map(str,cmd)),flush=True)
    subprocess.run(list(map(str,cmd)),check=True,**kwargs)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--destination',type=Path,required=True,help='Must not already exist')
    ap.add_argument('--component',choices=['all','ekstazi','maven','testmon','wrappers'],default='all')
    ap.add_argument('--repetitions',type=int,default=3)
    args=ap.parse_args();dest=args.destination.resolve()
    if dest.exists():raise SystemExit('Destination already exists; choose a fresh directory to preserve evidence.')
    if sys.version_info[:2]!=(3,12):raise SystemExit('Use Python 3.12 for this pinned reproduction.')
    if args.repetitions<1:raise SystemExit('Repetitions must be positive.')
    wants_java=args.component in ['all','ekstazi','maven','wrappers']
    if wants_java and (platform.system()!='Linux' or platform.machine() not in ['x86_64','AMD64']):
        raise SystemExit('The pinned JDK distribution targets Linux x86_64. Use a local Linux x86_64 environment.')
    dest.mkdir(parents=True)
    tc=dest/'toolchain';tc.mkdir()
    if wants_java:
        wanted=['jdk8.tar.gz','org.ekstazi.core-5.3.0.jar','junit-4.13.2.jar','hamcrest-core-1.3.jar']
        if args.component in ['all','maven']:wanted.append('maven.tar.gz')
        for name in wanted:
            url,expected=PINNED[name];target=tc/name;included=ROOT/'toolchain'/name
            if included.exists() and sha(included)==expected:shutil.copy2(included,target)
            else:
                print('Preparing pinned dependency:',name,flush=True)
                with urllib.request.urlopen(url,timeout=60) as response,target.open('wb') as output:
                    shutil.copyfileobj(response,output)
            if sha(target)!=expected:raise RuntimeError('Dependency checksum mismatch: '+name)
            if name.endswith('.tar.gz'):
                with tarfile.open(target) as tf:tf.extractall(tc,filter='data')
        (tc/'manifest.json').write_text(json.dumps({n:{'url':PINNED[n][0],'sha256':PINNED[n][1]} for n in wanted},indent=2)+'\n')
    if args.component in ['all','ekstazi','maven']:
        study=dest/'ekstazi_study';study.mkdir()
        for name in ['TraceRunner.java','run_experiments.py','run_maven_validation.py']:shutil.copy2(ROOT/'ekstazi_study'/name,study/name)
        shutil.copytree(ROOT/'ekstazi_study/fixture',study/'fixture')
        if args.component in ['all','ekstazi']:
            run([sys.executable,study/'run_experiments.py','--repetitions',str(args.repetitions)])
        if args.component in ['all','maven']:
            # Preparation may fetch build dependencies; it is excluded from the four offline measured checks.
            prep=dest/'prepare_maven';shutil.copytree(study/'fixture',prep)
            env=os.environ.copy();env['JAVA_HOME']=str(tc/'jdk8u432-b06');env['PATH']=env['JAVA_HOME']+'/bin:'+env['PATH']
            cmd=[tc/'apache-maven-3.8.8/bin/mvn','-B','-ntp','-Dmaven.repo.local='+str(tc/'m2'),'-Pekstazi','test']
            proxy=urllib.parse.urlparse(env.get('HTTPS_PROXY',env.get('HTTP_PROXY','')))
            if proxy.hostname:
                settings=ET.Element('settings');proxies=ET.SubElement(settings,'proxies');p=ET.SubElement(proxies,'proxy')
                entries={'id':'environment-proxy','active':'true','protocol':'http','host':proxy.hostname,'port':str(proxy.port or 80),'nonProxyHosts':'localhost|127.0.0.1'}
                if proxy.username:entries['username']=urllib.parse.unquote(proxy.username)
                if proxy.password:entries['password']=urllib.parse.unquote(proxy.password)
                for k,v in entries.items():ET.SubElement(p,k).text=v
                settings_path=dest/'.maven_network_settings.xml';ET.ElementTree(settings).write(settings_path,encoding='utf-8');settings_path.chmod(0o600)
                cmd[1:1]=['-s',settings_path]
                if Path('/etc/ssl/certs/java/cacerts').exists():env['MAVEN_OPTS']=env.get('MAVEN_OPTS','')+' -Djavax.net.ssl.trustStore=/etc/ssl/certs/java/cacerts'
            with (dest/'maven_dependency_preparation.log').open('w') as log:run(cmd,cwd=prep,env=env,stdout=log,stderr=subprocess.STDOUT)
            run([sys.executable,study/'run_maven_validation.py'])
    if args.component in ['all','wrappers']:
        p=dest/'project_sample';p.mkdir()
        for name in ['run_wrapper_pilots.py','analyze_results.py','pilot_artifact_manifest.json']:shutil.copy2(ROOT/'project_sample'/name,p/name)
        shutil.copytree(ROOT/'project_sample/pilot_artifacts',p/'pilot_artifacts')
        for item in json.loads((p/'pilot_artifact_manifest.json').read_text()):
            for f in item['files']:
                if sha(p/f['path'])!=f['sha256']:raise RuntimeError('Published library artifact hash mismatch')
        run([sys.executable,p/'run_wrapper_pilots.py'])
        # Per-project raw outputs are self-contained; aggregate reproduction does not resample repositories.
    if args.component in ['all','testmon']:
        p=dest/'testmon_pilot';p.mkdir()
        for name in ['run_testmon_pilot.py','analyze_testmon.py','requirements.txt','requirements-lock.txt']:shutil.copy2(ROOT/'testmon_pilot'/name,p/name)
        run([sys.executable,'-m','venv',p/'venv']);python=p/'venv/bin/python'
        run([python,'-m','pip','install','-r',p/'requirements-lock.txt'])
        run([python,p/'run_testmon_pilot.py','--repetitions',str(args.repetitions)])
        run([python,p/'analyze_testmon.py'])
    print('New evidence directory:',dest,flush=True)

if __name__=='__main__':main()
