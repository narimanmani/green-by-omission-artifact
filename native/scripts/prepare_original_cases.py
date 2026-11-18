"""Prepare exact original source-only cases from the recovered extension archive."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

CASES = {
    'itsdangerous_expiry': ('itsdangerous/timed.py','itsdangerous.timed','test_security_rejects_expired'),
    'starlette_trusted_host': ('starlette/middleware/trustedhost.py','starlette.middleware.trustedhost','test_security_rejects_untrusted_host'),
    'requests_crlf_header': ('requests/utils.py','requests.utils','test_security_rejects_header_injection'),
}

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('archive_root',type=Path)
    parser.add_argument('output',type=Path)
    args = parser.parse_args()
    original = args.archive_root.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True,exist_ok=False)
    manifest = {'cases':[]}
    provenance = {'archive_root':str(original),'method':'Faithful source-only case preparation from archived run_protected_ci.make_case and run_source_only_ci: restore snapshots/baseline.py; fix build_meta.version to 1 for all variants; keep original test bytes; set original pytest.ini testpaths/addopts.', 'cases':{}}
    for name,(target,module,test) in CASES.items():
        fixture = original/'fixtures'/f'{name}_copy_'
        baseline = output/name/'baseline'
        shutil.copytree(fixture,baseline,ignore=shutil.ignore_patterns('snapshots','.git','*.pyc','__pycache__','.coverage','.pytest_cache','.testmondata','*.db','result.json'))
        shutil.copyfile(fixture/'snapshots/baseline.py',baseline/target)
        (baseline/'build_meta.py').write_bytes(b'def version():\n    return 1\n')
        (baseline/'pytest.ini').write_bytes(b'[pytest]\ntestpaths = tests\naddopts = -rA\n')
        snapshots = output/name/'snapshots'
        snapshots.mkdir()
        for variant in ['ordinary','collision']:
            shutil.copyfile(fixture/f'snapshots/{variant}.py',snapshots/f'{variant}.py')
        hashes = {}
        for p in baseline.rglob('*'):
            if p.is_file(): hashes[p.relative_to(baseline).as_posix()] = digest(p)
        for p in (baseline/'tests').glob('*.py'):
            assert digest(p) == digest(fixture/'tests'/p.name), 'Original tests changed'
        provenance['cases'][name] = {'source_relative':target,'baseline_hashes':hashes,'snapshot_hashes':{v:digest(fixture/f'snapshots/{v}.py') for v in ['baseline','ordinary','collision']}}
        manifest['cases'].append({'name':name,'baseline_dir':f'{name}/baseline','source_relative':target,'ordinary_source':f'{name}/snapshots/ordinary.py','collision_source':f'{name}/snapshots/collision.py','security_nodeids':[f'tests/test_security.py::{test}'],'expected_import_origins':[{'module':module,'relative_path':target}],'expected_security_failure_patterns':['AssertionError','DID NOT RAISE']})
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    (output/'preparation-provenance.json').write_text(json.dumps(provenance,indent=2),encoding='utf-8')
    print(output/'manifest.json')

if __name__ == '__main__': main()
