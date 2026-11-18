#!/usr/bin/env python3
"""Summarize the pinned configuration corpus; no repository code is run."""
import csv, hashlib, json, re, urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parent
NS={'m':'http://maven.apache.org/POM/4.0.0'}

def coordinate_parent(x):
    p=x.find('m:parent',NS)
    return None if p is None else tuple(p.findtext('m:'+k,None,NS) for k in ['groupId','artifactId','version'])

def fetch_parents(items):
    records={}
    todo=[]
    for item in items:
        if item['status']!='inspected':continue
        x=ET.fromstring((ROOT/'snapshots'/('commons-'+item['name'])/'pom.xml').read_bytes())
        p=coordinate_parent(x)
        if p:todo.append(p)
    directory=ROOT/'parent_poms';directory.mkdir(exist_ok=True)
    while todo:
        g,a,v=todo.pop(0);key=f'{g}:{a}:{v}'
        if key in records:continue
        url=f"https://repo.maven.apache.org/maven2/{g.replace('.', '/')}/{a}/{v}/{a}-{v}.pom"
        try:
            with urllib.request.urlopen(url,timeout=30) as r:blob=r.read()
            path=directory/f'{a}-{v}.pom';path.write_bytes(blob)
            x=ET.fromstring(blob);p=coordinate_parent(x)
            if p:todo.append(p)
            matches=[]
            for n,line in enumerate(blob.decode().splitlines(),1):
                if re.search(r'ekstazi|pytest[-_]testmon|--testmon|starts-maven-plugin|clover:optimize',line,re.I):
                    matches.append({'line':n,'text':line.strip()})
            records[key]={'coordinate':key,'url':url,'path':str(path.relative_to(ROOT)),
                          'sha256':hashlib.sha256(blob).hexdigest(),'status':'inspected',
                          'parent':':'.join(p) if p else None,
                          'defaultGoal':x.findtext('m:build/m:defaultGoal',None,NS),
                          'rts_mentions':matches}
        except Exception as e:
            records[key]={'coordinate':key,'url':url,'status':'failed','error':str(e)}
    (ROOT/'parent_pom_manifest.json').write_text(json.dumps(list(records.values()),indent=2)+'\n')
    return records

def main():
    items=json.loads((ROOT/'repository_audit_raw.json').read_text())
    parents=fetch_parents(items)
    rows=[]
    for item in items:
        if item['status']!='inspected':continue
        base=ROOT/'snapshots'/('commons-'+item['name'])
        x=ET.fromstring((base/'pom.xml').read_bytes());p=coordinate_parent(x)
        goal=x.findtext('m:build/m:defaultGoal',None,NS)
        if not goal and p:goal=parents.get(':'.join(p),{}).get('defaultGoal')
        profile_records=[]
        for pro in x.findall('m:profiles/m:profile',NS):
            for plug in pro.findall('m:build/m:plugins/m:plugin',NS):
                if plug.findtext('m:groupId',None,NS)=='org.ekstazi':
                    profile_records.append({
                      'profile_id':pro.findtext('m:id',None,NS),
                      'activation_property':pro.findtext('m:activation/m:property/m:name',None,NS),
                      'activation_value':pro.findtext('m:activation/m:property/m:value',None,NS),
                      'active_by_default':pro.findtext('m:activation/m:activeByDefault','false',NS),
                      'artifact':plug.findtext('m:artifactId',None,NS),
                      'version':plug.findtext('m:version',None,NS)})
        ci_file=base/'.github/workflows/maven.yml'
        ci=yaml.load(ci_file.read_text(),Loader=yaml.BaseLoader)
        on=ci.get('on',{})
        if isinstance(on,str):events=[on]
        else:events=list(on)
        jobs=ci.get('jobs',{});steps=[s for job in jobs.values() for s in job.get('steps',[])]
        actions=[s['uses'] for s in steps if 'uses' in s]
        checkouts=[s for s in steps if s.get('uses','').startswith('actions/checkout@')]
        caches=[s.get('with',{}) for s in steps if s.get('uses','').startswith('actions/cache@')]
        commands=[s['run'] for s in steps if 'run' in s]
        all_ci='\n'.join((base/f['path']).read_text(errors='replace') for f in item['config_files'] if f['path'].startswith('.github/workflows/'))
        findings={
          'repository':'apache/commons-'+item['name'],'commit':item['sha'],
          'upstream_source_url':f"https://github.com/apache/commons-{item['name']}/tree/{item['sha']}",
          'config_files_inspected':len(item['config_files']),
          'java_production_files':item['source_counts']['production_java'],
          'java_test_files':item['source_counts']['test_java'],
          'root_parent':':'.join(p) if p else None,
          'ekstazi_optional_profiles':profile_records,
          'ekstazi_reference_any_workflow':bool(re.search('ekstazi',all_ci,re.I)),
          'testmon_reference_any_configuration':any(m['signal']=='testmon' for f in item['config_files'] for m in f['matches']),
          'primary_workflow':'.github/workflows/maven.yml',
          'primary_workflow_events':events,
          'primary_pull_request_trigger':'pull_request' in events,
          'primary_permissions':ci.get('permissions'),
          'primary_contents_permission_read':isinstance(ci.get('permissions'),dict) and ci['permissions'].get('contents')=='read',
          'primary_actions':actions,
          'primary_all_actions_pinned_40hex':bool(actions) and all(re.search(r'@[a-f0-9]{40}$',a) for a in actions),
          'primary_checkouts_persist_credentials_false':bool(checkouts) and all(s.get('with',{}).get('persist-credentials')=='false' for s in checkouts),
          'primary_cache_configuration':caches,
          'primary_maven_dependency_cache':any('.m2' in c.get('path','') for c in caches),
          'primary_run_commands':commands,
          'resolved_default_goal':goal,
          'branch_protection':'not_observed',
          'required_status_checks':'not_observed',
          'live_ci_use_of_ekstazi':'not_observed',
          'rts_metadata_integrity_verification':'no_explicit_reference_in_inspected_workflows',
        }
        rows.append(findings)
    (ROOT/'repository_audit_summary.json').write_text(json.dumps(rows,indent=2)+'\n')
    flat=[]
    for x in rows:
        flat.append({k:v for k,v in x.items() if isinstance(v,(str,int,float,bool)) or v is None})
        flat[-1]['ekstazi_profile_versions']=';'.join(p['version'] for p in x['ekstazi_optional_profiles'])
        flat[-1]['primary_workflow_events']=';'.join(x['primary_workflow_events'])
    with (ROOT/'repository_audit_summary.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(flat[0]));w.writeheader();w.writerows(flat)
    totals={
      'repositories_inspected':len(rows),
      'configuration_files_inspected':sum(x['config_files_inspected'] for x in rows),
      'parent_poms_inspected':sum(p['status']=='inspected' for p in parents.values()),
      'optional_ekstazi_profile_declared':sum(bool(x['ekstazi_optional_profiles']) for x in rows),
      'ekstazi_any_workflow_reference':sum(x['ekstazi_reference_any_workflow'] for x in rows),
      'testmon_any_configuration_reference':sum(x['testmon_reference_any_configuration'] for x in rows),
      'primary_pull_request_trigger':sum(x['primary_pull_request_trigger'] for x in rows),
      'primary_contents_permission_read':sum(x['primary_contents_permission_read'] for x in rows),
      'primary_all_actions_pinned_40hex':sum(x['primary_all_actions_pinned_40hex'] for x in rows),
      'primary_checkouts_persist_credentials_false':sum(x['primary_checkouts_persist_credentials_false'] for x in rows),
      'primary_maven_dependency_cache':sum(x['primary_maven_dependency_cache'] for x in rows),
      'selection':'purposive convenience sample; descriptive counts only; no population inference',
      'scope_note':'Configuration indicators are not evidence that a workflow ran, was mandatory, or actually used RTS. Native deployment prevalence remains unmeasured.',
    }
    (ROOT/'audit_totals.json').write_text(json.dumps(totals,indent=2)+'\n')
    print(json.dumps(totals,indent=2))

if __name__=='__main__':main()
