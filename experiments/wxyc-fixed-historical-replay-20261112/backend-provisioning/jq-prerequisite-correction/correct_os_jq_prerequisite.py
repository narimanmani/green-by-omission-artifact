import pathlib,subprocess,json,datetime,hashlib,re
BASE=pathlib.Path(__file__).resolve().parent
BASE.mkdir(parents=True,exist_ok=True)
SOURCE="sha256:56559845a6388a7f0141ceea11a76684615db3aa0d34e1f9521686bb508d53e5"
OUTPUT="sp2027-wxyc-replay-seed-jq:20261112"
PROV="sp2027-wxyc-jq-os-provision-20261112"
CHECK="sp2027-wxyc-jq-offline-verification-20261112"
STAGED="sp2027-wxyc-jq-staged:20261112"
EXPECTED_MANIFEST="0f518c86e2911fb9a6911bb8331fa58e1250c3bdcfcea035285b02c99517f280"
BOUNDS=["--cap-drop","ALL","--security-opt","no-new-privileges:true","--pids-limit","512","--memory","6g","--cpus","2","--label","sp2027.prerequisite-correction=jq-os-only"]
PKG_FORMAT=chr(36)+"{Package}\\t"+chr(36)+"{Version}\\n"
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(n,o):(BASE/n).write_text(json.dumps(o,indent=2)+"\n")
receipts=json.loads((BASE/"COMMAND_RECEIPTS.json").read_text()) if (BASE/"COMMAND_RECEIPTS.json").exists() else []
def cmd(label,args,timeout=120,fail=True):
 start=utc()
 try:r=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout);code,out=r.returncode,r.stdout
 except subprocess.TimeoutExpired as e:code,out=124,(e.stdout or b"")+b"\nOBSERVER_TIMEOUT\n"
 (BASE/(label+".log")).write_bytes(out)
 receipts.append({"label":label,"args":args,"started_utc":start,"ended_utc":utc(),"exit_code":code,"output_bytes":len(out),"output_sha256":hashlib.sha256(out).hexdigest()});save("COMMAND_RECEIPTS.json",receipts)
 print(json.dumps({"stage":label,"exit_code":code,"bytes":len(out)}),flush=True)
 if code and fail:raise RuntimeError(label+" exit"+str(code))
 return code,out
if (BASE/"FROZEN_JQ_CORRECTION_PLAN.json").exists():raise SystemExit("Correction already frozen; refuse rerun")
diag=r'''import pathlib,shutil,hashlib,json,subprocess
p=pathlib.Path("/opt/replay/seed/scripts/resolve-cron-schedule.sh")
pol=subprocess.run(["apt-cache","policy","jq","libjq1","libonig5"],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
print(json.dumps({"jq_path":shutil.which("jq"),"bash_path":shutil.which("bash"),"unchanged_resolver_sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"resolver_jq_lines":[{"line":i+1,"text":s} for i,s in enumerate(p.read_text().splitlines()) if "jq" in s],"policy_stdout":pol.stdout,"policy_stderr":pol.stderr,"policy_exit":pol.returncode,"subject_code_executed":False}))
'''
_,out=cmd("01b-readonly-missing-tool-diagnosis-private-scratch",["docker","run","--name","sp2027-wxyc-jq-readonly-diagnosis-v2-20261112","--network","none","--read-only","--tmpfs","/tmp:rw,nosuid,nodev,noexec,size=16m,mode=1777","--user","10001:10001",*BOUNDS,SOURCE,"python3","-c",diag])
d=json.loads(out)
if d["jq_path"] is not None:raise SystemExit("jq already present; no correction authorized by this diagnosis")
match=re.search(r"(?ms)^jq:\n.*?Candidate:\s*(\S+)",d["policy_stdout"])
if not match or match.group(1)=="(none)":raise SystemExit("No frozen jq candidate in official original APT index")
version=match.group(1)
_,existing=cmd("02-output-collision-check",["docker","image","inspect",OUTPUT],fail=False)
if not b"No such image" in existing:raise SystemExit("Output tag exists or unexpected collision response")
INSTALL="set -eu\nmkdir -p /tmp/wxyc-apt-archives/partial\nDEBIAN_FRONTEND=noninteractive apt-get -o APT::Sandbox::User=root -o Dir::Cache::archives=/tmp/wxyc-apt-archives install -y --no-install-recommends jq="+version+"\n"
save("FROZEN_JQ_CORRECTION_PLAN.json",{"frozen_utc":utc(),"source_image":SOURCE,"output_tag":OUTPUT,"diagnosis":d,"jq_version_from_original_official_index":version,"install_script":INSTALL,"root_user_only_trusted_os_package_install":True,"runtime_and_verification_user":"10001:10001","bounds":BOUNDS,"no_source_node_package_test_config_lock_changes":True,"no_jest_tests_candidates":True,"old_seed_and_v1_outcomes_retained":True,"expected_old_and_new_dependency_manifest_sha256":EXPECTED_MANIFEST,"acceptance":"Only jq/libjq1/libonig5 newly installed; no preexisting OS package version changed; every original source and dependency byte/symlink and Git identity unchanged."})
(BASE/"install-jq.sh").write_text(INSTALL,newline="\n")
verify=r'''import pathlib,json,hashlib,os,subprocess
p=pathlib.Path("/opt/replay/seed")
mp=pathlib.Path("/opt/replay/seed-installed-manifest.json")
assert hashlib.sha256(mp.read_bytes()).hexdigest()=="0f518c86e2911fb9a6911bb8331fa58e1250c3bdcfcea035285b02c99517f280"
m=json.loads(mp.read_text())
bad=[]
for e in m["entries"]:
 f=p/e["path"]
 if e["type"]=="symlink":
  if not f.is_symlink() or os.readlink(f)!=e["target"]:bad.append(e["path"])
 else:
  if not f.is_file() or hashlib.sha256(f.read_bytes()).hexdigest()!=e["sha256"]:bad.append(e["path"])
assert not bad, str(bad[:10])
r=subprocess.run(["python3","/opt/replay/provenance/verify_seed.py"],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
print(r.stdout,end="");print(r.stderr,end="")
assert r.returncode==0
assert hashlib.sha256(mp.read_bytes()).hexdigest()=="0f518c86e2911fb9a6911bb8331fa58e1250c3bdcfcea035285b02c99517f280"
print(json.dumps({"old_manifest_all_entries_reverified":len(m["entries"]),"old_new_manifest_identical":True,"jq_version":subprocess.check_output(["jq","--version"],text=True).strip(),"subject_code_executed":False}))
'''
(BASE/"verify-jq-seed.py").write_text(verify,newline="\n")
osmeta=r'''import pathlib,subprocess,json,hashlib
rows=[]
for n in ["jq","libjq1","libonig5"]:
 v=subprocess.check_output(["dpkg-query","-W","-f="+chr(36)+"{Version}",n],text=True).strip()
 show=subprocess.check_output(["apt-cache","show",n+"="+v],text=True)
 fields={}
 for line in show.splitlines():
  if ": " in line:
   k,value=line.split(": ",1)
   if k in ["Package","Version","Filename","SHA256","Size"]:fields[k]=value
 matches=[]
 for f in pathlib.Path("/tmp/wxyc-apt-archives").glob(n+"_*.deb"):
  b=f.read_bytes();matches.append({"file":str(f),"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest(),"matches_official_index":hashlib.sha256(b).hexdigest()==fields.get("SHA256")})
 rows.append({"package":n,"installed_version":v,"official_apt_index":fields,"archive_receipts":matches})
print(json.dumps(rows))
'''
result={"started_utc":utc(),"seed_eligible":False,"tests_executed":False,"candidate_executed":False,"old_seed_preserved":True}
try:
 cmd("03-create-os-provision",["docker","create","--name",PROV,"--network","bridge","--user","0:0",*BOUNDS,SOURCE,"sleep","infinity"])
 cmd("04-start-os-provision",["docker","start",PROV])
 cmd("05-os-provision-inspect",["docker","inspect",PROV])
 _,before=cmd("06-before-os-packages",["docker","exec",PROV,"dpkg-query","-W","-f="+PKG_FORMAT])
 cmd("07-copy-jq-install-script",["docker","cp",str(BASE/"install-jq.sh"),PROV+":/tmp/install-jq.sh"])
 cmd("08-official-jq-install-only",["docker","exec",PROV,"sh","/tmp/install-jq.sh"],timeout=300)
 _,after=cmd("09-after-os-packages",["docker","exec",PROV,"dpkg-query","-W","-f="+PKG_FORMAT])
 def packages(b):return dict(x.split("\t",1) for x in b.decode().splitlines() if "\t" in x)
 a,b=packages(before),packages(after)
 new={k:v for k,v in b.items() if k not in a}
 changed={k:{"before":v,"after":b.get(k)} for k,v in a.items() if b.get(k)!=v}
 if set(new)!={"jq","libjq1","libonig5"} or changed:raise RuntimeError("OS delta exceeds minimal jq dependencies: "+str((new,changed)))
 _,metadata=cmd("10-jq-official-version-and-deb-checksums",["docker","exec",PROV,"python3","-c",osmeta])
 osrows=json.loads(metadata)
 if not all(x["archive_receipts"] and all(z["matches_official_index"] for z in x["archive_receipts"]) for x in osrows):raise RuntimeError("Official jq/dependency archive checksums not all verified")
 save("OS_PACKAGE_DELTA.json",{"new":new,"changed_existing":changed,"official_archives":osrows})
 cmd("11-commit-os-corrected-staged",["docker","commit","--change","USER 10001:10001","--change","ENV HOME=/home/replay NPM_TOKEN=","--change","WORKDIR /opt/replay/seed",PROV,STAGED])
 cmd("12-stop-os-provision",["docker","stop","--time","1",PROV])
 cmd("13-create-offline-verifier",["docker","create","--name",CHECK,"--network","none","--user","10001:10001",*BOUNDS,"--env","HOME=/home/replay","--env","NPM_TOKEN=",STAGED,"sleep","infinity"])
 cmd("14-start-offline-verifier",["docker","start",CHECK])
 cmd("15-offline-verifier-inspect",["docker","inspect",CHECK])
 cmd("16-copy-readonly-observer",["docker","cp",str(BASE/"verify-jq-seed.py"),CHECK+":/tmp/verify-jq-seed.py"])
 cmd("17-all-original-source-and-installed-bytes-verification",["docker","exec",CHECK,"python3","/tmp/verify-jq-seed.py"],timeout=300)
 for label,src,dst in [("18-copy-new-provenance","/opt/replay/seed-provenance.json","seed-provenance.json"),("19-copy-identical-installed-manifest","/opt/replay/seed-installed-manifest.json","seed-installed-manifest.json")]:
  cmd(label,["docker","cp",CHECK+":"+src,str(BASE/dst)])
 cmd("20-commit-new-seed-tag",["docker","commit","--change","USER 10001:10001","--change","ENV HOME=/home/replay NPM_TOKEN=","--change","WORKDIR /opt/replay/seed",CHECK,OUTPUT])
 _,out=cmd("21-new-seed-image-inspect",["docker","image","inspect",OUTPUT])
 result.update({"seed_eligible":True,"image":OUTPUT,"image_id":json.loads(out)[0]["Id"],"installed_manifest_sha256":EXPECTED_MANIFEST,"original_source_files":1869,"installed_manifest_entries":49661,"new_os_packages":new,"existing_os_packages_changed":changed})
except Exception as e:result["failure"]=str(e)
finally:
 for c in [PROV,CHECK]:cmd("final-stop-"+c,["docker","stop","--time","1",c],fail=False)
 result["ended_utc"]=utc();save("JQ_CORRECTION_RESULT.json",result)
 rows=[]
 for f in sorted(BASE.rglob("*")):
  if f.is_file() and f.name!="SHA256_MANIFEST.json":
   data=f.read_bytes();rows.append({"path":f.relative_to(BASE).as_posix(),"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest()})
 save("SHA256_MANIFEST.json",rows)
 print(json.dumps(result),flush=True)

