"""Build and inspect one task-owned, offline fixed-replay container before execution."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent
IMAGE = 'sp2027-fixed-historical-replay:20261111-observer2'
NAME = 'sp2027-fixed-historical-replay-20261111-observer2'
SCRATCH = 'rw,noexec,nosuid,nodev,size=134217728,uid=10001,gid=10001,mode=0700'


def command(args, timeout=120):
    result = subprocess.run(args, cwd=ROOT, text=True, encoding='utf-8', errors='replace', capture_output=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError('Command failed: ' + repr(args[:3]) + '\n' + result.stderr[:2500] + '\n' + result.stdout[-2500:])
    return result.stdout


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    results = ROOT / 'results-corrected-observer'
    results.mkdir(exist_ok=True)
    require(not (results / 'execution.json').exists(), 'Preserve existing run; do not overwrite evidence')
    existing_containers = set(command(['docker', 'ps', '-aq', '--no-trunc']).split())
    existing_volumes = set(command(['docker', 'volume', 'ls', '-q']).split())
    image = json.loads(command(['docker', 'image', 'inspect', IMAGE]))[0]
    require(image['Os'] == 'linux' and image['Architecture'] == 'amd64', 'Wrong image platform')
    cid = command(['docker', 'create', '--name', NAME, '--platform', 'linux/amd64', '--user', '10001:10001',
                   '--read-only', '--network', 'none', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges:true',
                   '--tmpfs', '/tmp:' + SCRATCH, '--cpus', '1', '--memory', '512m', '--memory-swap', '512m',
                   '--pids-limit', '64', '--ipc', 'private', '--restart', 'no', '--log-driver', 'json-file',
                   '--log-opt', 'max-size=8m', '--log-opt', 'max-file=1',
                   '--label', 'research.scope=fixed-public-historical-regression-replay', IMAGE]).strip()
    before = json.loads(command(['docker', 'inspect', cid]))[0]
    h, c = before['HostConfig'], before['Config']
    checks = {
      'task_owned_name': before['Name'] == '/' + NAME,
      'expected_image': before['Image'] == image['Id'],
      'expected_entrypoint': c.get('Entrypoint') == ['python', '-I', '-B', '/opt/replay/runtime/run_replay.py'] and not c.get('Cmd'),
      'nonroot': c.get('User') == '10001:10001',
      'readonly_root': h.get('ReadonlyRootfs') is True,
      'no_network': h.get('NetworkMode') == 'none',
      'not_privileged': not h.get('Privileged'),
      'no_capabilities': h.get('CapDrop') == ['ALL'] and not h.get('CapAdd'),
      'no_new_privileges': h.get('SecurityOpt') in [['no-new-privileges:true'], ['no-new-privileges']],
      'no_host_or_volume_mounts': not h.get('Binds') and not h.get('VolumesFrom') and not any(m.get('Type') in ['bind', 'volume'] for m in before.get('Mounts', [])),
      'no_ports': not h.get('PortBindings') and not h.get('PublishAllPorts') and not c.get('ExposedPorts'),
      'no_devices': not h.get('Devices') and not h.get('DeviceRequests'),
      'private_namespaces': h.get('PidMode', '') == '' and h.get('IpcMode') == 'private',
      'bounded_cpu': h.get('NanoCpus') == 1000000000,
      'bounded_memory': h.get('Memory') == 536870912 and h.get('MemorySwap') == 536870912,
      'bounded_processes': h.get('PidsLimit') == 64,
      'bounded_temporary_storage': h.get('Tmpfs', {}).get('/tmp') == SCRATCH,
      'no_injected_credentials': set(e.split('=', 1)[0] for e in c.get('Env', [])) == set(e.split('=', 1)[0] for e in image['Config'].get('Env', [])),
    }
    (results / 'prestart-boundary.json').write_text(json.dumps({'container_id': cid, 'image_id': image['Id'], 'checks': checks}, indent=2) + '\n')
    require(all(checks.values()), 'Boundary check failed: ' + ', '.join(k for k, value in checks.items() if not value))
    command(['docker', 'start', '--attach', cid], timeout=300)
    after = json.loads(command(['docker', 'inspect', cid]))[0]
    raw = command(['docker', 'logs', cid])
    (results / 'raw-container-output.json').write_text(raw, encoding='utf-8')
    require(after['State']['Status'] == 'exited' and after['State']['ExitCode'] == 0, 'Replay infrastructure failed')
    report = json.loads(raw)
    (results / 'replay-result.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    preserved = existing_containers.issubset(set(command(['docker', 'ps', '-aq', '--no-trunc']).split())) and existing_volumes.issubset(set(command(['docker', 'volume', 'ls', '-q']).split()))
    require(preserved, 'Existing resource inventory changed')
    execution = {'container_id': cid, 'image_id': image['Id'], 'started_at': after['State']['StartedAt'],
       'finished_at': after['State']['FinishedAt'], 'exit_code': after['State']['ExitCode'], 'host_boundary_checks': checks,
       'preexisting_containers_and_volumes_retained': preserved,
       'result_sha256': hashlib.sha256((results / 'replay-result.json').read_bytes()).hexdigest(), 'status': report['status']}
    (results / 'execution.json').write_text(json.dumps(execution, indent=2) + '\n', encoding='utf-8')
    summary = {'status': report['status'], 'container_id': cid, 'image_id': image['Id'], 'repetitions': []}
    for row in report['repetitions']:
        item = {'repeat': row['repeat'], 'baseline': row['baseline']['counts'], 'baseline_setup_skips': row['baseline']['setup_skips'], 'baseline_eligible': row['baseline_eligible']}
        if 'selective' in row:
            item.update({'selective': row['selective']['counts'], 'selective_setup_skips': row['selective']['setup_skips'],
                         'independent_full': row['independent_full']['counts'], 'full_setup_skips': row['independent_full']['setup_skips'],
                         'conditions': row['conditions'], 'qualifying_joint_witness': row['qualifying_joint_witness']})
        summary['repetitions'].append(item)
    (results / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
