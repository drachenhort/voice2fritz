import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QMessageBox

from voice2fritz import config as config_module
from voice2fritz.audio import AudioDevice
from voice2fritz.gui.main_window import MainWindow


@pytest.fixture(autouse=True)
def no_device_persistence(monkeypatch):
    monkeypatch.setattr(config_module, "load_device_selection", lambda path=config_module.DEFAULT_CONFIG_PATH: (None, None))
    monkeypatch.setattr(config_module, "save_device_selection", lambda capture, playback, path=config_module.DEFAULT_CONFIG_PATH: None)


class FakeSipEngine(QObject):
    registrationStateChanged = Signal(str)
    incomingCall = Signal(object)
    callStateChanged = Signal(str)
    callEnded = Signal()

    def __init__(self):
        super().__init__()
        self.calls_made = []
        self.hangups = []
        self.mutes = []
        self.answers = []
        self.registrations = []
        self.selected_capture = None
        self.selected_playback = None
        self.dtmf_sent = []

    def make_call(self, number):
        self.calls_made.append(number)
        return object()

    def hangup(self, call):
        self.hangups.append(call)

    def set_mute(self, call, muted):
        self.mutes.append((call, muted))

    def answer(self, call):
        self.answers.append(call)

    def register(self, host, username, password):
        self.registrations.append((host, username, password))

    def send_dtmf(self, call, digit):
        self.dtmf_sent.append((call, digit))

    def list_devices(self):
        return [
            AudioDevice(id=0, name="Built-in Mic", has_input=True, has_output=False),
            AudioDevice(id=1, name="Headset", has_input=True, has_output=True),
        ]

    def select_capture_device(self, device_id):
        self.selected_capture = device_id

    def select_playback_device(self, device_id):
        self.selected_playback = device_id


def test_device_combos_populated_from_engine(qtbot):
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    assert [window.capture_combo.itemText(i) for i in range(window.capture_combo.count())] == [
        "Built-in Mic",
        "Headset",
    ]
    assert [window.playback_combo.itemText(i) for i in range(window.playback_combo.count())] == ["Headset"]


def test_call_button_calls_engine_make_call_with_entered_number(qtbot):
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    window.number_edit.setText("01234567")
    window.call_button.click()

    assert engine.calls_made == ["01234567"]


def test_hangup_button_calls_engine_hangup(qtbot):
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    window.number_edit.setText("01234567")
    window.call_button.click()
    window.hangup_button.click()

    assert len(engine.hangups) == 1


def test_mute_button_toggles_engine_mute(qtbot):
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    window.number_edit.setText("01234567")
    window.call_button.click()
    active_call = window._active_call
    window.mute_button.click()

    assert engine.mutes == [(active_call, True)]


def test_dialpad_button_appends_digit_to_number_field(qtbot):
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    window.digit_buttons["1"].click()
    window.digit_buttons["2"].click()
    window.digit_buttons["*"].click()

    assert window.number_edit.text() == "12*"


def test_dialpad_button_appends_to_existing_text(qtbot):
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    window.number_edit.setText("030")
    window.digit_buttons["5"].click()

    assert window.number_edit.text() == "0305"


def test_keyboard_digit_appends_to_number_field(qtbot):
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    qtbot.keyClick(window, "1")
    qtbot.keyClick(window, "2")
    qtbot.keyClick(window, "*")

    assert window.number_edit.text() == "12*"


def test_keyboard_digit_sends_dtmf_during_active_call(qtbot):
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    window.number_edit.setText("01234567")
    window.call_button.click()
    active_call = window._active_call

    qtbot.keyClick(window, "7")

    assert engine.dtmf_sent == [(active_call, "7")]


def test_dialpad_button_sends_dtmf_during_active_call(qtbot):
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    window.number_edit.setText("01234567")
    window.call_button.click()
    active_call = window._active_call
    window.number_edit.clear()

    window.digit_buttons["5"].click()

    assert engine.dtmf_sent == [(active_call, "5")]
    assert window.number_edit.text() == ""


def test_dialpad_button_appends_to_field_after_call_ends(qtbot):
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    window.number_edit.setText("01234567")
    window.call_button.click()
    window.hangup_button.click()
    window.number_edit.clear()

    window.digit_buttons["9"].click()

    assert engine.dtmf_sent == []
    assert window.number_edit.text() == "9"


def test_digit_buttons_get_dtmf_mode_property_during_active_call(qtbot):
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    assert window.digit_buttons["1"].property("dtmfMode") in (None, False)

    window.number_edit.setText("01234567")
    window.call_button.click()

    assert window.digit_buttons["1"].property("dtmfMode") is True

    window.hangup_button.click()

    assert window.digit_buttons["1"].property("dtmfMode") is False


def test_registration_state_updates_status_label(qtbot):
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    engine.registrationStateChanged.emit("200 OK")

    assert window.status_label.text() == "200 OK"


def test_device_combo_selection_calls_engine(qtbot):
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    window.capture_combo.setCurrentIndex(1)

    assert engine.selected_capture == 1


def test_initial_device_selection_applied_at_startup(qtbot):
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    assert engine.selected_capture == window.capture_combo.itemData(0)
    assert engine.selected_playback == window.playback_combo.itemData(0)


def test_incoming_call_accept_answers_and_enables_controls(qtbot, monkeypatch):
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    incoming_call = object()
    engine.incomingCall.emit(incoming_call)

    assert engine.answers == [incoming_call]
    assert window._active_call is incoming_call
    assert window.hangup_button.isEnabled()
    assert window.mute_button.isEnabled()


def test_incoming_call_reject_hangs_up_and_resets_state(qtbot, monkeypatch):
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.No)
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    incoming_call = object()
    engine.incomingCall.emit(incoming_call)

    assert engine.hangups == [incoming_call]
    assert window._active_call is None
    assert not window.hangup_button.isEnabled()
    assert not window.mute_button.isEnabled()


def test_restores_saved_device_selection_on_startup(qtbot, monkeypatch):
    monkeypatch.setattr(config_module, "load_device_selection", lambda path=config_module.DEFAULT_CONFIG_PATH: ("Headset", "Headset"))

    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    assert window.capture_combo.currentText() == "Headset"
    assert window.playback_combo.currentText() == "Headset"
    assert engine.selected_capture == 1
    assert engine.selected_playback == 1


def test_device_selection_change_persists_choice(qtbot, monkeypatch):
    saved = []
    monkeypatch.setattr(
        config_module,
        "save_device_selection",
        lambda capture, playback, path=config_module.DEFAULT_CONFIG_PATH: saved.append((capture, playback)),
    )

    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)
    saved.clear()

    window.capture_combo.setCurrentIndex(1)

    assert saved == [("Headset", "Headset")]


def test_account_saved_triggers_reregistration(qtbot, monkeypatch):
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    monkeypatch.setattr(config_module, "get_password", lambda username: "secret")
    cfg = config_module.AccountConfig(host="fritz.box", username="user123")

    window._on_account_saved(cfg)

    assert engine.registrations == [("fritz.box", "user123", "secret")]
