"""Capture package-installation provenance only; no research case is executed."""
import datetime
import hashlib
import importlib.metadata as md
import io
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import urllib.request
import zipfile

OUT = Path(__file__).resolve().parent
VERSIONS = {'pytest':'9.0.2', 'pytest-testmon':'2.3.0',
            'itsdangerous':'2.2.0', 'starlette':'0.50.0',
            'requests':'2.32.5', 'httpx':'0.28.1'}
details = {'scope':'Installation preparation only; original cases NOT_RUN; no hosted run',
           'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'python':sys.version, 'executable':sys.executable,
           'platform':platform.platform(), 'packages':{}}
plugin_wheel = None
for name, expected in VERSIONS.items():
    version = md.version(name)
    assert version == expected, (name,version,expected)
    url = f'https://pypi.org/pypi/{name}/{version}/json'
    raw = urllib.request.urlopen(url,timeout=30).read()
    (OUT / f'{name}-{version}-pypi.json').write_bytes(raw)
    info = json.loads(raw)
    package = {'version':version, 'metadata_url':url,
               'requires_dist':info['info']['requires_dist']}
    details['packages'][name] = package
    for entry in info['urls']:
        if entry['packagetype'] == 'bdist_wheel':
            data = urllib.request.urlopen(entry['url'],timeout=30).read()
            actual = hashlib.sha256(data).hexdigest()
            assert actual == entry['digests']['sha256']
            (OUT/entry['filename']).write_bytes(data)
            package['wheel'] = {'file':entry['filename'], 'sha256':actual,
                                'url':entry['url']}
            if name == 'pytest-testmon':
                plugin_wheel = data
            break
assert plugin_wheel is not None
details['plugin_modules'] = {}
dist = md.distribution('pytest-testmon')
with zipfile.ZipFile(io.BytesIO(plugin_wheel)) as wheel:
    for relative in dist.files:
        if str(relative).endswith('.py') and str(relative).startswith('testmon/'):
            source = Path(dist.locate_file(relative))
            data = source.read_bytes()
            assert data == wheel.read(str(relative)), f'Installed module differs from published wheel: {relative}'
            target = OUT/'pytest_testmon_source'/str(relative)
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(data)
            details['plugin_modules'][str(relative)] = hashlib.sha256(data).hexdigest()
details['installed_plugin_matches_wheel'] = bool(details['plugin_modules'])
env = dict(os.environ)
for key in ['PYTEST_ADDOPTS','PYTEST_PLUGINS','PYTHONPATH']:
    env.pop(key,None)
for label,args in [('pip-freeze',['-m','pip','freeze']),
                   ('pytest-version',['-m','pytest','--version']),
                   ('pytest-help',['-m','pytest','--help'])]:
    p = subprocess.run([sys.executable,*args],cwd=OUT,env=env,
                       capture_output=True,text=True,encoding='utf-8',errors='replace')
    (OUT/f'{label}.txt').write_text(p.stdout+p.stderr,encoding='utf-8')
    details[label] = {'exit':p.returncode,'file':f'{label}.txt'}
    assert p.returncode == 0, label
    if label == 'pip-freeze':
        (OUT/'requirements-frozen.txt').write_text(p.stdout,encoding='utf-8')
(OUT/'environment.json').write_text(json.dumps(details,indent=2),encoding='utf-8')
print(json.dumps({'scope':details['scope'], 'packages':VERSIONS,
                  'plugin_wheel_sha256':details['packages']['pytest-testmon']['wheel']['sha256'],
                  'plugin_modules_verified_against_wheel':len(details['plugin_modules'])},indent=2))
