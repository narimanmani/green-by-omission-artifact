#!/usr/bin/env python3
"""Run honest native RTS-baseline eligibility checks on isolated upstream code."""
import argparse,json,pathlib,subprocess,time,traceback,shutil,re,sys,xml.etree.ElementTree as ET
p=argparse.ArgumentParser()
for key in ("repo","sha","name","lang","out"):p.add_argument("--"+key,required=True)
a=p.parse_args();o=pathlib.Path(a.out).resolve();o.mkdir(parents=True,exist_ok=True)
root=o/"upstream";logs=o/"logs";logs.mkdir(exist_ok=True)
r={"repo":a.repo,"sha":a.sha,"name":a.name,"lang":a.lang,"status":"starting",
   "selector":"pytest-testmon 2.3.0" if a.lang=="python" else "Ekstazi 5.3.0",
   "attack_attempted":False,"security_test_mutated":False,"scope":"authentic upstream baseline and no-change only"}
def save():(o/"result.json").write_text(json.dumps(r,indent=2)+"\n")
def cmd(label,args,cwd=None,timeout=150):
    t=time.perf_counter()
    try:
        p=subprocess.run(args,cwd=cwd or root,capture_output=True,text=True,errors="replace",timeout=timeout)
        code=p.returncode;log=p.stdout+"\n"+p.stderr
    except subprocess.TimeoutExpired as e:
        code=124;log=((e.stdout or b"").decode(errors="replace") if isinstance(e.stdout,bytes) else (e.stdout or ""))+"\nTIMEOUT"
    (logs/(label+".log")).write_text(log)
    r[label]={"exit":code,"seconds":round(time.perf_counter()-t,3)}
    save();print("PILOT",a.name,label,code,flush=True)
    return code,log
def py():
    env=o/"venv"
    if cmd("venv",[sys.executable,"-m","venv",str(env)],cwd=o,timeout=65)[0]:raise RuntimeError("venv unavailable")
    python=str(env/"bin/python")
    if cmd("selector_install",[python,"-m","pip","install","pytest==9.0.2","pytest-testmon==2.3.0"],timeout=150)[0]:raise RuntimeError("testmon install failed")
    if cmd("project_install",[python,"-m","pip","install","-e","."],timeout=180)[0]:raise RuntimeError("upstream install failed")
    testfiles=sorted(p for p in root.rglob("test_*.py") if any(x in ("test","tests") for x in p.relative_to(root).parts) and len(p.relative_to(root).parts)<8)
    r["available_testfiles"]=len(testfiles);save()
    node=None
    for i,source in enumerate(testfiles[:3]):
        rel=source.relative_to(root).as_posix()
        code,out=cmd("collect_"+str(i),[python,"-m","pytest","--collect-only","-q",rel],timeout=90)
        cand=[s.strip() for s in out.splitlines() if s.strip().startswith(rel) and ".py::" in s]
        if code==0 and cand:node=cand[0];break
    r["selected_nodeid"]=node;save()
    if not node:raise RuntimeError("no collectable test from first 3 authentic files")
    test_file=node.split("::",1)[0]
    r["selection_scope"]="whole upstream test file, not forced individual node"
    r["test_file"]=test_file
    code,log=cmd("native_baseline",[python,"-m","pytest","-q","--testmon",test_file],timeout=165)
    counts=re.findall(r"\b([0-9]+) passed\b",log)
    r["baseline_pass_count"]=int(counts[-1]) if counts else 0
    if code!=0 or r["baseline_pass_count"]<1:raise RuntimeError("whole-file baseline did not execute passing tests")
    code,log=cmd("native_nochange",[python,"-m","pytest","-q","--testmon",test_file],timeout=135)
    nochange_counts=re.findall(r"\b([0-9]+) passed\b",log)
    r["nochange_pass_count"]=int(nochange_counts[-1]) if nochange_counts else 0
    r["nochange_returncode"]=code
    r["nochange_detected_deselection"]="deselected" in log.lower()
    r["selector_nochange_selected_zero"]=code==0 and r["nochange_pass_count"]==0
    r["status"]="baseline_and_selector_nochange_verified" if r["selector_nochange_selected_zero"] else "baseline_ran_but_selector_nochange_not_zero"
    save()
def java():
    pom=root/"pom.xml"
    if not pom.exists():raise RuntimeError("missing root pom")
    old=pom.read_bytes();(o/"upstream_pom.xml").write_bytes(old)
    ns="http://maven.apache.org/POM/4.0.0";tag=lambda x:"{"+ns+"}"+x
    ET.register_namespace("",ns);tree=ET.parse(pom);doc=tree.getroot()
    profiles=doc.find(tag("profiles"))
    if profiles is None:profiles=ET.SubElement(doc,tag("profiles"))
    profile=ET.SubElement(profiles,tag("profile"));ET.SubElement(profile,tag("id")).text="sp2027-ekstazi"
    build=ET.SubElement(profile,tag("build"));plugins=ET.SubElement(build,tag("plugins"))
    plugin=ET.SubElement(plugins,tag("plugin"))
    for key,value in (("groupId","org.ekstazi"),("artifactId","ekstazi-maven-plugin"),("version","5.3.0")):
        ET.SubElement(plugin,tag(key)).text=value
    executions=ET.SubElement(plugin,tag("executions"));execution=ET.SubElement(executions,tag("execution"));goals=ET.SubElement(execution,tag("goals"))
    for name in ("select","restore"):ET.SubElement(goals,tag("goal")).text=name
    surefire=ET.SubElement(plugins,tag("plugin"))
    for key,value in (("groupId","org.apache.maven.plugins"),("artifactId","maven-surefire-plugin"),("version","3.2.5")):
        ET.SubElement(surefire,tag(key)).text=value
    config=ET.SubElement(surefire,tag("configuration"))
    ET.SubElement(config,tag("excludesFile")).text="$"+"{java.io.tmpdir}/"+"$"+"{user.name}EkstaziExcludes"
    includes=ET.SubElement(config,tag("includes"))
    ET.SubElement(includes,tag("include")).text="**/"+"$"+"{sp2027.test.class}.java"
    tree.write(pom,encoding="utf-8",xml_declaration=True)
    tests=sorted(f for f in (root/"src/test/java").rglob("*Test.java")
                 if not f.stem.startswith(("Abstract","Base")) and len(f.stem)>4)
    r["available_concrete_test_classes"]=len(tests);save()
    if not tests:raise RuntimeError("no eligible concrete original JUnit test classes")
    common=["mvn","-B","-ntp","-Drat.skip=true","-Dcheckstyle.skip=true","-DskipITs=true","-Psp2027-ekstazi"]
    def outcomes(log):
        matches=re.findall(r"Tests run:\s*(\d+),\s*Failures:\s*(\d+),\s*Errors:\s*(\d+),\s*Skipped:\s*(\d+)",log)
        return [{"run":int(a),"failed":int(b),"errors":int(c),"skipped":int(d)} for a,b,c,d in matches]
    selected=None;baseline_count=0
    for i,f in enumerate(tests[:8]):
        code,log=cmd("native_baseline_"+str(i),common+["-Dsp2027.test.class="+f.stem,"test"],timeout=215)
        stats=outcomes(log)
        executed=max((q["run"]-q["skipped"] for q in stats),default=0)
        r["native_baseline_"+str(i)]["test_summary"]=stats[-5:]
        r["native_baseline_"+str(i)]["non_skipped_executed"]=executed
        save()
        if code==0 and executed>=1 and all(q["failed"]==0 and q["errors"]==0 for q in stats):
            selected=f.stem;baseline_count=executed;break
    r["selected_class"]=selected;r["baseline_non_skipped_executed"]=baseline_count
    r["selection_scope"]="Surefire includes class name; no -Dtest override"
    save()
    if not selected:raise RuntimeError("no nonzero passing native baseline among first 8 eligible concrete JUnit classes")
    code,log=cmd("native_nochange",common+["-Dsp2027.test.class="+selected,"test"],timeout=215)
    nochange=outcomes(log)
    r["nochange_returncode"]=code
    r["nochange_summary"]=nochange[-5:]
    r["nochange_non_skipped_executed"]=max((q["run"]-q["skipped"] for q in nochange),default=0)
    r["selector_nochange_selects_zero"]=code==0 and r["nochange_non_skipped_executed"]==0
    r["status"]="verified_nonzero_baseline_nochange_measured" if code==0 else "nochange_failed"
    save()
try:
    save()
    if root.exists():raise RuntimeError("output already has checkout")
    if cmd("clone",["git","clone","--no-checkout","--depth","1","https://github.com/"+a.repo+".git",str(root)],cwd=o,timeout=120)[0]:raise RuntimeError("clone failed")
    if cmd("fetch_sha",["git","fetch","--depth","1","origin",a.sha],timeout=120)[0]:raise RuntimeError("pinned SHA fetch failed")
    if cmd("checkout",["git","checkout","--detach",a.sha],timeout=90)[0]:raise RuntimeError("pinned SHA checkout failed")
    sha=subprocess.check_output(["git","rev-parse","HEAD"],cwd=root,text=True).strip()
    if sha!=a.sha:raise RuntimeError("upstream SHA mismatch")
    r["verified_sha"]=sha;save()
    if a.lang=="python":py()
    else:java()
except Exception as e:
    r["status"]="blocked_or_failed";r["error"]=str(e)
    (logs/"exception.txt").write_text(traceback.format_exc())
finally:
    save();print("PILOT_RESULT",json.dumps({k:r.get(k) for k in ("name","status","error","selected_nodeid","selected_class","nochange_returncode")}),flush=True)
