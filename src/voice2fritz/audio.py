import json
import subprocess
from dataclasses import dataclass

from PySide6.QtWidgets import QComboBox

from voice2fritz import config


SYSTEM_DEFAULT_LABEL = "System default"


@dataclass
class AudioDevice:
    # int: PJSIP device index. str: PipeWire/PulseAudio node name ("" = system default).
    id: int | str
    name: str
    has_input: bool
    has_output: bool


def list_audio_devices(raw_devices: list) -> list[AudioDevice]:
    return [
        AudioDevice(
            id=index,
            name=raw.name,
            has_input=raw.inputCount > 0,
            has_output=raw.outputCount > 0,
        )
        for index, raw in enumerate(raw_devices)
    ]


def _pactl_list(kind: str) -> list[dict]:
    try:
        output = subprocess.run(
            ["pactl", "-f", "json", "list", kind],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        ).stdout
        return json.loads(output)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        return []


def parse_pulse_devices(sinks: list[dict], sources: list[dict]) -> list[AudioDevice]:
    devices = [
        AudioDevice(id=sink["name"], name=sink.get("description") or sink["name"], has_input=False, has_output=True)
        for sink in sinks
    ]
    devices.extend(
        AudioDevice(id=source["name"], name=source.get("description") or source["name"], has_input=True, has_output=False)
        for source in sources
        if source.get("properties", {}).get("device.class") != "monitor"
    )
    return devices


def list_pulse_devices() -> list[AudioDevice]:
    devices = parse_pulse_devices(_pactl_list("sinks"), _pactl_list("sources"))
    if not devices:
        return []
    default = AudioDevice(id="", name=SYSTEM_DEFAULT_LABEL, has_input=True, has_output=True)
    return [default, *devices]


def wav_is_finalized(path: str) -> bool:
    """True once a WAV recorder has written its header's data size (it does so on close)."""
    try:
        with open(path, "rb") as wav:
            header = wav.read(44)
    except OSError:
        return False
    return len(header) == 44 and header[:4] == b"RIFF" and int.from_bytes(header[40:44], "little") > 0


def input_devices(devices: list[AudioDevice]) -> list[AudioDevice]:
    return [d for d in devices if d.has_input]


def output_devices(devices: list[AudioDevice]) -> list[AudioDevice]:
    return [d for d in devices if d.has_output]


def restore_saved_devices(sip_engine) -> None:
    devices = sip_engine.list_devices()
    capture_name, playback_name = config.load_device_selection()

    if capture_name is not None:
        for device in input_devices(devices):
            if device.name == capture_name:
                sip_engine.select_capture_device(device.id)
                break

    if playback_name is not None:
        for device in output_devices(devices):
            if device.name == playback_name:
                sip_engine.select_playback_device(device.id)
                break


def populate_and_restore_devices(
    sip_engine,
    capture_combo: QComboBox,
    playback_combo: QComboBox,
) -> None:
    capture_name, playback_name = config.load_device_selection()

    devices = sip_engine.list_devices()
    for device in input_devices(devices):
        capture_combo.addItem(device.name, device.id)
    for device in output_devices(devices):
        playback_combo.addItem(device.name, device.id)

    if capture_name is not None:
        index = capture_combo.findText(capture_name)
        if index >= 0:
            capture_combo.setCurrentIndex(index)
    if capture_combo.count() > 0:
        sip_engine.select_capture_device(capture_combo.itemData(capture_combo.currentIndex()))

    if playback_name is not None:
        index = playback_combo.findText(playback_name)
        if index >= 0:
            playback_combo.setCurrentIndex(index)
    if playback_combo.count() > 0:
        sip_engine.select_playback_device(playback_combo.itemData(playback_combo.currentIndex()))
