import pathlib, subprocess, json, datetime, hashlib, shutil
BASE=pathlib.Path(__file__).resolve().parent
PLAN=json.loads((BASE/"FROZEN_PROVISIONING_PLAN.json").read_text())
PROV="sp2027-wxyc-backend-provision-20261112"
OFF="sp2027-wxyc-backend-offline-rebuild-20261112"
STAGED="sp2027-wxyc-backend-staged:20261112"
OUTPUT=PLAN["output_tag"]
BOUNDS=PLAN["bounds"]
APPENV=PLAN["app_environment"]
TOOLCHAIN="set -eu\nmkdir -p /tmp/wxyc-apt-archives/partial\napt-get -o APT::Sandbox::User=root update\nDEBIAN_FRONTEND=noninteractive apt-get -o APT::Sandbox::User=root -o Dir::Cache::archives=/tmp/wxyc-apt-archives install -y --no-install-recommends git build-essential python3 ca-certificates\nnode --version\nnpm --version\ngit --version\npython3 --version\ng++ --version\ndpkg-query -W\n"
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(name,obj):(BASE/name).write_text(json.dumps(obj,indent=2)+"\n")
if (BASE/"FROZEN_ADMIN_REPAIR_PLAN.json").exists():raise SystemExit("Repair already frozen; refuse rerun")
for name in ["PROVISIONING_RESULT.json","COMMAND_RECEIPTS.json","SHA256_MANIFEST.json"]:
    shutil.copyfile(BASE/name,BASE/("ATTEMPT1_"+name))
repair={"frozen_utc":utc(),"reason":"Original APT archive partial directory is owned by _apt with mode700; capability-dropped root cannot write it. Failed before npm/source transfer.","administrative_change_only":"Use fresh root-owned /tmp/wxyc-apt-archives cache; keep caps ALL dropped, exact base/runtime/source and application lock unchanged.","toolchain_script":TOOLCHAIN,"prior_failure":"PROVISIONING_RESULT.json and ATTEMPT1_PROVISIONING_RESULT.json; no subject execution","baseline_command_plan_unchanged_except_apt_cache":True,"no_dependencies_changed":True,"no_study_tests_or_candidates":True}
save("FROZEN_ADMIN_REPAIR_PLAN.json",repair)
(BASE/"toolchain-repair.sh").write_text(TOOLCHAIN,newline="\n")
receipts=json.loads((BASE/"COMMAND_RECEIPTS.json").read_text())
def cmd(label,args,timeout=120,fail=True,input_data=None):
    start=utc()
    try:r=subprocess.run(args,input=input_data,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout);code,out=r.returncode,r.stdout
    except subprocess.TimeoutExpired as e:code,out=124,(e.stdout or b"")+b"\nOBSERVER_TIMEOUT\n"
    (BASE/(label+".log")).write_bytes(out)
    receipts.append({"label":label,"args":args,"started_utc":start,"ended_utc":utc(),"exit_code":code,"output_bytes":len(out),"output_sha256":hashlib.sha256(out).hexdigest()})
    save("COMMAND_RECEIPTS.json",receipts)
    print(json.dumps({"stage":label,"exit_code":code,"bytes":len(out)}),flush=True)
    if code and fail:raise RuntimeError(label+" exit"+str(code))
    return code,out
result={"started_utc":utc(),"seed_eligible":False,"tests_executed":False,"candidate_executed":False,"prior_provisioning_failure_retained":True,"administrative_repair":"APT cache ownership only; app inputs unchanged"}
try:
    cmd("repair-01-start-provision",["docker","start",PROV])
    cmd("repair-02-copy-toolchain-script",["docker","cp",str(BASE/"toolchain-repair.sh"),PROV+":/tmp/toolchain-repair.sh"])
    cmd("repair-03-toolchain-inspect",["docker","inspect",PROV])
    cmd("repair-04-install-trusted-toolchain",["docker","exec",PROV,"sh","/tmp/toolchain-repair.sh"],timeout=900)
    data=(BASE/"baseline-source-and-git-uid10001.tar").read_bytes()
    cmd("repair-05-transfer-source-and-exact-package",["docker","cp","--archive","-",PROV+":/"],input_data=data)
    cmd("repair-06-original-locked-npm-ci",["docker","exec","--user","10001:10001",*APPENV,PROV,"sh","/opt/replay/provenance/install.sh"],timeout=900)
    cmd("repair-07-commit-installed-state",["docker","commit","--change","USER 10001:10001","--change","ENV HOME=/home/replay NPM_TOKEN=","--change","WORKDIR /opt/replay/seed",PROV,STAGED])
    cmd("repair-08-stop-provision",["docker","stop","--time","1",PROV])
    cmd("repair-09-create-offline-rebuild",["docker","create","--name",OFF,"--network","none","--user","10001:10001",*BOUNDS,"--env","HOME=/home/replay","--env","NPM_TOKEN=",STAGED,"sleep","infinity"])
    cmd("repair-10-start-offline-rebuild",["docker","start",OFF])
    cmd("repair-11-offline-rebuild-inspect",["docker","inspect",OFF])
    cmd("repair-12-original-offline-npm-rebuild-and-observer",["docker","exec",OFF,"sh","/opt/replay/provenance/offline-rebuild.sh"],timeout=900)
    for label,src,dst in [("repair-13-copy-installed-manifest","/opt/replay/seed-installed-manifest.json","seed-installed-manifest.json"),("repair-14-copy-seed-provenance","/opt/replay/seed-provenance.json","seed-provenance.json")]:
        cmd(label,["docker","cp",OFF+":"+src,str(BASE/dst)])
    audit=json.loads((BASE/"seed-provenance.json").read_text())
    if not audit["eligible_seed"]:raise RuntimeError("Seed observer reports ineligible")
    cmd("repair-15-commit-final-seed",["docker","commit","--change","USER 10001:10001","--change","ENV HOME=/home/replay NPM_TOKEN=","--change","WORKDIR /opt/replay/seed",OFF,OUTPUT])
    _,out=cmd("repair-16-final-seed-image-inspect",["docker","image","inspect",OUTPUT])
    result.update({"seed_eligible":True,"image":OUTPUT,"image_id":json.loads(out)[0]["Id"],"installed_manifest_sha256":audit["installed_manifest_sha256"],"baseline_all_tracked_bytes_unchanged":audit["all_baseline_tracked_bytes_unchanged"],"shared_all_members_match":audit["all_exact_shared_members_match"],"installed_manifest_path":"/opt/replay/seed-installed-manifest.json","seed_root":"/opt/replay/seed","runtime_user":"10001:10001"})
except Exception as e:result["failure"]=str(e)
finally:
    for name in [PROV,OFF]:cmd("repair-final-stop-"+name,["docker","stop","--time","1",name],fail=False)
    result["ended_utc"]=utc();save("ADMIN_REPAIR_PROVISIONING_RESULT.json",result)
    manifest=[]
    for f in sorted(BASE.rglob("*")):
        if f.is_file() and f.name!="SHA256_MANIFEST.json":
            b=f.read_bytes();manifest.append({"path":f.relative_to(BASE).as_posix(),"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest()})
    save("SHA256_MANIFEST.json",manifest)
    print(json.dumps(result),flush=True)

