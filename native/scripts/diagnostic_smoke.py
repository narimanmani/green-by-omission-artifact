"""Plugin installation/platform diagnostic; never an original research-case result."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--output', type=Path, default=root / 'diagnostic_smoke')
args = parser.parse_args()
repo = args.output.resolve()
repo.mkdir(parents=True, exist_ok=False)
(repo / 'module').mkdir(exist_ok=True)
(repo / 'tests').mkdir(exist_ok=True)
(repo / '.gitignore').write_text('__pycache__/\n.pytest_cache/\n', encoding='utf-8')
(repo / 'module' / '__init__.py').write_text('', encoding='utf-8')
(repo / 'module' / 'calc.py').write_text('def add(a, b):\n    return a + b\n', encoding='utf-8')
(repo / 'tests' / 'test_calc.py').write_text('from module.calc import add\n\ndef test_add():\n    assert add(1, 2) == 3\n', encoding='utf-8')
commands = []
def call(args):
    p = subprocess.run(args, cwd=repo, capture_output=True, text=True, encoding='utf-8', env={**os.environ, 'PYTHONIOENCODING':'utf-8', 'PYTHONDONTWRITEBYTECODE':'1'})
    commands.append({'command': args, 'exit': p.returncode, 'stdout':p.stdout, 'stderr':p.stderr})
    return p
assert call(['git','init','-b','main']).returncode == 0
call(['git','config','user.name','Private research diagnostic'])
call(['git','config','user.email','research@example.invalid'])
call(['git','config','core.autocrlf','false'])
call(['git','add','.'])
call(['git','commit','-m','Diagnostic baseline'])
call(['git','update-ref','refs/remotes/origin/main','HEAD'])
call([sys.executable,'-m','pytest','--depper','--depper-base-branch=main','--depper-debug','-vv','-s'])
call(['git','switch','-c','ordinary-diagnostic'])
(repo / 'module' / 'calc.py').write_text('def add(a, b):\n    return a - b\n', encoding='utf-8')
call(['git','add','.'])
call(['git','commit','-m','Diagnostic ordinary change'])
call(['git','status','--porcelain=v1'])
call([sys.executable,'-m','pytest','--depper','--depper-base-branch=main','--depper-debug','-vv','-s'])
call([sys.executable,'-m','pytest','-vv','-s'])
(root / 'logs' / 'diagnostic-smoke.json').write_text(json.dumps({'scope':'Installation diagnostic only; not one of original cases', 'commands':commands},indent=2), encoding='utf-8')
for c in commands:
    if '-m' in c['command'] and 'pytest' in c['command']:
        print(c['exit'], c['stdout'], c['stderr'])
