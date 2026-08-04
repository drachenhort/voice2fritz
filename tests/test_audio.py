from dataclasses import dataclass

from voice2fritz.audio import AudioDevice, list_audio_devices, input_devices, output_devices


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
