import json

import pytest

from voice2fritz.config import (
    AccountConfig,
    load_config,
    save_config,
    get_password,
    set_password,
)


def test_save_and_load_config_round_trip(tmp_path):
    path = tmp_path / "config.json"
    cfg = AccountConfig(host="fritz.box", username="user123")

    save_config(cfg, path)
    loaded = load_config(path)

    assert loaded == cfg


def test_load_config_missing_file_returns_none(tmp_path):
    path = tmp_path / "does-not-exist.json"
    assert load_config(path) is None


def test_save_config_creates_parent_dirs(tmp_path):
    path = tmp_path / "nested" / "dir" / "config.json"
    cfg = AccountConfig(host="fritz.box", username="user123")

    save_config(cfg, path)

    assert path.exists()
    assert json.loads(path.read_text()) == {"host": "fritz.box", "username": "user123"}


def test_set_and_get_password_uses_keyring(monkeypatch):
    store: dict[tuple[str, str], str] = {}

    def fake_set_password(service, username, password):
        store[(service, username)] = password

    def fake_get_password(service, username):
        return store.get((service, username))

    monkeypatch.setattr("voice2fritz.config.keyring.set_password", fake_set_password)
    monkeypatch.setattr("voice2fritz.config.keyring.get_password", fake_get_password)

    set_password("user123", "hunter2")

    assert get_password("user123") == "hunter2"
    assert store[("voice2fritz", "user123")] == "hunter2"


def test_get_password_unknown_user_returns_none(monkeypatch):
    monkeypatch.setattr("voice2fritz.config.keyring.get_password", lambda service, username: None)
    assert get_password("nobody") is None
