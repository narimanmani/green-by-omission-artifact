"""Inspect and run an offline parser-only diagnosis of existing snapshots."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent
IMAGE = 'sp2027-saved-case-diagnosis:20261111'
NAME = 'sp2027-saved-case-diagnosis-20261111'
TMP = 'rw,noexec,nosuid,nodev,size=16777216,uid=10001,gid=10001,mode=0700'


def command(args):
    p = subprocess.run(args, cwd=ROOT, text=True, capture_output=True, encoding='utf-8', timeout=60)
    if p.returncode:
        raise RuntimeError(p.stderr[:1500] + p.stdout[-1500:])
    return p.stdout


def main():
    assert not (ROOT / 'execution.json').exists(), 'Preserve existing diagnosis'
    image = json.loads(command(['docker', 'image', 'inspect', IMAGE]))[0]
    parent = json.loads(command(['docker', 'image', 'inspect', 'sp2027-fixed-historical-replay:20261111-observer2']))[0]
    assert parent['Id'] == 'sha256:5c2f0556d84fea99bea63538667c4754bef1d8e7ac20e137c36633e3e5c59d10'
    cid = command(['docker', 'create', '--name', NAME, '--platform', 'linux/amd64', '--user', '10001:10001',
        '--read-only', '--network', 'none', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges:true',
        '--tmpfs', '/tmp:' + TMP, '--cpus', '1', '--memory', '256m', '--memory-swap', '256m',
        '--pids-limit', '32', '--ipc', 'private', '--restart', 'no',
        '--label', 'research.scope=parser-only-saved-case-diagnosis', IMAGE]).strip()
    before = json.loads(command(['docker', 'inspect', cid]))[0]
    h, c = before['HostConfig'], before['Config']
    checks = {
        'task_owned': before['Name'] == '/' + NAME,
        'pinned_image': before['Image'] == image['Id'],
        'parser_only_entrypoint': c['Entrypoint'] == ['python', '-I', '-B', '/opt/diagnosis/diagnose_saved_case.py'] and not c.get('Cmd'),
        'nonroot': c['User'] == '10001:10001',
        'readonly_root': h['ReadonlyRootfs'],
        'network_disabled': h['NetworkMode'] == 'none',
        'unprivileged': not h['Privileged'],
        'all_capabilities_dropped': h['CapDrop'] == ['ALL'] and not h.get('CapAdd'),
        'no_new_privileges': h['SecurityOpt'] in [['no-new-privileges:true'], ['no-new-privileges']],
        'no_host_or_volume_mount': not h.get('Binds') and not h.get('VolumesFrom') and not any(m['Type'] in ['bind', 'volume'] for m in before.get('Mounts', [])),
        'no_devices': not h.get('Devices') and not h.get('DeviceRequests'),
        'no_ports': not h.get('PortBindings') and not h.get('PublishAllPorts') and not c.get('ExposedPorts'),
        'private_namespaces': h.get('PidMode', '') == '' and h['IpcMode'] == 'private',
        'bounded_cpu': h['NanoCpus'] == 1000000000,
        'bounded_memory': h['Memory'] == h['MemorySwap'] == 268435456,
        'bounded_processes': h['PidsLimit'] == 32,
        'bounded_scratch': h['Tmpfs'] == {'/tmp': TMP},
        'no_injected_environment': c['Env'] == image['Config']['Env'],
    }
    (ROOT / 'prestart-boundary.json').write_text(json.dumps(checks, indent=2) + '\n')
    assert all(checks.values()), checks
    output = command(['docker', 'start', '--attach', cid])
    result = json.loads(output)
    (ROOT / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    after = json.loads(command(['docker', 'inspect', cid]))[0]
    assert after['State']['Status'] == 'exited' and after['State']['ExitCode'] == 0
    assert json.loads(command(['docker', 'logs', cid])) == result
    receipt = {'container_id': cid, 'image_id': image['Id'], 'parent_image_id': parent['Id'],
        'started_at': after['State']['StartedAt'], 'finished_at': after['State']['FinishedAt'],
        'exit_code': after['State']['ExitCode'], 'host_boundary_checks': checks,
        'result_sha256': hashlib.sha256((ROOT / 'result.json').read_bytes()).hexdigest()}
    (ROOT / 'execution.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
