import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QDockWidget

from voice2fritz import call_log as call_log_module
from voice2fritz import config as config_module
from voice2fritz import contacts as contacts_module
from voice2fritz import ringtone
from voice2fritz.audio import AudioDevice
from voice2fritz.gui.main_window import MainWindow


@pytest.fixture(autouse=True)
def no_device_persistence(monkeypatch):
    monkeypatch.setattr(config_module, "load_device_selection", lambda path=config_module.DEFAULT_CONFIG_PATH: (None, None))
    monkeypatch.setattr(config_module, "save_device_selection", lambda capture, playback, path=config_module.DEFAULT_CONFIG_PATH: None)


@pytest.fixture(autouse=True)
def no_ringtone_playback(monkeypatch):
    monkeypatch.setattr(ringtone, "play_ringtone", lambda: None)
    monkeypatch.setattr(ringtone, "stop_ringtone", lambda: None)


@pytest.fixture(autouse=True)
def no_call_log_persistence(monkeypatch):
    monkeypatch.setattr(call_log_module, "append_call_log_entry", lambda entry, path=call_log_module.DEFAULT_CALL_LOG_PATH: None)
    monkeypatch.setattr(contacts_module, "load_contacts", lambda path=contacts_module.DEFAULT_CONTACTS_PATH: [])


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
        self.remote_number = "+4917600000000"

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

    def get_remote_number(self, call):
        return self.remote_number

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
    assert [window.call_details.speaker_combo.itemText(i) for i in range(window.call_details.speaker_combo.count())] == ["Headset"]


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
    window.call_details.mute_button.click()

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

    assert window.sip_status_label.text() == "SIP Status: 200 OK"


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
    assert engine.selected_playback == window.call_details.speaker_combo.itemData(0)


def test_incoming_call_accept_answers_and_enables_controls(qtbot):
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    incoming_call = object()
    engine.incomingCall.emit(incoming_call)
    assert window.incoming_popup is not None

    window.incoming_popup.answered.emit()

    assert engine.answers == [incoming_call]
    assert window._active_call is incoming_call
    assert window.hangup_button.isEnabled()
    assert window.call_details.mute_button.isEnabled()
    assert window.call_details.name_label.text() == engine.remote_number
    assert window.incoming_popup is None


def test_incoming_call_reject_hangs_up_and_resets_state(qtbot):
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    incoming_call = object()
    engine.incomingCall.emit(incoming_call)
    window.incoming_popup.declined.emit()

    assert engine.hangups == [incoming_call]
    assert window._active_call is None
    assert not window.hangup_button.isEnabled()
    assert not window.call_details.mute_button.isEnabled()
    assert window.incoming_popup is None


def test_restores_saved_device_selection_on_startup(qtbot, monkeypatch):
    monkeypatch.setattr(config_module, "load_device_selection", lambda path=config_module.DEFAULT_CONFIG_PATH: ("Headset", "Headset"))

    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    assert window.capture_combo.currentText() == "Headset"
    assert window.call_details.speaker_combo.currentText() == "Headset"
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


def test_contacts_button_opens_dialog_and_fills_number_on_selection(qtbot, monkeypatch):
    from PySide6.QtCore import QObject, Signal

    class FakeContactsDialogQt(QObject):
        contactSelected = Signal(str)

        def __init__(self, parent=None):
            super().__init__()
            FakeContactsDialogQt.last_instance = self

        def exec(self):
            return None

    monkeypatch.setattr("voice2fritz.gui.main_window.ContactsDialog", FakeContactsDialogQt)

    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    window.contacts_button.click()

    assert FakeContactsDialogQt.last_instance is not None

    FakeContactsDialogQt.last_instance.contactSelected.emit("+4917612345678")

    assert window.number_edit.text() == "+4917612345678"


def test_account_saved_triggers_reregistration(qtbot, monkeypatch):
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    monkeypatch.setattr(config_module, "get_password", lambda username: "secret")
    cfg = config_module.AccountConfig(host="fritz.box", username="user123")

    window._on_account_saved(cfg)

    assert engine.registrations == [("fritz.box", "user123", "secret")]
    assert window.account_label.text() == "Account: fritz.box"


def test_completed_outgoing_call_appends_log_entry(qtbot, monkeypatch):
    logged = []
    monkeypatch.setattr(call_log_module, "append_call_log_entry", lambda entry, path=call_log_module.DEFAULT_CALL_LOG_PATH: logged.append(entry))

    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    window.number_edit.setText("+4917612345678")
    window.call_button.click()
    window.hangup_button.click()

    assert len(logged) == 1
    assert logged[0].number == "+4917612345678"
    assert logged[0].direction == "outgoing"
    assert logged[0].duration_seconds >= 0


def test_accepted_incoming_call_appends_log_entry(qtbot, monkeypatch):
    logged = []
    monkeypatch.setattr(call_log_module, "append_call_log_entry", lambda entry, path=call_log_module.DEFAULT_CALL_LOG_PATH: logged.append(entry))

    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    incoming_call = object()
    engine.incomingCall.emit(incoming_call)
    window.incoming_popup.answered.emit()
    window.hangup_button.click()

    assert len(logged) == 1
    assert logged[0].number == engine.remote_number
    assert logged[0].direction == "incoming"


def test_rejected_incoming_call_appends_missed_log_entry(qtbot, monkeypatch):
    logged = []
    monkeypatch.setattr(call_log_module, "append_call_log_entry", lambda entry, path=call_log_module.DEFAULT_CALL_LOG_PATH: logged.append(entry))

    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    incoming_call = object()
    engine.incomingCall.emit(incoming_call)
    window.incoming_popup.declined.emit()

    assert len(logged) == 1
    assert logged[0].number == engine.remote_number
    assert logged[0].direction == "missed"
    assert logged[0].duration_seconds == 0


def test_incoming_call_auto_dismisses_popup_on_remote_hangup(qtbot, monkeypatch):
    stopped = []
    monkeypatch.setattr(ringtone, "stop_ringtone", lambda: stopped.append(True))
    logged = []
    monkeypatch.setattr(call_log_module, "append_call_log_entry", lambda entry, path=call_log_module.DEFAULT_CALL_LOG_PATH: logged.append(entry))

    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    incoming_call = object()
    engine.incomingCall.emit(incoming_call)
    assert window.incoming_popup is not None

    engine.callEnded.emit()

    assert window.incoming_popup is None
    assert stopped == [True]
    assert len(logged) == 1
    assert logged[0].direction == "missed"


def test_second_incoming_call_replaces_first_pending_popup(qtbot, monkeypatch):
    stop_calls = []
    play_calls = []
    monkeypatch.setattr(ringtone, "stop_ringtone", lambda: stop_calls.append(True))
    monkeypatch.setattr(ringtone, "play_ringtone", lambda: play_calls.append(True))

    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    first_call = object()
    engine.remote_number = "+4917600000000"
    engine.incomingCall.emit(first_call)
    first_popup = window.incoming_popup
    assert first_popup is not None
    assert play_calls == [True]

    second_call = object()
    engine.remote_number = "+4917699999999"
    engine.incomingCall.emit(second_call)

    assert window.incoming_popup is not None
    assert window.incoming_popup is not first_popup
    assert window._active_call is second_call
    assert window._call_number == "+4917699999999"
    # stop_ringtone for the first call must happen before the second play_ringtone
    assert stop_calls == [True]
    assert play_calls == [True, True]


def test_call_log_entry_uses_matching_contact_name(qtbot, monkeypatch):
    monkeypatch.setattr(
        contacts_module,
        "load_contacts",
        lambda path=contacts_module.DEFAULT_CONTACTS_PATH: [contacts_module.Contact(name="Anna Schmidt", number="+4917612345678")],
    )
    logged = []
    monkeypatch.setattr(call_log_module, "append_call_log_entry", lambda entry, path=call_log_module.DEFAULT_CALL_LOG_PATH: logged.append(entry))

    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    window.number_edit.setText("+4917612345678")
    window.call_button.click()
    window.hangup_button.click()

    assert logged[0].name == "Anna Schmidt"


def test_log_button_toggles_dock_visibility(qtbot):
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)
    window.show()

    assert window.log_dock.isVisible()

    window.log_button.click()
    assert not window.log_dock.isVisible()

    window.log_button.click()
    assert window.log_dock.isVisible()


def test_log_panel_entry_activated_fills_number_field(qtbot):
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    window.log_panel.entryActivated.emit("+4917612345678")

    assert window.number_edit.text() == "+4917612345678"


def test_completing_a_call_refreshes_log_panel_live(qtbot, monkeypatch):
    logged_entries = []

    def fake_append(entry, path=call_log_module.DEFAULT_CALL_LOG_PATH):
        logged_entries.append(entry)

    monkeypatch.setattr(call_log_module, "append_call_log_entry", fake_append)
    monkeypatch.setattr(call_log_module, "load_call_log", lambda path=call_log_module.DEFAULT_CALL_LOG_PATH: logged_entries)

    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)
    assert window.log_panel.entry_list.count() == 0

    window.number_edit.setText("+4917612345678")
    window.call_button.click()
    window.hangup_button.click()

    assert window.log_panel.entry_list.count() == 1


def test_backspace_button_removes_last_character(qtbot):
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    window.number_edit.setText("0123")
    window.backspace_button.click()

    assert window.number_edit.text() == "012"


def test_set_account_host_updates_account_label(qtbot):
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    window.set_account_host("fritz.box")

    assert window.account_label.text() == "Account: fritz.box"


def test_outgoing_call_updates_call_details_panel(qtbot):
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    window.number_edit.setText("+4917612345678")
    window.call_button.click()

    assert window.call_details.name_label.text() == "+4917612345678"
    assert window.call_details.state_label.text() == "Active"

    window.hangup_button.click()

    assert window.call_details.name_label.text() == "No active call"


def test_call_details_docks_stacked_on_left(qtbot):
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)
    window.show()

    from PySide6.QtCore import Qt

    assert window.dockWidgetArea(window.call_details_dock) == Qt.DockWidgetArea.LeftDockWidgetArea
    assert window.dockWidgetArea(window.log_dock) == Qt.DockWidgetArea.LeftDockWidgetArea


def test_call_details_dock_is_not_closable(qtbot):
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    assert not (window.call_details_dock.features() & QDockWidget.DockWidgetFeature.DockWidgetClosable)


def test_t9_letters_match_mapping(qtbot):
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    expected = {
        "1": "", "2": "ABC", "3": "DEF",
        "4": "GHI", "5": "JKL", "6": "MNO",
        "7": "PQRS", "8": "TUV", "9": "WXYZ",
        "*": "", "0": "+", "#": "",
    }
    for digit, letters in expected.items():
        assert window.digit_letter_labels[digit].text() == letters
