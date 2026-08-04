from voice2fritz import config
from voice2fritz.gui.settings_dialog import SettingsDialog


def test_save_button_persists_config_and_password(qtbot, tmp_path, monkeypatch):
    saved_configs = []
    saved_passwords = []

    monkeypatch.setattr(config, "save_config", lambda cfg, path=config.DEFAULT_CONFIG_PATH: saved_configs.append(cfg))
    monkeypatch.setattr(config, "set_password", lambda username, password: saved_passwords.append((username, password)))

    dialog = SettingsDialog()
    qtbot.addWidget(dialog)

    dialog.host_edit.setText("fritz.box")
    dialog.username_edit.setText("user123")
    dialog.password_edit.setText("hunter2")

    with qtbot.waitSignal(dialog.accountSaved, timeout=1000):
        dialog.save_button.click()

    assert saved_configs == [config.AccountConfig(host="fritz.box", username="user123")]
    assert saved_passwords == [("user123", "hunter2")]


def test_save_button_persists_fritzbox_credentials(qtbot, tmp_path, monkeypatch):
    saved_usernames = []
    saved_passwords = []

    monkeypatch.setattr(config, "save_config", lambda cfg, path=config.DEFAULT_CONFIG_PATH: None)
    monkeypatch.setattr(config, "set_password", lambda username, password: None)
    monkeypatch.setattr(config, "save_fritzbox_username", lambda username, path=config.DEFAULT_CONFIG_PATH: saved_usernames.append(username))
    monkeypatch.setattr(config, "set_fritzbox_password", lambda username, password: saved_passwords.append((username, password)))

    dialog = SettingsDialog()
    qtbot.addWidget(dialog)

    dialog.host_edit.setText("fritz.box")
    dialog.username_edit.setText("sipuser")
    dialog.password_edit.setText("sip-secret")
    dialog.fritzbox_username_edit.setText("fritzuser")
    dialog.fritzbox_password_edit.setText("fritzbox-secret")

    with qtbot.waitSignal(dialog.accountSaved, timeout=1000):
        dialog.save_button.click()

    assert saved_usernames == ["fritzuser"]
    assert saved_passwords == [("fritzuser", "fritzbox-secret")]
