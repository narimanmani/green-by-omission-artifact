"""Passive pytest observation; never imports the application under test."""
import json
import os
from pathlib import Path
import sys
import pytest

data = {'collected': [], 'deselected': [], 'synthetic_deselected_count': 0,
        'reports': [], 'collection_errors': []}

def pytest_collection_finish(session):
    data['collected'] = [item.nodeid for item in session.items]

def pytest_deselected(items):
    for item in items:
        nodeid = getattr(item, 'nodeid', None)
        if nodeid is None:
            data['synthetic_deselected_count'] += 1
        else:
            data['deselected'].append(nodeid)

def pytest_collectreport(report):
    if report.failed:
        data['collection_errors'].append({'nodeid':report.nodeid,
                                          'longrepr':str(report.longrepr)})

def pytest_runtest_logreport(report):
    item = {'nodeid':report.nodeid, 'when':report.when, 'outcome':report.outcome}
    if report.failed:
        item['longrepr'] = str(report.longrepr)
    data['reports'].append(item)

@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_sessionfinish(session, exitstatus):
    # Capture after testmon's zero-collected -> success sessionfinish hook.
    yield
    data['initial_exitstatus'] = int(exitstatus)
    data['final_exitstatus'] = int(session.exitstatus)
    data['executed_tests'] = sorted({r['nodeid'] for r in data['reports']
                                     if r['when'] == 'call'})
    data['skipped_tests'] = sorted({r['nodeid'] for r in data['reports']
                                    if r['outcome'] == 'skipped'})
    module_name = os.environ['OBSERVER_TARGET_MODULE']
    module = sys.modules.get(module_name)
    data['target_module'] = {'name':module_name, 'loaded':module is not None,
                             'file':getattr(module, '__file__', None)}
    data['plugin_modules'] = {name:getattr(mod, '__file__', None)
                              for name,mod in sys.modules.items()
                              if name == 'testmon' or name.startswith('testmon.')}
    Path(os.environ['OBSERVER_OUTPUT']).write_text(json.dumps(data,indent=2),encoding='utf-8')
