#!/usr/bin/env python3
"""Read-only, commit-pinned configuration audit of a purposive Java sample.

No repository code, workflow, build, or hook is executed. The initial names
are a convenience sample, NOT a probability sample of Java deployments.
"""
import argparse
import concurrent.futures as cf
import csv
import datetime as dt
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parent
NAMES = sorted(['bcel', 'beanutils', 'cli', 'codec', 'collections', 'compress',
                'configuration', 'crypto', 'csv', 'dbcp', 'dbutils', 'digester',
                'email', 'exec', 'io', 'lang', 'math', 'numbers', 'pool', 'text'])
SIGNALS = {
    'ekstazi': re.compile(r'ekstazi', re.I),
    'starts': re.compile(r'(?:edu\.illinois:starts|starts-maven-plugin|<artifactId>starts</artifactId>|STARTS regression)', re.I),
    'testmon': re.compile(r'(?:pytest[-_]testmon|--testmon|\.testmondata)'),
    'clover_test_optimization': re.compile(r'(?:clover:optimize|<artifactId>clover-maven-plugin</artifactId>|<testOptimization>)', re.I),
}

def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def resolve(name):
    url = 'https://github.com/apache/commons-' + name + '.git'
    try:
        p = subprocess.run(['git', 'ls-remote', '--symref', url, 'HEAD'],
                           capture_output=True, text=True, timeout=60)
    except Exception as e:
        return {'name':name,'repository':url,'status':'resolve_failed','error':str(e)}
    if p.returncode:
        return {'name':name,'repository':url,'status':'resolve_failed','error':p.stderr[:2000]}
    lines = p.stdout.splitlines()
    sha = next((x.split()[0] for x in lines if re.match(r'^[0-9a-f]{40}\s+HEAD$',x)), None)
    branch = next((x.split()[1] for x in lines if x.startswith('ref: ')), None)
    return {'name':name,'repository':url,'sha':sha,'branch':branch,
            'resolved_at_utc':utc(),'status':'resolved' if sha else 'resolve_failed',
            'ls_remote':p.stdout}

def is_config(path):
    pp = Path(path)
    return (pp.name in {'pom.xml','build.gradle','build.gradle.kts','Jenkinsfile',
                        '.travis.yml','build.xml','gradle.properties'}
            or path.startswith('.github/workflows/')
            or path.startswith('.circleci/')
            or pp.name.startswith('Jenkinsfile'))

def retrieve(item):
    if item['status'] != 'resolved':
        return item
    out = dict(item)
    url = f"https://codeload.github.com/apache/commons-{item['name']}/tar.gz/{item['sha']}"
    try:
        with urllib.request.urlopen(url, timeout=90) as r:
            data = r.read(80*1024*1024+1)
        if len(data)>80*1024*1024:
            raise ValueError('archive exceeds configured 80 MiB cap')
        archive_dir = ROOT/'archives'
        archive_dir.mkdir(exist_ok=True)
        archive = archive_dir/f"commons-{item['name']}-{item['sha']}.tar.gz"
        archive.write_bytes(data)
        out.update(archive_url=url, archive_path=str(archive.relative_to(ROOT)),
                   archive_sha256=hashlib.sha256(data).hexdigest(), archive_bytes=len(data),
                   retrieved_at_utc=utc())
        destination = ROOT/'snapshots'/f"commons-{item['name']}"
        destination.mkdir(parents=True, exist_ok=True)
        configs=[]
        source_counts={'production_java':0,'test_java':0}
        docs=[]
        with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                parts=Path(m.name).parts
                if len(parts)<2 or '..' in parts:
                    continue
                rel='/'.join(parts[1:])
                if '/src/main/java/' in '/'+rel and rel.endswith('.java'):
                    source_counts['production_java']+=1
                if '/src/test/java/' in '/'+rel and rel.endswith('.java'):
                    source_counts['test_java']+=1
                if is_config(rel):
                    blob=tf.extractfile(m).read()
                    local=destination/rel
                    local.parent.mkdir(parents=True,exist_ok=True)
                    local.write_bytes(blob)
                    content=blob.decode('utf-8',errors='replace')
                    matches=[]
                    for num,line in enumerate(content.splitlines(),1):
                        for signal,pattern in SIGNALS.items():
                            if pattern.search(line):
                                matches.append({'signal':signal,'line':num,'text':line.strip()})
                    configs.append({'path':rel,'sha256':hashlib.sha256(blob).hexdigest(),
                                    'bytes':len(blob),'matches':matches})
                elif m.size<1024*1024 and (rel.endswith('.md') or '/site/' in rel or rel.endswith('.txt')):
                    content=tf.extractfile(m).read().decode('utf-8',errors='replace')
                    if re.search('ekstazi|pytest-testmon',content,re.I):
                        docs.append(rel)
        out.update(status='inspected',source_counts=source_counts,config_files=configs,
                   documentation_paths_with_mentions=docs)
    except Exception as e:
        out.update(status='retrieve_failed',error=str(e))
    return out

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,help='Replay these previously frozen commit IDs.')
    parser.add_argument('--refresh',action='store_true',help='Resolve new default-branch HEADs instead of replaying the existing manifest.')
    args=parser.parse_args()
    protocol={
      'frozen_at_utc':utc(),'sample_type':'purposive convenience sample',
      'sample_frame':'20 named Apache Commons Java components, selected by the researcher before this script scans their contents',
      'repositories':['apache/commons-'+x for x in NAMES],
      'scope':'Current default-branch HEAD, resolved to immutable commits before scanning. POMs, Gradle, Ant, Jenkins, GitHub Actions, Travis, CircleCI files are scanned.',
      'denominator':'Only successfully retrieved and inspected repositories; failures remain in manifest.',
      'not_measured':['actual CI executions','branch protection settings','private/shared workflow contents','deployment population prevalence'],
      'selection_bias':'Single-organization and shared-parent sample; search results had already suggested Ekstazi references in commons-math and commons-numbers. This is not a blinded or representative prevalence estimate.',
      'safety':'Read-only public source retrieval; no repository code or CI executed.',
    }
    frozen=args.manifest or ROOT/'frozen_repository_manifest.json'
    if frozen.exists() and not args.refresh:
        items=json.loads(frozen.read_text())
    else:
        (ROOT/'sampling_protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
        with cf.ThreadPoolExecutor(max_workers=4) as pool:
            items=list(pool.map(resolve,NAMES))
        (ROOT/'frozen_repository_manifest.json').write_text(json.dumps(items,indent=2)+'\n')
    print('Resolved',sum(x['status']=='resolved' for x in items),'of',len(items),flush=True)
    with cf.ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(retrieve,items))
    (ROOT/'repository_audit_raw.json').write_text(json.dumps(results,indent=2)+'\n')
    rows=[]
    for x in results:
        matches=[dict(path=f['path'],**m) for f in x.get('config_files',[]) for m in f['matches']]
        rows.append({'repository':'apache/commons-'+x['name'],'commit':x.get('sha',''),
                     'inspection_status':x['status'],'config_file_count':len(x.get('config_files',[])),
                     'production_java_files':x.get('source_counts',{}).get('production_java',''),
                     'test_java_files':x.get('source_counts',{}).get('test_java',''),
                     'ekstazi_config_mention':any(m['signal']=='ekstazi' for m in matches),
                     'testmon_config_mention':any(m['signal']=='testmon' for m in matches),
                     'other_rts_config_mention':any(m['signal'] in ['starts','clover_test_optimization'] for m in matches),
                     'evidence_paths':';'.join(sorted(set(m['path'] for m in matches)))})
    with (ROOT/'repository_screen.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    print(json.dumps(rows,indent=2),flush=True)

if __name__=='__main__':
    main()
