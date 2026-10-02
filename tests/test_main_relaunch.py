import sys

import pytest

from voice2fritz import main


@pytest.fixture
def recorded(monkeypatch):
    calls = {}
    monkeypatch.setattr(main.os, "execv", lambda path, args: calls.setdefault("execv", (path, args)))
    monkeypatch.setattr(main.subprocess, "Popen", lambda args: calls.setdefault("popen", args))
    monkeypatch.setattr(sys, "argv", ["voice2fritz", "--flag"])
    return calls


def test_relaunch_from_source_on_linux(monkeypatch, recorded):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.delattr(sys, "frozen", raising=False)

    main._relaunch()

    assert recorded["execv"] == (sys.executable, [sys.executable, "-m", "voice2fritz.main", "--flag"])


def test_relaunch_packaged_build_on_windows_spawns_and_exits(monkeypatch, recorded):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(sys, "frozen", True, raising=False)

    with pytest.raises(SystemExit):
        main._relaunch()

    assert recorded["popen"] == [sys.executable, "--flag"]
    assert "execv" not in recorded
