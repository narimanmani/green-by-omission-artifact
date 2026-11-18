import pathlib,subprocess,json,datetime,hashlib,shutil
BASE=pathlib.Path(__file__).resolve().parent
P=json.loads((BASE/"FROZEN_PROVISIONING_PLAN.json").read_text())
SOURCE="sp2027-wxyc-backend-staged:20261112"
HEADERS="sp2027-wxyc-backend-header-data-20261112"
OFF="sp2027-wxyc-backend-offline-rebuild-v2-20261112"
STAGED="sp2027-wxyc-backend-headers-staged:20261112"
OUTPUT=P["output_tag"]
HEADER_CMD=["node","/usr/local/lib/node_modules/npm/node_modules/node-gyp/bin/node-gyp.js","install","--ensure","--target=24.19.0","--verbose"]
BOUNDS=P["bounds"]
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(n,o):(BASE/n).write_text(json.dumps(o,indent=2)+"\n")
if (BASE/"FROZEN_HEADER_PREFILL_PLAN.json").exists():raise SystemExit("Header repair already frozen")
shutil.copyfile(BASE/"COMMAND_RECEIPTS.json",BASE/"PRE_HEADER_COMMAND_RECEIPTS.json")
shutil.copyfile(BASE/"SHA256_MANIFEST.json",BASE/"PRE_HEADER_SHA256_MANIFEST.json")
save("FROZEN_HEADER_PREFILL_PLAN.json",{"frozen_utc":utc(),"reason":"Original offline cpu-features node-gyp lifecycle required exact runtime Node24.19.0 headers absent from default cache.","administrative_prerequisite_only":True,"clean_pre_rebuild_image":SOURCE,"runtime":"Node24.19.0/npm11.17.0 unchanged","public_data_only_command":HEADER_CMD,"official_header_url":"https://nodejs.org/download/release/v24.19.0/node-v24.19.0-headers.tar.gz","official_checksum_url":"https://nodejs.org/download/release/v24.19.0/SHASUMS256.txt","node_gyp_validates_checksum":True,"offline_rebuild_command_unchanged":"sh /opt/replay/provenance/offline-rebuild.sh","bounds":BOUNDS,"uid":"10001:10001","no_credentials_mounts_ports_socket":True,"dependency_source_lock_config_changes":False,"tests_candidates_executed":False})
receipts=json.loads((BASE/"COMMAND_RECEIPTS.json").read_text())
def cmd(label,args,timeout=120,fail=True):
    start=utc()
    try:r=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout);code,out=r.returncode,r.stdout
    except subprocess.TimeoutExpired as e:code,out=124,(e.stdout or b"")+b"\nOBSERVER_TIMEOUT\n"
    (BASE/(label+".log")).write_bytes(out)
    receipts.append({"label":label,"args":args,"started_utc":start,"ended_utc":utc(),"exit_code":code,"output_bytes":len(out),"output_sha256":hashlib.sha256(out).hexdigest()});save("COMMAND_RECEIPTS.json",receipts)
    print(json.dumps({"stage":label,"exit_code":code,"bytes":len(out)}),flush=True)
    if code and fail:raise RuntimeError(label+" exit"+str(code))
    return code,out
result={"started_utc":utc(),"seed_eligible":False,"tests_executed":False,"candidate_executed":False,"prior_failures_retained":True,"administrative_repair":"Exact Node24.19.0 public headers prefill, identical original offline lifecycle command"}
try:
    cmd("header-01-create-public-data-prefill",["docker","create","--name",HEADERS,"--network","bridge","--user","10001:10001",*BOUNDS,"--env","HOME=/home/replay","--env","NPM_TOKEN=",SOURCE,"sleep","infinity"])
    cmd("header-02-start-public-data-prefill",["docker","start",HEADERS])
    cmd("header-03-public-data-inspect",["docker","inspect",HEADERS])
    cmd("header-04-exact-runtime-headers-public-data",["docker","exec",HEADERS,*HEADER_CMD],timeout=300)
    cmd("header-05-commit-prefilled-state",["docker","commit",HEADERS,STAGED])
    cmd("header-06-stop-header-prefill",["docker","stop","--time","1",HEADERS])
    cmd("header-07-create-clean-offline-rebuild",["docker","create","--name",OFF,"--network","none","--user","10001:10001",*BOUNDS,"--env","HOME=/home/replay","--env","NPM_TOKEN=",STAGED,"sleep","infinity"])
    cmd("header-08-start-clean-offline-rebuild",["docker","start",OFF])
    cmd("header-09-offline-inspect",["docker","inspect",OFF])
    cmd("header-10-original-offline-rebuild-and-observer",["docker","exec",OFF,"sh","/opt/replay/provenance/offline-rebuild.sh"],timeout=900)
    for label,src,dst in [("header-11-copy-manifest","/opt/replay/seed-installed-manifest.json","seed-installed-manifest.json"),("header-12-copy-provenance","/opt/replay/seed-provenance.json","seed-provenance.json")]:
        cmd(label,["docker","cp",OFF+":"+src,str(BASE/dst)])
    audit=json.loads((BASE/"seed-provenance.json").read_text())
    if not audit["eligible_seed"]:raise RuntimeError("Seed observer ineligible")
    cmd("header-13-commit-final-seed",["docker","commit","--change","USER 10001:10001","--change","ENV HOME=/home/replay NPM_TOKEN=","--change","WORKDIR /opt/replay/seed",OFF,OUTPUT])
    _,out=cmd("header-14-final-image-inspect",["docker","image","inspect",OUTPUT])
    result.update({"seed_eligible":True,"image":OUTPUT,"image_id":json.loads(out)[0]["Id"],"installed_manifest_sha256":audit["installed_manifest_sha256"],"baseline_all_tracked_bytes_unchanged":audit["all_baseline_tracked_bytes_unchanged"],"shared_all_members_match":audit["all_exact_shared_members_match"],"installed_manifest_path":"/opt/replay/seed-installed-manifest.json","seed_root":"/opt/replay/seed","runtime_user":"10001:10001"})
except Exception as e:result["failure"]=str(e)
finally:
    for c in [HEADERS,OFF]:cmd("header-final-stop-"+c,["docker","stop","--time","1",c],fail=False)
    result["ended_utc"]=utc();save("HEADER_REPAIR_PROVISIONING_RESULT.json",result)
    rows=[]
    for f in sorted(BASE.rglob("*")):
        if f.is_file() and f.name!="SHA256_MANIFEST.json":
            b=f.read_bytes();rows.append({"path":f.relative_to(BASE).as_posix(),"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest()})
    save("SHA256_MANIFEST.json",rows)
    print(json.dumps(result),flush=True)

