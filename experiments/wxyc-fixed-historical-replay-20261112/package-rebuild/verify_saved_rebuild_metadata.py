import base64, hashlib, json, pathlib, datetime
p=pathlib.Path(__file__).resolve().parent
source={r["path"]:r for r in json.loads((p/"SOURCE_FILE_MANIFEST.json").read_text())}
mapping={"package.json":"post-build-package.json","package-lock.json":"post-build-package-lock.json","scripts/generate-models.js":"post-build-generate-models.js","tsup.config.ts":"post-build-tsup.config.ts","tsconfig.json":"post-build-tsconfig.json","api.yaml":"post-build-api.yaml"}
checks=[]
for original,copy in mapping.items():
    b=(p/copy).read_bytes()
    checks.append({"original":original,"copy":copy,"sha256":hashlib.sha256(b).hexdigest(),"unchanged":hashlib.sha256(b).hexdigest()==source[original]["sha256"]})
isolations=[]
for log in ["05-provision-inspect.log","13-offline-inspect.log"]:
    row=json.loads((p/log).read_text())[0]
    h=row["HostConfig"]
    isolations.append({"stage":log,"user":row["Config"]["User"],"network_mode":h["NetworkMode"],"mounts":row["Mounts"],"binds":h.get("Binds"),"port_bindings":h.get("PortBindings"),"cap_drop":h["CapDrop"],"security_options":h["SecurityOpt"],"privileged":h["Privileged"],"memory_bytes":h["Memory"],"cpu_nanoseconds":h["NanoCpus"],"pids_limit":h["PidsLimit"],"environment_variable_names":[s.split("=",1)[0] for s in row["Config"]["Env"]]})
b=(p/"wxyc-shared-4.1.0.tgz").read_bytes()
expected=json.loads((p/"FROZEN_BUILD_PLAN.json").read_text())["expected_full_integrity"]
observed="sha512-"+base64.b64encode(hashlib.sha512(b).digest()).decode()
out={"checked_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"artifact_code_execution":False,"full_integrity":observed,"full_integrity_matches_original_lock":observed==expected,"original_build_input_copies":checks,"all_copied_original_inputs_unchanged":all(x["unchanged"] for x in checks),"isolation":isolations,"git_in_base_image":False,"git_probe":"Read-only network:none base-image command-v git returned no executable path."}
(p/"POST_BUILD_READONLY_VERIFICATION.json").write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
rows=[]
for f in sorted(p.rglob("*")):
    if f.is_file() and f.name!="SHA256_MANIFEST.json":
        b=f.read_bytes()
        rows.append({"path":f.relative_to(p).as_posix(),"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest()})
(p/"SHA256_MANIFEST.json").write_text(json.dumps(rows,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"full_hash_match":out["full_integrity_matches_original_lock"],"all_six_build_inputs_unchanged":out["all_copied_original_inputs_unchanged"],"manifest_files":len(rows),"manifest_sha256":hashlib.sha256((p/"SHA256_MANIFEST.json").read_bytes()).hexdigest()}))

