"""Passive pytest observer loaded from outside the research Git checkout."""
import json
import os
from pathlib import Path
import sys
import pytest

data = {'collected_after_selection': [], 'deselected': [], 'reports': [], 'collection_errors': []}

@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(items):
    data['collected_after_selection'] = [i.nodeid for i in items]

def pytest_deselected(items):
    data['deselected'].extend(i.nodeid for i in items)

def pytest_runtest_logreport(report):
    entry = {'nodeid':report.nodeid, 'when':report.when, 'outcome':report.outcome}
    if report.failed:
        entry['failure_text'] = str(report.longrepr)
    data['reports'].append(entry)

def pytest_collectreport(report):
    if report.failed:
        data['collection_errors'].append({'nodeid':report.nodeid, 'failure_text':str(report.longrepr)})

def pytest_sessionfinish(session, exitstatus):
    data['exitstatus'] = int(exitstatus)
    data['executed_tests'] = sorted({r['nodeid'] for r in data['reports'] if r['when'] == 'call'})
    data['skipped_tests'] = sorted({r['nodeid'] for r in data['reports'] if r['outcome'] == 'skipped'})
    root = Path(os.environ['NATIVE_CASE_ROOT']).resolve()
    origins = []
    for rule in json.loads(os.environ['NATIVE_EXPECTED_IMPORT_ORIGINS']):
        module = sys.modules.get(rule['module'])
        filename = getattr(module, '__file__', None)
        actual = Path(filename).resolve() if filename else None
        expected = (root / rule.get('relative_path',rule.get('relative_prefix',''))).resolve()
        inside_root = actual is not None and actual.is_relative_to(root)
        matched = inside_root and (actual == expected if 'relative_path' in rule else actual.is_relative_to(expected))
        origins.append({'module':rule['module'], 'actual_file':str(actual) if actual else None, 'expected':str(expected), 'match_mode':'exact' if 'relative_path' in rule else 'prefix', 'matched':matched})
    data['import_origins'] = origins
    data['import_origins_valid'] = bool(origins) and all(o['matched'] for o in origins)
    Path(os.environ['NATIVE_EVIDENCE_JSON']).write_text(json.dumps(data, indent=2), encoding='utf-8')
