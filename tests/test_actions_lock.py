import threading
import time

import pytest
from unittest.mock import patch


def _import_actions():
    from ui import actions

    return actions


def _wait_unlocked(actions, timeout=2.0):
    deadline = time.time() + timeout
    while actions.is_locked() and time.time() < deadline:
        time.sleep(0.005)


def test_run_locked_rejects_concurrent_call():
    actions = _import_actions()
    calls = []
    release = threading.Event()

    def target():
        calls.append(1)
        release.wait(1)

    with patch("ui.actions._notify_locked"):
        actions._run_locked(target)
        with pytest.raises(RuntimeError, match="Already running"):
            actions._run_locked(target)
        release.set()
        _wait_unlocked(actions)
        assert len(calls) == 1
        actions._set_locked(False)


def test_run_locked_allows_after_unlock():
    actions = _import_actions()
    calls = []

    def target():
        calls.append(1)

    with patch("ui.actions._notify_locked"):
        actions._run_locked(target)
        _wait_unlocked(actions)
        actions._run_locked(target)
        _wait_unlocked(actions)
        assert len(calls) == 2
