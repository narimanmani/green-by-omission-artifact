import pathlib,json,hashlib,os,subprocess
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
