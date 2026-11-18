import os, pathlib, json, hashlib, subprocess, stat, datetime
ROOT=pathlib.Path("/opt/replay/seed")
OUT=pathlib.Path("/opt/replay")
base=json.loads((OUT/"provenance/baseline-source-manifest.json").read_text())
def digest(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()
source=[]
for row in base:
    f=ROOT/row["path"]
    got=digest(f) if f.is_file() else None
    source.append({"path":row["path"],"expected_sha256":row["sha256"],"observed_sha256":got,"unchanged":got==row["sha256"]})
def cli(args):
    r=subprocess.run(args,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    return {"args":args,"exit_code":r.returncode,"stdout":r.stdout,"stderr":r.stderr}
git={k:cli(v) for k,v in {"head":["git","rev-parse","HEAD"],"origin_main":["git","rev-parse","origin/main"],"tree":["git","rev-parse","HEAD^{tree}"],"status":["git","status","--porcelain=v1","--untracked-files=no"],"version":["git","--version"]}.items()}
lock=json.loads((ROOT/"package-lock.json").read_text())
installed=[]
missing=[]
mismatches=[]
for path,record in lock["packages"].items():
    if not path or record.get("link"):continue
    pj=ROOT/path/"package.json"
    if pj.exists():
        actual=json.loads(pj.read_text())
        row={"path":path,"expected_version":record.get("version"),"installed_version":actual.get("version"),"name":actual.get("name"),"resolved":record.get("resolved"),"integrity":record.get("integrity"),"version_matches":actual.get("version")==record.get("version")}
        installed.append(row)
        if not row["version_matches"]:mismatches.append(row)
    else:
        missing.append({"path":path,"optional":record.get("optional",False),"os":record.get("os"),"cpu":record.get("cpu"),"resolved":record.get("resolved")})
entries=[]
def walk(folder):
    for ent in sorted(os.scandir(folder),key=lambda x:x.name):
        rel=pathlib.Path(ent.path).relative_to(ROOT).as_posix()
        in_dep="node_modules" in pathlib.PurePosixPath(rel).parts
        if ent.is_symlink():
            if in_dep:entries.append({"path":rel,"type":"symlink","target":os.readlink(ent.path)})
        elif ent.is_dir(follow_symlinks=False):
            if ent.name!=".git":walk(ent.path)
        elif ent.is_file(follow_symlinks=False) and in_dep:
            entries.append({"path":rel,"type":"file","bytes":ent.stat().st_size,"sha256":digest(ent.path)})
walk(ROOT)
links=[]
for e in entries:
    if e["type"]=="symlink":
        target=e["target"]
        resolved=(ROOT/e["path"]).parent.joinpath(target).resolve()
        links.append({"path":e["path"],"target":target,"absolute_target":os.path.isabs(target),"resolved_inside_seed":resolved.is_relative_to(ROOT),"exists":resolved.exists()})
versions={}
for name,path in {"jest":"node_modules/jest/package.json","ts-jest":"node_modules/ts-jest/package.json","typescript":"node_modules/typescript/package.json","shared":"node_modules/@wxyc/shared/package.json"}.items():
    versions[name]=json.loads((ROOT/path).read_text()).get("version")
runtime={"node":cli(["node","--version"]),"npm":cli(["npm","--version"]),"git":git["version"]}
manifest={"schema_version":1,"baseline_commit":"b86530c6c656b7a8f72d42145e9d46995c7ab53d","root":str(ROOT),"entries":entries,"summary":{"entry_count":len(entries),"regular_file_count":sum(e["type"]=="file" for e in entries),"symlink_count":sum(e["type"]=="symlink" for e in entries),"regular_file_bytes":sum(e.get("bytes",0) for e in entries),"installed_versions":versions},"runtime":runtime}
(OUT/"seed-installed-manifest.json").write_text(json.dumps(manifest,separators=(",",":"))+"\n")
unexpected_missing=[x for x in missing if not x["optional"]]
pkgroot=json.loads((ROOT/"node_modules/@wxyc/shared/package.json").read_text())
shared_expected=json.loads((OUT/"provenance/shared-package-file-manifest.json").read_text())
shared=[]
for e in shared_expected:
    rel=e["path"].removeprefix("package/")
    path=ROOT/"node_modules/@wxyc/shared"/rel
    got=digest(path) if path.is_file() else None
    shared.append({"path":rel,"expected_sha256":e["sha256"],"observed_sha256":got,"match":got==e["sha256"]})
report={"verified_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"source_files":source,"all_baseline_tracked_bytes_unchanged":all(x["unchanged"] for x in source),"git":git,"runtime":runtime,"locked_installed_packages":installed,"missing_packages":missing,"unexpected_nonoptional_missing":unexpected_missing,"version_mismatches":mismatches,"symlinks":links,"all_installed_symlinks_relative_inside_seed":all(not x["absolute_target"] and x["resolved_inside_seed"] and x["exists"] for x in links),"shared_package_members":shared,"all_exact_shared_members_match":all(x["match"] for x in shared),"installed_manifest_sha256":digest(OUT/"seed-installed-manifest.json"),"study_tests_executed":False}
report["eligible_seed"]=report["all_baseline_tracked_bytes_unchanged"] and not unexpected_missing and not mismatches and report["all_installed_symlinks_relative_inside_seed"] and report["all_exact_shared_members_match"] and git["head"]["stdout"].strip()==manifest["baseline_commit"] and git["origin_main"]["stdout"].strip()==manifest["baseline_commit"] and not git["status"]["stdout"].strip()
(OUT/"seed-provenance.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps({"eligible_seed":report["eligible_seed"],"tracked_files":len(source),"dependency_files":manifest["summary"]["regular_file_count"],"dependency_symlinks":manifest["summary"]["symlink_count"],"locked_packages_present":len(installed),"optional_packages_absent":len(missing)-len(unexpected_missing),"unexpected_missing":len(unexpected_missing),"version_mismatches":len(mismatches),"all_shared_members_match":report["all_exact_shared_members_match"],"manifest_sha256":report["installed_manifest_sha256"]}),flush=True)
if not report["eligible_seed"]:raise SystemExit(2)

