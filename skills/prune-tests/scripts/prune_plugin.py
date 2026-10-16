"""pytest plugin for prune-tests: per-test coverage contexts and a JSON-lines test log.
Load with `-p prune_plugin` and this folder on PYTHONPATH; PRUNE_LOG names the log."""
import json
import os

import coverage
import pytest

_LOG = os.environ.get("PRUNE_LOG")


def _write(row: dict) -> None:
    with open(_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item, nextitem):
    cov = coverage.Coverage.current()
    if cov:
        cov.switch_context(item.nodeid)
    yield
    if cov:
        cov.switch_context("")


def pytest_runtest_logreport(report):
    if _LOG:
        _write({"id": report.nodeid, "when": report.when,
                "outcome": report.outcome, "s": report.duration})


def pytest_collectreport(report):
    # A mutant that breaks a test module's import shows up here, not in runtest.
    if _LOG and report.failed:
        _write({"id": report.nodeid, "when": "collect", "outcome": "failed", "s": 0.0})
