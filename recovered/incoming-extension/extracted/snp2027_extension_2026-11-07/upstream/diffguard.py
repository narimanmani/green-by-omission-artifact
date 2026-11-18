"""Independent RESEARCH COMPARATOR, not a published RTS tool.

Git changed-file identity + conservative static Python import graph.  No source
fingerprints, runtime caches, CRCs, or runtime coverage dependencies.
Only intended as a local algorithmic control against testmon's selection.
"""
import ast
from collections import deque
from pathlib import Path
import subprocess
import pytest


def pytest_addoption(parser):
    parser.getgroup('static-diff-comparator').addoption(
        '--static-diff', action='store_true', default=False,
        help='Select tests transitively importing changed application modules')


def modules(root):
    out={}
    for f in root.rglob('*.py'):
        rel=f.relative_to(root)
        if any(x in ('.git','__pycache__','.pytest_cache','snapshots','upstream','.tox','tests') for x in rel.parts):
            continue
        parts=list(rel.with_suffix('').parts)
        if parts[-1]=='__init__':parts.pop()
        if parts:out['.'.join(parts)]=f
    return out


def imports(filename, name, modindex):
    try:tree=ast.parse(filename.read_text())
    except (SyntaxError,UnicodeError,OSError):return set()
    deps=set()
    pkg=name if filename.name=='__init__.py' else '.'.join(name.split('.')[:-1])
    for n in ast.walk(tree):
        if isinstance(n,ast.Import):
            for a in n.names:
                v=a.name
                if v in modindex:deps.add(v)
                elif v.split('.')[0] in modindex:deps.add(v.split('.')[0])
        if isinstance(n,ast.ImportFrom):
            if n.level:
                pp=pkg.split('.') if pkg else []
                pp=pp[:max(0,len(pp)-n.level+1)]
                base='.'.join([*pp,*([n.module] if n.module else [])])
            else:base=n.module or ''
            if base in modindex:deps.add(base)
            for a in n.names:
                full=base+'.'+a.name if base else a.name
                if full in modindex:deps.add(full)
    return deps


def affected_test_files(root,changed):
    idx=modules(root)
    changed_modules={k for k,f in idx.items() if str(f.relative_to(root)) in changed}
    graph={k:imports(f,k,idx) for k,f in idx.items()}
    result=set()
    all_tests=list((root/'tests').rglob('test_*.py'))
    for f in all_tests:
        todo=deque(imports(f,'tests.'+f.stem,idx));seen=set()
        while todo:
            current=todo.popleft()
            if current in seen:continue
            seen.add(current)
            todo.extend(graph.get(current,()))
        if changed_modules.intersection(seen) or str(f.relative_to(root)) in changed:
            result.add(str(f.relative_to(root)))
    return result,changed_modules


def pytest_collection_modifyitems(config,items):
    if not config.getoption('--static-diff'):return
    root=Path(config.rootpath)
    cmd=['git','diff','--name-only','main...HEAD']
    p=subprocess.run(cmd,cwd=root,text=True,capture_output=True)
    if p.returncode:raise pytest.UsageError('Cannot compare changes with trusted main: '+p.stderr)
    changed=set(p.stdout.strip().splitlines())
    selected,mods=affected_test_files(root,changed)
    # Fail closed, not fail open, if changed code has no statically imported dependents.
    if any(x.endswith('.py') for x in changed) and not selected:
        selected={str(Path(x.path).relative_to(root)) for x in items}
    keep=[];drop=[]
    for item in items:
        path=str(Path(item.path).relative_to(root))
        (keep if path in selected else drop).append(item)
    items[:]=keep
    config.hook.pytest_deselected(items=drop)
    print(f'STATIC_DIFF changed={sorted(changed)!r} modules={sorted(mods)!r} testfiles={sorted(selected)!r}')
