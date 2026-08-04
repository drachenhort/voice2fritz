from dataclasses import dataclass


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
