import pytest

from voice2fritz import config
from voice2fritz.audio import AudioDevice
from voice2fritz.gui.settings_dialog import SettingsDialog


class _FakeSipEngine:
    def __init__(self, devices=None):
        self._devices = devices or []
        self.selected_capture = None
        self.selected_playback = None

    def list_devices(self):
        return self._devices

    def select_capture_device(self, device_id):
        self.selected_capture = device_id

    def select_playback_device(self, device_id):
        self.selected_playback = device_id


@pytest.fixture(autouse=True)
def no_device_persistence(monkeypatch):
    monkeypatch.setattr(config, "load_device_selection", lambda path=config.DEFAULT_CONFIG_PATH: (None, None))
    monkeypatch.setattr(config, "save_device_selection", lambda capture, playback, path=config.DEFAULT_CONFIG_PATH: None)


def test_save_button_persists_config_and_password(qtbot, tmp_path, monkeypatch):
    saved_configs = []
    saved_passwords = []

    monkeypatch.setattr(config, "save_config", lambda cfg, path=config.DEFAULT_CONFIG_PATH: saved_configs.append(cfg))
    monkeypatch.setattr(config, "set_password", lambda username, password: saved_passwords.append((username, password)))

    dialog = SettingsDialog(_FakeSipEngine())
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

    dialog = SettingsDialog(_FakeSipEngine())
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

    dialog = SettingsDialog(_FakeSipEngine())
    qtbot.addWidget(dialog)

    assert dialog.google_priority_checkbox.isChecked() is False


def _sample_devices():
    return [
        AudioDevice(id=0, name="Built-in Mic", has_input=True, has_output=False),
        AudioDevice(id=1, name="Headset", has_input=True, has_output=True),
    ]


def test_device_combos_populated_from_engine(qtbot):
    engine = _FakeSipEngine(_sample_devices())

    dialog = SettingsDialog(engine)
    qtbot.addWidget(dialog)

    assert [dialog.capture_combo.itemText(i) for i in range(dialog.capture_combo.count())] == [
        "Built-in Mic",
        "Headset",
    ]
    assert [dialog.speaker_combo.itemText(i) for i in range(dialog.speaker_combo.count())] == ["Headset"]


def test_initial_device_selection_applied_at_construction(qtbot):
    engine = _FakeSipEngine(_sample_devices())

    dialog = SettingsDialog(engine)
    qtbot.addWidget(dialog)

    assert engine.selected_capture == dialog.capture_combo.itemData(0)
    assert engine.selected_playback == dialog.speaker_combo.itemData(0)


def test_restores_saved_device_selection_on_construction(qtbot, monkeypatch):
    monkeypatch.setattr(config, "load_device_selection", lambda path=config.DEFAULT_CONFIG_PATH: ("Headset", "Headset"))
    engine = _FakeSipEngine(_sample_devices())

    dialog = SettingsDialog(engine)
    qtbot.addWidget(dialog)

    assert dialog.capture_combo.currentText() == "Headset"
    assert dialog.speaker_combo.currentText() == "Headset"
    assert engine.selected_capture == 1
    assert engine.selected_playback == 1


def test_device_combo_selection_calls_engine(qtbot):
    engine = _FakeSipEngine(_sample_devices())
    dialog = SettingsDialog(engine)
    qtbot.addWidget(dialog)

    dialog.capture_combo.setCurrentIndex(1)

    assert engine.selected_capture == 1


def test_device_selection_change_persists_choice(qtbot, monkeypatch):
    saved = []
    monkeypatch.setattr(
        config,
        "save_device_selection",
        lambda capture, playback, path=config.DEFAULT_CONFIG_PATH: saved.append((capture, playback)),
    )
    engine = _FakeSipEngine(_sample_devices())
    dialog = SettingsDialog(engine)
    qtbot.addWidget(dialog)
    saved.clear()

    dialog.capture_combo.setCurrentIndex(1)

    assert saved == [("Headset", "Headset")]


def test_opening_dialog_does_not_overwrite_saved_device_selection(qtbot, monkeypatch):
    # Stateful fake: unlike the constant-lambda fakes used elsewhere in this file,
    # this one actually reflects what gets saved during construction - so it can
    # catch a regression where signal-driven saves fire before the real saved
    # value has been read and restored.
    store = {"capture": "Headset", "playback": "Headset"}

    def fake_load(path=config.DEFAULT_CONFIG_PATH):
        return (store["capture"], store["playback"])

    def fake_save(capture, playback, path=config.DEFAULT_CONFIG_PATH):
        store["capture"] = capture
        store["playback"] = playback

    monkeypatch.setattr(config, "load_device_selection", fake_load)
    monkeypatch.setattr(config, "save_device_selection", fake_save)

    devices = [
        AudioDevice(id=0, name="Built-in Mic", has_input=True, has_output=True),
        AudioDevice(id=1, name="Headset", has_input=True, has_output=True),
    ]
    engine = _FakeSipEngine(devices)

    dialog = SettingsDialog(engine)
    qtbot.addWidget(dialog)

    assert store == {"capture": "Headset", "playback": "Headset"}
    assert engine.selected_capture == 1
    assert engine.selected_playback == 1


def test_host_and_username_prefilled_from_existing_account(qtbot, monkeypatch):
    monkeypatch.setattr(
        config,
        "load_config",
        lambda path=config.DEFAULT_CONFIG_PATH: config.AccountConfig(host="fritz.box", username="user123"),
    )

    dialog = SettingsDialog(_FakeSipEngine())
    qtbot.addWidget(dialog)

    assert dialog.host_edit.text() == "fritz.box"
    assert dialog.username_edit.text() == "user123"


def test_host_and_username_stay_empty_when_no_existing_account(qtbot, monkeypatch):
    monkeypatch.setattr(config, "load_config", lambda path=config.DEFAULT_CONFIG_PATH: None)

    dialog = SettingsDialog(_FakeSipEngine())
    qtbot.addWidget(dialog)

    assert dialog.host_edit.text() == ""
    assert dialog.username_edit.text() == ""
