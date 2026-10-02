import pytest

from voice2fritz import config
from voice2fritz.gui import settings_panel as settings_panel_module
from voice2fritz.gui.settings_panel import SettingsPanel
from voice2fritz.sip_engine import peak_to_level


class _RecordingEngine:
    def __init__(self):
        self.events = []
        self.level = 0.0
        self.fail_recording = False

    def list_devices(self):
        return []

    def select_capture_device(self, device_id):
        pass

    def select_playback_device(self, device_id):
        pass

    def start_level_monitor(self):
        self.events.append("monitor on")

    def stop_level_monitor(self):
        self.events.append("monitor off")

    def capture_level(self):
        return self.level

    def start_echo_recording(self, path):
        if self.fail_recording:
            raise RuntimeError("no capture device")
        self.events.append("record")

    def stop_echo_recording(self):
        self.events.append("stop record")

    def start_echo_playback(self, path):
        self.events.append("play")

    def stop_echo_playback(self):
        self.events.append("stop play")


@pytest.fixture(autouse=True)
def no_device_persistence(monkeypatch):
    monkeypatch.setattr(config, "load_device_selection", lambda path=config.DEFAULT_CONFIG_PATH: (None, None))
    monkeypatch.setattr(config, "save_device_selection", lambda capture, playback, path=config.DEFAULT_CONFIG_PATH: None)


@pytest.fixture
def finalized_wav(monkeypatch):
    state = {"ready": True}
    monkeypatch.setattr(settings_panel_module, "wav_is_finalized", lambda path: state["ready"])
    return state


@pytest.fixture
def recorded_peak(monkeypatch):
    state = {"peak": 12000}
    monkeypatch.setattr(settings_panel_module, "wav_peak", lambda path: state["peak"])
    return state


@pytest.fixture
def panel(qtbot, finalized_wav, recorded_peak):
    engine = _RecordingEngine()
    panel = SettingsPanel(engine)
    qtbot.addWidget(panel)
    return panel


def test_level_monitor_runs_only_while_panel_is_shown(panel):
    panel.show()
    assert panel.sip_engine.events[-1] == "monitor on"

    panel.hide()
    assert panel.sip_engine.events[-1] == "monitor off"


def test_mic_level_bar_follows_engine_level(panel):
    panel.sip_engine.level = 0.42
    panel._update_mic_level()

    assert panel.mic_level_bar.value() == 42


def test_echo_test_records_then_plays_back(panel):
    panel.echo_test_button.click()
    assert panel.sip_engine.events[-1] == "record"
    assert not panel.echo_test_button.isEnabled()
    assert panel.echo_test_status.text().startswith("Recording")

    panel._advance_echo_test()
    assert panel.sip_engine.events[-1] == "stop record"
    assert panel.echo_test_status.text().startswith("Preparing")

    panel._advance_echo_test()
    assert panel.sip_engine.events[-1] == "play"
    assert panel.echo_test_status.text().startswith("Playing")

    panel._advance_echo_test()
    assert "stop play" in panel.sip_engine.events
    assert panel.echo_test_button.isEnabled()
    assert panel.echo_test_status.text().startswith("Done")


def test_echo_test_waits_for_recorder_to_finish_file(panel, finalized_wav):
    finalized_wav["ready"] = False
    panel.echo_test_button.click()
    panel._advance_echo_test()  # stop recording

    panel._advance_echo_test()  # file not finished yet
    assert "play" not in panel.sip_engine.events
    assert panel.echo_test_status.text().startswith("Preparing")

    finalized_wav["ready"] = True
    panel._advance_echo_test()
    assert panel.sip_engine.events[-1] == "play"


def test_echo_test_gives_up_when_file_never_finishes(panel, finalized_wav):
    finalized_wav["ready"] = False
    panel.echo_test_button.click()
    panel._advance_echo_test()

    for _ in range(settings_panel_module._ECHO_FINALIZE_MAX_POLLS):
        panel._advance_echo_test()

    assert panel.echo_test_status.text() == "Test failed: the recording was not saved."
    assert panel.echo_test_button.isEnabled()


def test_silent_recording_warns_instead_of_playing(panel, recorded_peak):
    recorded_peak["peak"] = 13  # what a muted headset mic delivered
    panel.echo_test_button.click()
    panel._advance_echo_test()
    panel._advance_echo_test()

    assert "play" not in panel.sip_engine.events
    assert panel.echo_test_status.text() == "Recorded only silence - is the mic muted?"
    assert panel.echo_test_button.isEnabled()


def test_echo_test_failure_is_reported(panel):
    panel.sip_engine.fail_recording = True

    panel.echo_test_button.click()

    assert panel.echo_test_status.text() == "Test failed: no capture device"
    assert panel.echo_test_button.isEnabled()


def test_call_cancels_echo_test_and_disables_button(panel):
    panel.echo_test_button.click()

    panel.set_call_active(True)

    assert panel.echo_test_status.text() == "Test cancelled."
    assert not panel.echo_test_button.isEnabled()

    panel.set_call_active(False)
    assert panel.echo_test_button.isEnabled()


def test_hiding_panel_during_call_keeps_button_disabled(panel):
    panel.show()
    panel.set_call_active(True)
    panel.hide()

    assert not panel.echo_test_button.isEnabled()


@pytest.mark.parametrize(
    ("peak", "level"),
    [(0, 0.0), (32767, pytest.approx(1.0, abs=0.001)), (33, pytest.approx(0.0, abs=0.01)), (1036, pytest.approx(0.5, abs=0.01))],
)
def test_peak_to_level_uses_minus_60_to_0_dbfs(peak, level):
    assert peak_to_level(peak) == level
