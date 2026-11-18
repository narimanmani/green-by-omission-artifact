import pathlib,subprocess,json,hashlib,datetime
BASE=pathlib.Path(__file__).resolve().parent
IMAGE="sha256:56559845a6388a7f0141ceea11a76684615db3aa0d34e1f9521686bb508d53e5"
OBSERVER=r'''import pathlib,os,json,hashlib
root=pathlib.Path("/opt/replay/seed")
original={r["path"] for r in json.loads(pathlib.Path("/opt/replay/provenance/baseline-source-manifest.json").read_text())}
extras=[]
def walk(folder):
 for e in sorted(os.scandir(folder),key=lambda x:x.name):
  rel=pathlib.Path(e.path).relative_to(root).as_posix()
  if e.name in [".git","node_modules"] and e.is_dir(follow_symlinks=False):continue
  if e.is_symlink():
   if rel not in original:extras.append({"path":rel,"type":"symlink","target":os.readlink(e.path)})
  elif e.is_dir(follow_symlinks=False):walk(e.path)
  elif e.is_file(follow_symlinks=False) and rel not in original:
   b=pathlib.Path(e.path).read_bytes()
   extras.append({"path":rel,"type":"file","bytes":len(b),"sha256":hashlib.sha256(b).hexdigest()})
walk(root)
print(json.dumps({"untracked_files_or_links_outside_git_and_node_modules":extras,"count":len(extras),"generated_module_candidates":[e for e in extras if any(x in pathlib.PurePosixPath(e["path"]).parts for x in ["dist","build","generated"]) or e["path"].endswith((".js",".mjs",".cjs",".ts",".tsx",".node"))],"subject_code_executed":False}))
'''
args=["docker","run","--name","sp2027-wxyc-seed-outside-deps-audit-20261112","--network","none","--read-only","--user","10001:10001","--cap-drop","ALL","--security-opt","no-new-privileges:true","--pids-limit","64","--memory","256m","--cpus","1",IMAGE,"python3","-c",OBSERVER]
r=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=120)
(BASE/"outside-dependencies-observer.stdout.json").write_bytes(r.stdout)
(BASE/"outside-dependencies-observer.stderr.log").write_bytes(r.stderr)
receipt={"utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"image_id":IMAGE,"args":args,"exit_code":r.returncode,"stdout_sha256":hashlib.sha256(r.stdout).hexdigest(),"stderr_sha256":hashlib.sha256(r.stderr).hexdigest(),"study_code_or_build_execution":False,"container_retained":True}
(BASE/"OUTSIDE_DEPENDENCIES_OBSERVER_RECEIPT.json").write_text(json.dumps(receipt,indent=2)+"\n")
print(json.dumps({"exit_code":r.returncode,"report":json.loads(r.stdout) if r.returncode==0 else r.stderr.decode()}))

