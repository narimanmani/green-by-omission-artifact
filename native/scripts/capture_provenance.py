import hashlib
import importlib.metadata as md
import json
import platform
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'provenance'
OUT.mkdir(exist_ok=True)
names = ['pytest', 'pytest-depper', 'itsdangerous', 'starlette', 'requests', 'httpx']
details = {'python': sys.version, 'executable': sys.executable, 'platform': platform.platform(), 'packages': {}}
for name in names:
    version = md.version(name)
    url = f'https://pypi.org/pypi/{name}/{version}/json'
    raw = urllib.request.urlopen(url).read()
    (OUT / f'{name}-{version}-pypi.json').write_bytes(raw)
    info = json.loads(raw)
    details['packages'][name] = {'version': version, 'metadata_url': url, 'requires_dist': info['info']['requires_dist']}
    for entry in info['urls']:
        if entry['packagetype'] == 'bdist_wheel':
            dest = OUT / entry['filename']
            dest.write_bytes(urllib.request.urlopen(entry['url']).read())
            actual = hashlib.sha256(dest.read_bytes()).hexdigest()
            assert actual == entry['digests']['sha256']
            details['packages'][name]['wheel'] = {'file': dest.name, 'sha256': actual, 'url': entry['url']}
            break
import pytest_depper
src = Path(pytest_depper.__file__).parent
target = OUT / 'pytest_depper_source'
target.mkdir(exist_ok=True)
details['plugin_modules'] = {}
for f in src.glob('*.py'):
    shutil.copy2(f, target / f.name)
    details['plugin_modules'][f.name] = hashlib.sha256(f.read_bytes()).hexdigest()
(OUT / 'environment.json').write_text(json.dumps(details, indent=2), encoding='utf-8')
for label, args in [('pip-freeze', ['-m', 'pip', 'freeze']), ('pytest-version', ['-m', 'pytest', '--version']), ('pytest-help', ['-m', 'pytest', '--help'])]:
    p = subprocess.run([sys.executable, *args], capture_output=True, text=True, encoding='utf-8')
    (OUT / f'{label}.txt').write_text(p.stdout + p.stderr, encoding='utf-8')
    if label == 'pip-freeze':
        (OUT / 'requirements-frozen.txt').write_text(p.stdout, encoding='utf-8')
print(json.dumps(details, indent=2))
