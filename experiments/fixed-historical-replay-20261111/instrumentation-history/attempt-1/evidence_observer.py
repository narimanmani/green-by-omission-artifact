"""Record outcomes without changing the original test suite or selection."""
import importlib.metadata
import json
import os
from pathlib import Path
import pytest

STATE = {"calls": [], "other_reports": [], "collection_errors": [], "deselected": []}


def pytest_sessionstart(session):
    import requests
    STATE["requests_import"] = requests.__file__
    STATE["requests_version"] = requests.__version__
    STATE["versions"] = {name: importlib.metadata.version(name) for name in
                         ["pytest", "pytest-testmon", "coverage", "urllib3", "certifi", "charset-normalizer", "idna"]}
    STATE["invocation"] = list(session.config.invocation_params.args)
    STATE["configured_addopts"] = session.config.getini("addopts")
    STATE["plugins"] = sorted(str(name) for name, obj in session.config.pluginmanager.list_name_plugin() if obj is not None)


def pytest_collection_finish(session):
    STATE["selected_items"] = [item.nodeid for item in session.items]


def pytest_deselected(items):
    STATE["deselected"].extend(item.nodeid for item in items)


def pytest_collectreport(report):
    if report.failed:
        STATE["collection_errors"].append({"nodeid": report.nodeid, "longrepr": str(report.longrepr)})


def pytest_runtest_logreport(report):
    item = {"nodeid": report.nodeid, "when": report.when, "outcome": report.outcome}
    if report.failed or report.skipped:
        item["longrepr"] = str(report.longrepr)
    STATE["calls" if report.when == "call" else "other_reports"].append(item)


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_sessionfinish(session, exitstatus):
    STATE["initial_exit_status"] = int(exitstatus)
    yield
    STATE["exit_status"] = int(session.exitstatus)
    STATE["testscollected"] = session.testscollected
    Path(os.environ["STUDY_OBSERVER_OUTPUT"]).write_text(json.dumps(STATE, indent=2) + "\n", encoding="utf-8")
