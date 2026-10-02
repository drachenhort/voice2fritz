from dataclasses import dataclass

from PySide6.QtWidgets import QComboBox

from voice2fritz import audio, config
from voice2fritz.audio import (
    AudioDevice,
    list_audio_devices,
    list_pulse_devices,
    parse_pulse_devices,
    wav_is_finalized,
    wav_peak,
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


def test_parse_pulse_devices_uses_descriptions_and_skips_monitors():
    sinks = [{"name": "Arctis_Chat", "description": "Arctis Nova 7 Chat"}]
    sources = [
        {"name": "alsa_input.usb-headset", "description": "Headset Mic", "properties": {"device.class": "sound"}},
        {"name": "Arctis_Chat.monitor", "description": "Monitor of Arctis Nova 7 Chat", "properties": {"device.class": "monitor"}},
    ]

    assert parse_pulse_devices(sinks, sources) == [
        AudioDevice(id="Arctis_Chat", name="Arctis Nova 7 Chat", has_input=False, has_output=True),
        AudioDevice(id="alsa_input.usb-headset", name="Headset Mic", has_input=True, has_output=False),
    ]


def test_list_pulse_devices_prepends_system_default(monkeypatch):
    lists = {
        "sinks": [{"name": "Arctis_Chat", "description": "Arctis Nova 7 Chat"}],
        "sources": [{"name": "mic", "description": "Headset Mic", "properties": {}}],
    }
    monkeypatch.setattr(audio, "_pactl_list", lambda kind: lists[kind])

    devices = list_pulse_devices()

    assert devices[0] == AudioDevice(id="", name="System default", has_input=True, has_output=True)
    assert [d.name for d in devices[1:]] == ["Arctis Nova 7 Chat", "Headset Mic"]


def test_list_pulse_devices_empty_without_pactl(monkeypatch):
    def missing_pactl(*args, **kwargs):
        raise FileNotFoundError("pactl")

    monkeypatch.setattr(audio.subprocess, "run", missing_pactl)

    assert list_pulse_devices() == []


def _wav_header(data_size):
    return b"RIFF" + (36 + data_size).to_bytes(4, "little") + b"WAVEfmt " + bytes(20) + b"data" + data_size.to_bytes(4, "little")


def test_wav_is_finalized_once_data_size_written(tmp_path):
    path = tmp_path / "echo.wav"
    path.write_bytes(_wav_header(0) + bytes(4096))
    assert wav_is_finalized(str(path)) is False

    path.write_bytes(_wav_header(4096) + bytes(4096))
    assert wav_is_finalized(str(path)) is True


def test_wav_is_finalized_false_for_missing_file(tmp_path):
    assert wav_is_finalized(str(tmp_path / "missing.wav")) is False


def _write_wav(path, samples):
    import array
    import wave

    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(array.array("h", samples).tobytes())


def test_wav_peak_returns_largest_absolute_sample(tmp_path):
    path = tmp_path / "echo.wav"
    _write_wav(path, [0, 120, -6836, 300])

    assert wav_peak(str(path)) == 6836


def test_wav_peak_is_zero_for_unreadable_file(tmp_path):
    path = tmp_path / "broken.wav"
    path.write_bytes(b"not a wav")

    assert wav_peak(str(path)) == 0
    assert wav_peak(str(tmp_path / "missing.wav")) == 0
