import base64, datetime, hashlib, json, pathlib, subprocess, tarfile, time, urllib.request, shutil, sys

BASE = pathlib.Path(__file__).resolve().parent
BASE.mkdir(parents=True, exist_ok=True)
COMMIT = "e9374c62f32c9fd4ccccd23651babb7a556fa210"
IMAGE = "node@sha256:a9f5f7c91a432850b2a8a7797adf5eadb6c733ceed61167806cee7ea7fbc29df"
EXPECTED = "sha512-Onouu4bGBL9sVVLIhzLy72+jDg/JBTkNH88XF+4x5A101eq747vmyD/nfXNo1Q21SciMc+KTWWP/QFmtN/6WRA=="
EXPECTED_SHA1 = "cd129532df5782044467db10c8dd0e91648b0547"
PROVISION = "sp2027-wxyc-shared-one-rebuild-provision-20261112"
OFFLINE = "sp2027-wxyc-shared-one-rebuild-offline-20261112"
PREPARED = "sp2027-wxyc-shared-exact-provisioned:20261112"
WORK = "/home/node/work/wxyc-shared"
PUBLIC_URL = "https://codeload.github.com/WXYC/wxyc-shared/tar.gz/" + COMMIT
PROVISION_SCRIPT = "set -eu\nmkdir -p " + WORK + "\ntar -xzf /tmp/source.tar.gz --strip-components=1 --no-same-owner -C " + WORK + "\ncd " + WORK + "\nnode --version\nnpm --version\nnpm ci --ignore-scripts --no-audit --no-fund\n"
BUILD_SCRIPT = "set -eu\ncd " + WORK + "\nnode --version\nnpm --version\nnpm run generate:typescript\nnpm run build\nnpm pack --json\n"
BOUNDS = ["--user", "1000:1000", "--cap-drop", "ALL", "--security-opt", "no-new-privileges:true", "--pids-limit", "256", "--memory", "4g", "--cpus", "2", "--env", "HOME=/home/node", "--workdir", "/home/node", "--label", "sp2027.package-rebuild=one-frozen-attempt"]

def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def save(name, obj):
    (BASE / name).write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")

receipts = []
def command(label, args, timeout=120, allow_failure=False):
    start = utc()
    try:
        r = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
        code, out = r.returncode, r.stdout
    except subprocess.TimeoutExpired as e:
        code, out = 124, (e.stdout or b"") + b"\nHOST_OBSERVER_TIMEOUT\n"
    (BASE / (label + ".log")).write_bytes(out)
    row = {"label":label, "args":args, "started_utc":start, "ended_utc":utc(), "exit_code":code, "output_sha256":hashlib.sha256(out).hexdigest(), "output_bytes":len(out)}
    receipts.append(row)
    save("COMMAND_RECEIPTS.json", receipts)
    print(json.dumps({"stage":label,"exit_code":code,"bytes":len(out)}), flush=True)
    if code and not allow_failure:
        raise RuntimeError(label + " failed with exit code " + str(code))
    return code, out

if (BASE / "FROZEN_BUILD_PLAN.json").exists():
    raise SystemExit("Frozen attempt already exists; refusal to rerun.")

plan = {"frozen_utc":utc(), "one_attempt_only":True, "source_url":PUBLIC_URL, "source_commit":COMMIT, "source_tag":"v4.1.0", "runtime_image":IMAGE, "node":"24.19.0", "npm":"11.17.0", "expected_full_integrity":EXPECTED, "expected_sha1":EXPECTED_SHA1, "provision_network":"bridge; public resolved npm registry data only; no lifecycle scripts", "build_network":"none", "container_arguments":BOUNDS, "host_mounts":False, "docker_socket":False, "ports":False, "credentials_injected":False, "provision_script":PROVISION_SCRIPT, "offline_build_script":BUILD_SCRIPT, "acceptance":"Use archive only if complete SHA512 equals unchanged backend lock integrity. Any failure/mismatch ends attempt without variants.", "source_lock_scripts_config_unchanged":True, "upstream_tests_run":False}
save("FROZEN_BUILD_PLAN.json", plan)
(BASE / "provision.sh").write_text(PROVISION_SCRIPT, encoding="utf-8", newline="\n")
(BASE / "offline-build.sh").write_text(BUILD_SCRIPT, encoding="utf-8", newline="\n")
result = {"started_utc":utc(), "complete_sha512_match":False, "usable_for_original_dependency":False, "attempt_count":1}
try:
    with urllib.request.urlopen(PUBLIC_URL, timeout=90) as response:
        data = response.read()
        save("SOURCE_DOWNLOAD_RECEIPT.json", {"url":PUBLIC_URL,"final_url":response.url,"status":response.status,"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest(),"retrieved_utc":utc()})
    archive = BASE / "source-e9374c62.tar.gz"
    archive.write_bytes(data)
    source_manifest=[]
    with tarfile.open(archive, "r:gz") as tf:
        for m in tf.getmembers():
            p = pathlib.PurePosixPath(m.name)
            if p.is_absolute() or ".." in p.parts:
                raise RuntimeError("Unsafe archive member path")
            if m.issym() or m.islnk():
                raise RuntimeError("Unexpected source archive link")
            if m.isfile():
                b=tf.extractfile(m).read()
                source_manifest.append({"path":"/".join(p.parts[1:]),"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest(),"git_blob_sha1":hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()})
    save("SOURCE_FILE_MANIFEST.json",source_manifest)
    expected_blobs={"package.json":"6fba109a699405cd927abfe58f59ec56ac39f619","package-lock.json":"caf153200ad1eea9695a12b3d2f76e76abe690cd"}
    observed={r["path"]:r["git_blob_sha1"] for r in source_manifest}
    if any(observed.get(p)!=sha for p,sha in expected_blobs.items()):
        raise RuntimeError("Source archive mismatch against independently fetched immutable Git blobs")
    command("00-image-inspect", ["docker","image","inspect",IMAGE])
    command("01-create-provision",["docker","create","--name",PROVISION,"--network","bridge",*BOUNDS,IMAGE,"sleep","infinity"])
    command("02-start-provision",["docker","start",PROVISION])
    command("03-copy-source",["docker","cp",str(archive),PROVISION+":/tmp/source.tar.gz"])
    command("04-copy-provision-script",["docker","cp",str(BASE/"provision.sh"),PROVISION+":/tmp/provision.sh"])
    command("05-provision-inspect",["docker","inspect",PROVISION])
    command("06-provision-public-data-only",["docker","exec",PROVISION,"sh","/tmp/provision.sh"],timeout=900)
    command("07-commit-provisioned",["docker","commit",PROVISION,PREPARED])
    command("08-prepared-image-inspect",["docker","image","inspect",PREPARED])
    command("09-stop-provision",["docker","stop","--time","1",PROVISION])
    command("10-create-offline",["docker","create","--name",OFFLINE,"--network","none",*BOUNDS,PREPARED,"sleep","infinity"])
    command("11-start-offline",["docker","start",OFFLINE])
    command("12-copy-offline-script",["docker","cp",str(BASE/"offline-build.sh"),OFFLINE+":/tmp/offline-build.sh"])
    command("13-offline-inspect",["docker","inspect",OFFLINE])
    command("14-offline-original-build-and-pack",["docker","exec",OFFLINE,"sh","/tmp/offline-build.sh"],timeout=900)
    command("15-copy-built-archive",["docker","cp",OFFLINE+":"+WORK+"/wxyc-shared-4.1.0.tgz",str(BASE/"wxyc-shared-4.1.0.tgz")])
    command("16-copy-built-package-json",["docker","cp",OFFLINE+":"+WORK+"/package.json",str(BASE/"post-build-package.json")])
    command("17-copy-built-lockfile",["docker","cp",OFFLINE+":"+WORK+"/package-lock.json",str(BASE/"post-build-package-lock.json")])
    built=(BASE/"wxyc-shared-4.1.0.tgz").read_bytes()
    integrity="sha512-"+base64.b64encode(hashlib.sha512(built).digest()).decode()
    sha1=hashlib.sha1(built).hexdigest()
    package_members=[]
    with tarfile.open(BASE/"wxyc-shared-4.1.0.tgz","r:gz") as tf:
        for m in tf.getmembers():
            if m.isfile():
                b=tf.extractfile(m).read()
                package_members.append({"path":m.name,"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest()})
    save("BUILT_PACKAGE_FILE_MANIFEST.json", package_members)
    unchanged={}
    for path, output in [("package.json","post-build-package.json"),("package-lock.json","post-build-package-lock.json")]:
        b=(BASE/output).read_bytes()
        unchanged[path]=hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()==expected_blobs[path]
    result.update({"build_succeeded":True,"archive_bytes":len(built),"archive_sha256":hashlib.sha256(built).hexdigest(),"archive_sha1":sha1,"archive_full_integrity":integrity,"expected_full_integrity":EXPECTED,"complete_sha512_match":integrity==EXPECTED,"sha1_match":sha1==EXPECTED_SHA1,"original_files_unchanged":unchanged,"package_file_count":len(package_members),"usable_for_original_dependency":integrity==EXPECTED and all(unchanged.values())})
except Exception as e:
    result.update({"build_succeeded":False,"failure":str(e)})
finally:
    for container in [PROVISION,OFFLINE]:
        command("final-stop-"+container,["docker","stop","--time","1",container],allow_failure=True)
    result["ended_utc"]=utc()
    save("REBUILD_RESULT.json",result)
    rows=[]
    for f in sorted(BASE.rglob("*")):
        if f.is_file() and f.name!="SHA256_MANIFEST.json":
            b=f.read_bytes()
            rows.append({"path":f.relative_to(BASE).as_posix(),"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest()})
    save("SHA256_MANIFEST.json",rows)
    print(json.dumps(result),flush=True)

