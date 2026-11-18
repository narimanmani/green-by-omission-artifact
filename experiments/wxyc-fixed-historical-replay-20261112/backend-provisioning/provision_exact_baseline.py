import pathlib, subprocess, json, datetime, hashlib, tarfile, io, os, base64
BASE=pathlib.Path(__file__).resolve().parent
STUDY=BASE.parent
SRC=STUDY/"input/upstream"
COMMIT="b86530c6c656b7a8f72d42145e9d46995c7ab53d"
IMAGE="node@sha256:a9f5f7c91a432850b2a8a7797adf5eadb6c733ceed61167806cee7ea7fbc29df"
PROV="sp2027-wxyc-backend-provision-20261112"
OFF="sp2027-wxyc-backend-offline-rebuild-20261112"
STAGED="sp2027-wxyc-backend-staged:20261112"
OUTPUT="sp2027-wxyc-replay-seed:20261112"
BOUNDS=["--cap-drop","ALL","--security-opt","no-new-privileges:true","--pids-limit","512","--memory","6g","--cpus","2","--label","sp2027.backend-provisioning=baseline-only-no-tests"]
APPENV=["--env","HOME=/home/replay","--env","NPM_TOKEN=","--env","GIT_CONFIG_COUNT=2","--env","GIT_CONFIG_KEY_0=url.https://github.com/.insteadOf","--env","GIT_CONFIG_VALUE_0=ssh://git@github.com/","--env","GIT_CONFIG_KEY_1=url.https://github.com/.insteadOf","--env","GIT_CONFIG_VALUE_1=git@github.com:"]
TOOLCHAIN="set -eu\napt-get -o APT::Sandbox::User=root update\nDEBIAN_FRONTEND=noninteractive apt-get -o APT::Sandbox::User=root install -y --no-install-recommends git build-essential python3 ca-certificates\nnode --version\nnpm --version\ngit --version\npython3 --version\ng++ --version\ndpkg-query -W\n"
INSTALL="set -eu\ncd /opt/replay/seed\nnode --version\nnpm --version\ngit rev-parse HEAD\ngit rev-parse origin/main\nnpm cache add /opt/replay/provenance/wxyc-shared-4.1.0.tgz --ignore-scripts --no-audit --no-fund\nnpm ci --ignore-scripts --prefer-offline --no-audit --no-fund\n"
REBUILD="set -eu\ncd /opt/replay/seed\nnode --version\nnpm --version\nnpm rebuild --offline --no-audit --no-fund\npython3 /opt/replay/provenance/verify_seed.py\n"
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(name,obj):(BASE/name).write_text(json.dumps(obj,indent=2)+"\n",encoding="utf-8")
receipts=[]
def cmd(label,args,timeout=120,fail=True,input_data=None):
    start=utc()
    try:
        r=subprocess.run(args,input=input_data,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
        code,out=r.returncode,r.stdout
    except subprocess.TimeoutExpired as e:code,out=124,(e.stdout or b"")+b"\nOBSERVER_TIMEOUT\n"
    (BASE/(label+".log")).write_bytes(out)
    receipts.append({"label":label,"args":args,"started_utc":start,"ended_utc":utc(),"exit_code":code,"output_bytes":len(out),"output_sha256":hashlib.sha256(out).hexdigest()})
    save("COMMAND_RECEIPTS.json",receipts)
    print(json.dumps({"stage":label,"exit_code":code,"bytes":len(out)}),flush=True)
    if code and fail:raise RuntimeError(label+" exit"+str(code))
    return code,out
BASE.mkdir(parents=True,exist_ok=True)
if (BASE/"FROZEN_PROVISIONING_PLAN.json").exists():raise SystemExit("Refusing to rerun frozen attempt")
code,out=cmd("00-output-tag-collision-check",["docker","image","inspect",OUTPUT],fail=False)
if not code:raise SystemExit("Output image already exists; no overwrite")
plan={"frozen_utc":utc(),"baseline":COMMIT,"input_path":str(SRC),"runtime_image":IMAGE,"node":"24.19.0","npm":"11.17.0","output_tag":OUTPUT,"provision_user":"UID0 only trusted Debian toolchain install; UID10001 all npm/source operations","offline_runtime_user":"10001:10001","bounds":BOUNDS,"app_environment":APPENV,"toolchain_script":TOOLCHAIN,"network_install_script":INSTALL,"offline_script":REBUILD,"lifecycle_policy":"npm ci ignore-scripts online, original npm rebuild offline; no tests/Jest/candidate","transport_rewrite":"SSH to HTTPS for identical original public git repo/commit only; original lock unchanged","matched_shared_integrity":"sha512-Onouu4bGBL9sVVLIhzLy72+jDg/JBTkNH88XF+4x5A101eq747vmyD/nfXNo1Q21SciMc+KTWWP/QFmtN/6WRA==","host_mounts":False,"ports":False,"docker_socket":False,"credentials_injected":False,"npm_token_empty_for_interpolation_only":True,"source_edits":False,"dependency_substitutions":False}
save("FROZEN_PROVISIONING_PLAN.json",plan)
for name,text in [("toolchain.sh",TOOLCHAIN),("install.sh",INSTALL),("offline-rebuild.sh",REBUILD)]:(BASE/name).write_text(text,newline="\n")
result={"started_utc":utc(),"seed_eligible":False,"tests_executed":False,"candidate_executed":False}
try:
    baseline=json.loads((STUDY/"input/baseline-source-manifest.json").read_text())
    for r in baseline:
        b=(SRC/r["path"]).read_bytes()
        if hashlib.sha256(b).hexdigest()!=r["sha256"]:raise RuntimeError("Host baseline mismatch "+r["path"])
    config=(SRC/".git/config").read_text()
    forbidden=["https://git@","@github.com:"]
    if "credential" in config.lower() or "https://" in config and "https://github.com/WXYC/Backend-Service" not in config:
        raise RuntimeError("Unapproved project Git config; not copied")
    archive=BASE/"baseline-source-and-git-uid10001.tar"
    with tarfile.open(archive,"w") as tf:
        def add(path,b,mode=0o644):
            t=tarfile.TarInfo(path);t.size=len(b);t.mode=mode;t.uid=t.gid=10001;t.mtime=0;tf.addfile(t,io.BytesIO(b))
        for directory in ["opt/replay","opt/replay/seed","opt/replay/provenance","home/replay"]:
            t=tarfile.TarInfo(directory);t.type=tarfile.DIRTYPE;t.mode=0o755;t.uid=t.gid=10001;tf.addfile(t)
        seed_dirs=set()
        for r in baseline:
            for parent in pathlib.PurePosixPath(r["path"]).parents:
                if str(parent)!=".":seed_dirs.add(parent.as_posix())
        seed_dirs.add(".git")
        for d in (SRC/".git").rglob("*"):
            if d.is_dir():seed_dirs.add(d.relative_to(SRC).as_posix())
        for directory in sorted(seed_dirs,key=lambda x:(x.count("/"),x)):
            t=tarfile.TarInfo("opt/replay/seed/"+directory);t.type=tarfile.DIRTYPE;t.mode=0o755;t.uid=t.gid=10001;tf.addfile(t)
        for r in baseline:add("opt/replay/seed/"+r["path"],(SRC/r["path"]).read_bytes(),0o755 if r["mode"]=="100755" else 0o644)
        for f in sorted((SRC/".git").rglob("*")):
            if f.is_symlink():raise RuntimeError("Unexpected project Git symlink")
            if f.is_file():add("opt/replay/seed/"+f.relative_to(SRC).as_posix(),f.read_bytes())
        for name,b in [
          ("baseline-source-manifest.json",(STUDY/"input/baseline-source-manifest.json").read_bytes()),
          ("shared-package-file-manifest.json",(STUDY/"package-rebuild/BUILT_PACKAGE_FILE_MANIFEST.json").read_bytes()),
          ("wxyc-shared-4.1.0.tgz",(STUDY/"package-rebuild/wxyc-shared-4.1.0.tgz").read_bytes()),
          ("verify_seed.py",(BASE/"verify_seed.py").read_bytes()),
          ("install.sh",INSTALL.encode()),("offline-rebuild.sh",REBUILD.encode())
        ]:add("opt/replay/provenance/"+name,b)
    data=archive.read_bytes()
    save("SOURCE_TRANSFER_RECEIPT.json",{"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest(),"tracked_files":len(baseline),"source_git_config_credential_check":"No credential stanza or authenticated remote detected; no configuration contents logged","ownership":"10001:10001","source_modes":"original Git100644/100755"})
    cmd("01-base-image-inspect",["docker","image","inspect",IMAGE])
    cmd("02-create-toolchain-provision",["docker","create","--name",PROV,"--network","bridge",*BOUNDS,IMAGE,"sleep","infinity"])
    cmd("03-start-toolchain-provision",["docker","start",PROV])
    cmd("04-copy-toolchain-script",["docker","cp",str(BASE/"toolchain.sh"),PROV+":/tmp/toolchain.sh"])
    cmd("05-toolchain-provision-inspect",["docker","inspect",PROV])
    cmd("06-install-trusted-toolchain",["docker","exec",PROV,"sh","/tmp/toolchain.sh"],timeout=900)
    cmd("07-transfer-source-and-exact-package",["docker","cp","--archive","-",PROV+":/"],input_data=data)
    cmd("08-original-locked-npm-ci",["docker","exec","--user","10001:10001",*APPENV,PROV,"sh","/opt/replay/provenance/install.sh"],timeout=900)
    cmd("09-commit-installed-state",["docker","commit","--change","USER 10001:10001","--change","ENV HOME=/home/replay NPM_TOKEN=","--change","WORKDIR /opt/replay/seed",PROV,STAGED])
    cmd("10-stop-provision",["docker","stop","--time","1",PROV])
    cmd("11-create-offline-rebuild",["docker","create","--name",OFF,"--network","none","--user","10001:10001",*BOUNDS,"--env","HOME=/home/replay","--env","NPM_TOKEN=",STAGED,"sleep","infinity"])
    cmd("12-start-offline-rebuild",["docker","start",OFF])
    cmd("13-offline-rebuild-inspect",["docker","inspect",OFF])
    cmd("14-original-offline-npm-rebuild-and-observer",["docker","exec",OFF,"sh","/opt/replay/provenance/offline-rebuild.sh"],timeout=900)
    for label,src,dst in [
      ("15-copy-installed-manifest","/opt/replay/seed-installed-manifest.json","seed-installed-manifest.json"),
      ("16-copy-seed-provenance","/opt/replay/seed-provenance.json","seed-provenance.json")
    ]:cmd(label,["docker","cp",OFF+":"+src,str(BASE/dst)])
    audit=json.loads((BASE/"seed-provenance.json").read_text())
    if not audit["eligible_seed"]:raise RuntimeError("Seed observer reports ineligible")
    cmd("17-commit-final-seed",["docker","commit","--change","USER 10001:10001","--change","ENV HOME=/home/replay NPM_TOKEN=","--change","WORKDIR /opt/replay/seed",OFF,OUTPUT])
    _,out=cmd("18-final-seed-image-inspect",["docker","image","inspect",OUTPUT])
    image_id=json.loads(out)[0]["Id"]
    result.update({"seed_eligible":True,"image":OUTPUT,"image_id":image_id,"installed_manifest_sha256":audit["installed_manifest_sha256"],"baseline_all_tracked_bytes_unchanged":audit["all_baseline_tracked_bytes_unchanged"],"shared_all_members_match":audit["all_exact_shared_members_match"],"installed_manifest_path":"/opt/replay/seed-installed-manifest.json","seed_root":"/opt/replay/seed","runtime_user":"10001:10001"})
except Exception as e:
    result["failure"]=str(e)
finally:
    for name in [PROV,OFF]:cmd("final-stop-"+name,["docker","stop","--time","1",name],fail=False)
    result["ended_utc"]=utc();save("PROVISIONING_RESULT.json",result)
    manifest=[]
    for f in sorted(BASE.rglob("*")):
        if f.is_file() and f.name!="SHA256_MANIFEST.json":
            b=f.read_bytes();manifest.append({"path":f.relative_to(BASE).as_posix(),"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest()})
    save("SHA256_MANIFEST.json",manifest)
    print(json.dumps(result),flush=True)

