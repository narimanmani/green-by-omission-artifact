"""Prepare and run the fixed, offline replay; never run project code on the host."""
from pathlib import Path
import argparse, base64, gzip, hashlib, json, shutil, subprocess, time

ROOT = Path(__file__).resolve().parent
TAG = 'sp2027-wxyc-fixed-history-jq:20261112'
PREFIX = 'SP2027_EVIDENCE:'

def sha(data): return hashlib.sha256(data).hexdigest()
def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
def invoke(args, directory, name, check=True, timeout=3600):
    directory.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(args, capture_output=True, timeout=timeout)
    (directory / (name + '.stdout')).write_bytes(result.stdout)
    (directory / (name + '.stderr')).write_bytes(result.stderr)
    save_json(directory / (name + '.command.json'), dict(command=args, exit_code=result.returncode))
    if check and result.returncode:
        raise RuntimeError(name + ' failed; see retained command logs.')
    return result
def inspect_image(image):
    return json.loads(subprocess.check_output(['docker','image','inspect',image]))[0]

def prepare(args):
    freeze_path = ROOT / 'EXECUTION_FREEZE.json'
    if freeze_path.exists(): raise RuntimeError('Execution freeze already exists; refusing replacement.')
    seed = inspect_image(args.seed_image)
    if seed['Id'] != args.seed_image: raise RuntimeError('Pass an immutable seed image ID.')
    context = ROOT / 'lab-image-context'
    if context.exists(): raise RuntimeError('Build context already exists; refusing replacement.')
    context.mkdir()
    for source, destination in [
        (ROOT/'run_replay.mjs', 'run_replay.mjs'),
        (ROOT/'PROTOCOL_PREDECLARATION.json', 'FROZEN_PROTOCOL.json'),
        (ROOT/'PROTOCOL_PREDECLARATION.json', 'PROTOCOL_PREDECLARATION.json'),
        (ROOT/'INPUT_IDENTITY.json', 'INPUT_IDENTITY.json'),
        (ROOT/'input/baseline-source-manifest.json', 'input/baseline-source-manifest.json'),
        (ROOT/'input/candidate-source-manifest.json', 'input/candidate-source-manifest.json'),
        (ROOT/'input/original-unit-test-manifest.json', 'input/original-unit-test-manifest.json'),
        (ROOT/'input/fixed-candidate/shared/authentication/src/auth.definition.ts', 'candidate-auth.definition.ts'),
        (Path(args.seed_manifest), 'seed-installed-manifest.json')]:
        target = context / destination
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    if inspect_image('sp2027-wxyc-replay-seed-jq:20261112')['Id'] != args.seed_image:
        raise RuntimeError('Seed tag does not identify the supplied immutable image.')
    logs = ROOT / 'lab-preparation'
    existing = subprocess.run(['docker','image','inspect',TAG],capture_output=True)
    if existing.returncode == 0: raise RuntimeError('Final image tag already exists; refusing replacement.')
    assembly = invoke(['docker','create','--name','sp2027-wxyc-final-assembly-jq-20261112',
        '--network','none','--user','10001:10001','--cap-drop','ALL',
        '--security-opt','no-new-privileges:true',args.seed_image],logs,'create-unstarted-assembly').stdout.decode().strip()
    before = json.loads(subprocess.check_output(['docker','inspect',assembly]))[0]
    save_json(logs/'unstarted-assembly-inspect.json',before)
    if before['Image'] != args.seed_image or before['State']['Running'] or not before['State']['StartedAt'].startswith('0001-'):
        raise RuntimeError('Assembly container must be the exact seed and never started.')
    invoke(['docker','cp',str(context)+ '/.',assembly+':/opt/replay/'],logs,'copy-frozen-infrastructure')
    invoke(['docker','commit','--change','USER 10001:10001','--change','WORKDIR /work',
        '--change','ENV HOME=/work/home CI=true NODE_ENV=test EMAIL_ENABLED=false',
        '--change','ENTRYPOINT ["node","/opt/replay/run_replay.mjs"]','--change','CMD []',
        assembly,TAG],logs,'commit-unstarted-assembly')
    final = inspect_image(TAG)
    if final.get('Parent') != args.seed_image:
        raise RuntimeError('Final image parent does not equal the immutable seed.')
    seed_layers = seed.get('RootFS',{}).get('Layers',[])
    if not seed_layers or final.get('RootFS',{}).get('Layers',[])[:len(seed_layers)] != seed_layers:
        raise RuntimeError('Final image does not retain the frozen seed filesystem layers.')
    save_json(logs/'final-image-inspect.json', final)
    save_json(logs/'seed-image-inspect.json', seed)
    inputs = {str(path.relative_to(context)).replace('\\','/'):sha(path.read_bytes())
              for path in sorted(context.rglob('*')) if path.is_file()}
    freeze = dict(schema_version=1, frozen_at_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
                  seed_image_id=args.seed_image, final_image_id=final['Id'], context_files_sha256=inputs,
                  host_orchestrator_sha256=sha(Path(__file__).read_bytes()), repetitions=3,
                  study_test_executions_before_freeze=0, protocol=json.loads((context/'FROZEN_PROTOCOL.json').read_text()))
    save_json(freeze_path, freeze)
    print(json.dumps(dict(status='EXECUTION_FROZEN_NO_SUBJECT_RUN',image=final['Id'],freeze_sha256=sha(freeze_path.read_bytes()))),flush=True)

def execute(args):
    freeze_path = ROOT / 'EXECUTION_FREEZE.json'
    freeze = json.loads(freeze_path.read_text())
    if sha(Path(__file__).read_bytes()) != freeze['host_orchestrator_sha256']:
        raise RuntimeError('Frozen host orchestrator changed.')
    for name, expected in freeze['context_files_sha256'].items():
        if sha((ROOT/'lab-image-context'/name).read_bytes()) != expected:
            raise RuntimeError('Frozen input changed: ' + name)
    if args.repetition not in (1,2,3): raise RuntimeError('Only three predeclared repetitions are allowed.')
    folder = ROOT / 'results' / ('repetition-' + str(args.repetition))
    if folder.exists(): raise RuntimeError('Repetition evidence exists; refusing replacement.')
    folder.mkdir(parents=True)
    name = 'sp2027-wxyc-fixed-replay-jq-20261112-r' + str(args.repetition)
    image = freeze['final_image_id']
    command = ['docker','create','--name',name,'--hostname','sp2027-replay','--init',
        '--user','10001:10001','--network','none','--read-only','--cap-drop','ALL',
        '--security-opt','no-new-privileges:true','--cpus','2','--memory','6g','--memory-swap','6g',
        '--pids-limit','256','--stop-timeout','5',
        '--tmpfs','/work:rw,exec,nosuid,nodev,size=3g,uid=10001,gid=10001,mode=1777',
        '--tmpfs','/tmp:rw,noexec,nosuid,nodev,size=128m,uid=10001,gid=10001,mode=1777',
        '--env','CI=true','--env','NODE_ENV=test','--env','EMAIL_ENABLED=false','--env','HOME=/work/home',
        '--label','sp2027.study=wxyc-fixed-history-jq-20261112','--label','sp2027.repetition='+str(args.repetition),image]
    result = invoke(command,folder,'create')
    container = result.stdout.decode().strip()
    state = json.loads(subprocess.check_output(['docker','inspect',container]))[0]
    save_json(folder/'before-start-inspect.json',state)
    h,c = state['HostConfig'],state['Config']
    checks = dict(image=state['Image']==image,user=c.get('User')=='10001:10001',network=h.get('NetworkMode')=='none',
        readonly_root=h.get('ReadonlyRootfs') is True,cap_drop=set(h.get('CapDrop') or [])=={'ALL'},
        no_new_privileges=any('no-new-privileges' in item for item in h.get('SecurityOpt',[])),
        cpu=h.get('NanoCpus')==2_000_000_000,memory=h.get('Memory')==6*1024**3,
        swap=h.get('MemorySwap')==6*1024**3,pids=h.get('PidsLimit')==256,
        no_binds=not h.get('Binds'),no_host_mounts=not state.get('Mounts'),no_devices=not h.get('Devices'),
        not_privileged=not h.get('Privileged'),no_ports=not h.get('PortBindings') and not h.get('PublishAllPorts'),
        private_pid=not h.get('PidMode'),private_ipc=h.get('IpcMode')=='private',
        temporary_paths=set(h.get('Tmpfs') or {})=={'/work','/tmp'})
    sensitive = ('TOKEN','PASSWORD','SECRET','CREDENTIAL','ACCESS_KEY','PRIVATE_KEY')
    environment = dict(item.split('=',1) for item in c.get('Env',[]) if '=' in item)
    checks['no_nonempty_credential_environment'] = not any(value for key,value in environment.items() if any(word in key.upper() for word in sensitive))
    save_json(folder/'host-boundary-checks.json',dict(checks=checks,all_pass=all(checks.values())))
    if not all(checks.values()): raise RuntimeError('Container boundaries failed before start; no subject execution.')
    print(json.dumps(dict(status='STARTING_ISOLATED_REPETITION',repetition=args.repetition,container=container,boundaries=len(checks))),flush=True)
    try:
        result = invoke(['docker','start','--attach',container],folder,'execution',check=False,timeout=3600)
    except subprocess.TimeoutExpired:
        invoke(['docker','stop','--time','5',container],folder,'watchdog-stop',check=False)
        raise RuntimeError('One-hour container watchdog expired; evidence retained, no retry.')
    after = json.loads(subprocess.check_output(['docker','inspect',container]))[0]
    save_json(folder/'after-execution-inspect.json',after)
    lines = [line for line in result.stdout.decode('utf-8',errors='replace').splitlines() if line.startswith(PREFIX)]
    if len(lines)!=1: raise RuntimeError('Expected exactly one evidence envelope; raw output retained.')
    envelope = json.loads(lines[0][len(PREFIX):])
    packed = base64.b64decode(envelope['payload_base64'],validate=True)
    if len(packed)!=envelope['gzip_bytes'] or sha(packed)!=envelope['gzip_sha256']:
        raise RuntimeError('Evidence gzip identity mismatch.')
    payload = gzip.decompress(packed)
    if len(payload)!=envelope['uncompressed_bytes'] or sha(payload)!=envelope['uncompressed_sha256']:
        raise RuntimeError('Evidence payload identity mismatch.')
    (folder/'evidence.json').write_bytes(payload)
    save_json(folder/'export-envelope.json',{key:value for key,value in envelope.items() if key!='payload_base64'})
    evidence = json.loads(payload)
    outer_ok = result.returncode == 0 and after.get('State',{}).get('ExitCode') == 0 and not after.get('State',{}).get('OOMKilled') and not after.get('State',{}).get('Error')
    summary = dict(repetition=args.repetition,status=evidence.get('status') if outer_ok else 'INELIGIBLE_OUTER_CONTAINER_STATUS',
                   qualifying_joint_witness=outer_ok and evidence.get('qualifying_joint_witness') is True,
                   inner_qualifying_joint_witness=evidence.get('qualifying_joint_witness'),outer_container_eligible=outer_ok,
                   arms={key:arm.get('summary',{}).get('counts') for key,arm in evidence.get('arms',{}).items()},
                   process_exit=result.returncode,oom_killed=after.get('State',{}).get('OOMKilled'))
    save_json(folder/'host-summary.json',summary)
    print(json.dumps(summary),flush=True)

parser = argparse.ArgumentParser()
subs = parser.add_subparsers(dest='action',required=True)
prep = subs.add_parser('prepare'); prep.add_argument('--seed-image',required=True); prep.add_argument('--seed-manifest',required=True)
execution = subs.add_parser('execute'); execution.add_argument('--repetition',required=True,type=int)
arguments = parser.parse_args()
(prepare if arguments.action=='prepare' else execute)(arguments)
