from dataclasses import dataclass

from PySide6.QtWidgets import QComboBox

from voice2fritz import config


@dataclass
class AudioDevice:
    id: int
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
    devices = sip_engine.list_devices()
    for device in input_devices(devices):
        capture_combo.addItem(device.name, device.id)
    for device in output_devices(devices):
        playback_combo.addItem(device.name, device.id)

    capture_name, playback_name = config.load_device_selection()

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
