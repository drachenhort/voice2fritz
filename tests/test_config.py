import json

from voice2fritz.config import (
    AccountConfig,
    load_config,
    save_config,
    load_device_selection,
    save_device_selection,
    load_fritzbox_username,
    save_fritzbox_username,
    get_fritzbox_password,
    set_fritzbox_password,
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


def test_load_config_malformed_json_returns_none(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("{not valid json")
    assert load_config(path) is None


def test_load_config_missing_keys_returns_none(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"host": "fritz.box"}))
    assert load_config(path) is None


def test_save_config_creates_parent_dirs(tmp_path):
    path = tmp_path / "nested" / "dir" / "config.json"
    cfg = AccountConfig(host="fritz.box", username="user123")

    save_config(cfg, path)

    assert path.exists()
    assert json.loads(path.read_text()) == {"host": "fritz.box", "username": "user123"}


def test_save_and_load_device_selection_round_trip(tmp_path):
    path = tmp_path / "config.json"

    save_device_selection("Astro A50: USB Audio #1 (hw:1,1)", "pulse", path)

    assert load_device_selection(path) == ("Astro A50: USB Audio #1 (hw:1,1)", "pulse")


def test_load_device_selection_missing_file_returns_none_pair(tmp_path):
    path = tmp_path / "does-not-exist.json"
    assert load_device_selection(path) == (None, None)


def test_save_device_selection_preserves_existing_account(tmp_path):
    path = tmp_path / "config.json"
    cfg = AccountConfig(host="fritz.box", username="user123")
    save_config(cfg, path)

    save_device_selection("Astro A50", "pulse", path)

    assert load_config(path) == cfg
    assert load_device_selection(path) == ("Astro A50", "pulse")


def test_save_config_preserves_existing_device_selection(tmp_path):
    path = tmp_path / "config.json"
    save_device_selection("Astro A50", "pulse", path)

    cfg = AccountConfig(host="fritz.box", username="user123")
    save_config(cfg, path)

    assert load_config(path) == cfg
    assert load_device_selection(path) == ("Astro A50", "pulse")


def test_save_and_load_fritzbox_username_round_trip(tmp_path):
    path = tmp_path / "config.json"

    save_fritzbox_username("fritzuser", path)

    assert load_fritzbox_username(path) == "fritzuser"


def test_load_fritzbox_username_missing_file_returns_none(tmp_path):
    path = tmp_path / "does-not-exist.json"
    assert load_fritzbox_username(path) is None


def test_save_fritzbox_username_preserves_existing_account(tmp_path):
    path = tmp_path / "config.json"
    cfg = AccountConfig(host="fritz.box", username="user123")
    save_config(cfg, path)

    save_fritzbox_username("fritzuser", path)

    assert load_config(path) == cfg
    assert load_fritzbox_username(path) == "fritzuser"


def test_set_and_get_fritzbox_password_uses_distinct_keyring_key(monkeypatch):
    store: dict[tuple[str, str], str] = {}

    def fake_set_password(service, username, password):
        store[(service, username)] = password

    def fake_get_password(service, username):
        return store.get((service, username))

    monkeypatch.setattr("voice2fritz.config.keyring.set_password", fake_set_password)
    monkeypatch.setattr("voice2fritz.config.keyring.get_password", fake_get_password)

    set_password("user123", "sip-secret")
    set_fritzbox_password("user123", "fritzbox-secret")

    assert get_password("user123") == "sip-secret"
    assert get_fritzbox_password("user123") == "fritzbox-secret"


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
