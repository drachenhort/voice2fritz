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


def test_save_button_persists_google_priority_setting(qtbot, tmp_path, monkeypatch):
    saved_values = []

    monkeypatch.setattr(config, "save_config", lambda cfg, path=config.DEFAULT_CONFIG_PATH: None)
    monkeypatch.setattr(config, "set_password", lambda username, password: None)
    monkeypatch.setattr(config, "save_google_sync_overwrites_local", lambda value, path=config.DEFAULT_CONFIG_PATH: saved_values.append(value))

    dialog = SettingsDialog()
    qtbot.addWidget(dialog)

    dialog.host_edit.setText("fritz.box")
    dialog.username_edit.setText("user123")
    dialog.password_edit.setText("hunter2")
    dialog.google_priority_checkbox.setChecked(False)

    with qtbot.waitSignal(dialog.accountSaved, timeout=1000):
        dialog.save_button.click()

    assert saved_values == [False]


def test_constructor_loads_saved_google_priority_setting(qtbot, monkeypatch):
    monkeypatch.setattr(config, "load_google_sync_overwrites_local", lambda path=config.DEFAULT_CONFIG_PATH: False)

    dialog = SettingsDialog()
    qtbot.addWidget(dialog)

    assert dialog.google_priority_checkbox.isChecked() is False
