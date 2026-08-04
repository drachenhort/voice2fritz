from dataclasses import dataclass

from PySide6.QtWidgets import QComboBox

from voice2fritz import config
from voice2fritz.audio import (
    AudioDevice,
    list_audio_devices,
    input_devices,
    output_devices,
    populate_and_restore_devices,
    restore_saved_devices,
)


@dataclass
class FakeRawDevice:
    name: str
    inputCount: int
    outputCount: int


def test_list_audio_devices_maps_fields_and_assigns_ids():
    raw = [
        FakeRawDevice(name="Built-in Mic", inputCount=2, outputCount=0),
        FakeRawDevice(name="Headset", inputCount=1, outputCount=2),
    ]

    devices = list_audio_devices(raw)

    assert devices == [
        AudioDevice(id=0, name="Built-in Mic", has_input=True, has_output=False),
        AudioDevice(id=1, name="Headset", has_input=True, has_output=True),
    ]


def test_list_audio_devices_empty():
    assert list_audio_devices([]) == []


def test_input_devices_filters_to_input_capable():
    devices = [
        AudioDevice(id=0, name="Mic", has_input=True, has_output=False),
        AudioDevice(id=1, name="Speaker", has_input=False, has_output=True),
    ]
    assert input_devices(devices) == [devices[0]]


def test_output_devices_filters_to_output_capable():
    devices = [
        AudioDevice(id=0, name="Mic", has_input=True, has_output=False),
        AudioDevice(id=1, name="Speaker", has_input=False, has_output=True),
    ]
    assert output_devices(devices) == [devices[1]]


class _FakeSipEngine:
    def __init__(self, devices):
        self._devices = devices
        self.selected_capture = None
        self.selected_playback = None

    def list_devices(self):
        return self._devices

    def select_capture_device(self, device_id):
        self.selected_capture = device_id

    def select_playback_device(self, device_id):
        self.selected_playback = device_id


def _sample_devices():
    return [
        AudioDevice(id=0, name="Built-in Mic", has_input=True, has_output=False),
        AudioDevice(id=1, name="Headset", has_input=True, has_output=True),
    ]


def test_restore_saved_devices_selects_matching_saved_names(monkeypatch):
    monkeypatch.setattr(config, "load_device_selection", lambda path=config.DEFAULT_CONFIG_PATH: ("Headset", "Headset"))
    engine = _FakeSipEngine(_sample_devices())

    restore_saved_devices(engine)

    assert engine.selected_capture == 1
    assert engine.selected_playback == 1


def test_restore_saved_devices_is_noop_when_nothing_saved(monkeypatch):
    monkeypatch.setattr(config, "load_device_selection", lambda path=config.DEFAULT_CONFIG_PATH: (None, None))
    engine = _FakeSipEngine(_sample_devices())

    restore_saved_devices(engine)

    assert engine.selected_capture is None
    assert engine.selected_playback is None


def test_populate_and_restore_devices_populates_combos(qtbot, monkeypatch):
    monkeypatch.setattr(config, "load_device_selection", lambda path=config.DEFAULT_CONFIG_PATH: (None, None))
    engine = _FakeSipEngine(_sample_devices())
    capture_combo = QComboBox()
    playback_combo = QComboBox()
    qtbot.addWidget(capture_combo)
    qtbot.addWidget(playback_combo)

    populate_and_restore_devices(engine, capture_combo, playback_combo)

    assert [capture_combo.itemText(i) for i in range(capture_combo.count())] == ["Built-in Mic", "Headset"]
    assert [playback_combo.itemText(i) for i in range(playback_combo.count())] == ["Headset"]
    assert engine.selected_capture == 0
    assert engine.selected_playback == 1


def test_populate_and_restore_devices_restores_saved_selection(qtbot, monkeypatch):
    monkeypatch.setattr(config, "load_device_selection", lambda path=config.DEFAULT_CONFIG_PATH: ("Headset", "Headset"))
    engine = _FakeSipEngine(_sample_devices())
    capture_combo = QComboBox()
    playback_combo = QComboBox()
    qtbot.addWidget(capture_combo)
    qtbot.addWidget(playback_combo)

    populate_and_restore_devices(engine, capture_combo, playback_combo)

    assert capture_combo.currentText() == "Headset"
    assert playback_combo.currentText() == "Headset"
    assert engine.selected_capture == 1
    assert engine.selected_playback == 1
