from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDockWidget,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from voice2fritz import call_log, config, contacts, ringtone
from voice2fritz.audio import restore_saved_devices
from voice2fritz.gui.call_details_panel import CallDetailsPanel
from voice2fritz.gui.call_log_panel import CallLogPanel
from voice2fritz.gui.contacts_dialog import ContactsDialog
from voice2fritz.gui.incoming_call_popup import IncomingCallPopup
from voice2fritz.gui.settings_dialog import SettingsDialog

_T9_LETTERS = {
    "1": "", "2": "ABC", "3": "DEF",
    "4": "GHI", "5": "JKL", "6": "MNO",
    "7": "PQRS", "8": "TUV", "9": "WXYZ",
    "*": "", "0": "+", "#": "",
}


class MainWindow(QMainWindow):
    def __init__(self, sip_engine, parent=None):
        super().__init__(parent)
        self.setWindowTitle("voice2fritz")
        self.sip_engine = sip_engine
        self._active_call = None
        self._call_direction: str | None = None
        self._call_number: str | None = None
        self._call_start_time: datetime | None = None
        self.incoming_popup: IncomingCallPopup | None = None

        self.number_edit = QLineEdit()
        self.number_edit.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.backspace_button = QPushButton("⌫")
        self.backspace_button.setToolTip("Backspace")

        number_row = QHBoxLayout()
        number_row.addWidget(self.number_edit)
        number_row.addWidget(self.backspace_button)

        self.digit_buttons: dict[str, QPushButton] = {}
        self.digit_letter_labels: dict[str, QLabel] = {}
        dialpad_grid = QGridLayout()
        dialpad_rows = [
            ["1", "2", "3"],
            ["4", "5", "6"],
            ["7", "8", "9"],
            ["*", "0", "#"],
        ]
        for row, digits in enumerate(dialpad_rows):
            for col, digit in enumerate(digits):
                button = QPushButton(digit)
                button.setObjectName("dialpadButton")
                button.clicked.connect(lambda checked=False, d=digit: self._on_digit_clicked(d))

                letters_label = QLabel(_T9_LETTERS[digit])
                letters_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                letters_label.setStyleSheet("color: #8a8f98; font-size: 11px;")

                cell = QVBoxLayout()
                cell.setSpacing(0)
                cell.addWidget(button)
                cell.addWidget(letters_label)
                cell_widget = QWidget()
                cell_widget.setLayout(cell)

                dialpad_grid.addWidget(cell_widget, row, col)
                self.digit_buttons[digit] = button
                self.digit_letter_labels[digit] = letters_label

        self.call_button = QPushButton("📞 CALL")
        self.call_button.setObjectName("callButton")
        self.call_button.setToolTip("Call")

        self.hangup_button = QPushButton("✕ Hangup")
        self.hangup_button.setObjectName("navButton")
        self.hangup_button.setToolTip("Hang up")
        self.hangup_button.setEnabled(False)
        self.mute_button = QPushButton("🔇 Mute")
        self.mute_button.setObjectName("navButton")
        self.mute_button.setToolTip("Mute")
        self.mute_button.setCheckable(True)
        self.mute_button.setEnabled(False)

        call_control_row = QHBoxLayout()
        call_control_row.addWidget(self.hangup_button)
        call_control_row.addWidget(self.mute_button)

        dialpad_column = QVBoxLayout()
        dialpad_column.addLayout(number_row)
        dialpad_column.addLayout(dialpad_grid)
        dialpad_column.addWidget(self.call_button)
        dialpad_column.addLayout(call_control_row)

        self.settings_button = QPushButton("⚙ Settings")
        self.settings_button.setObjectName("navButton")
        self.settings_button.setToolTip("Settings")
        self.contacts_button = QPushButton("Contacts")
        self.contacts_button.setObjectName("navButton")
        self.log_button = QPushButton("Log")
        self.log_button.setObjectName("navButton")

        nav_row = QHBoxLayout()
        nav_row.addWidget(self.settings_button)
        nav_row.addWidget(self.contacts_button)
        nav_row.addWidget(self.log_button)

        self.sip_status_led = QLabel()
        self.sip_status_led.setFixedSize(14, 14)
        self._set_sip_status_led(is_ok=False, text="Not registered")

        status_row = QHBoxLayout()
        status_row.addWidget(self.sip_status_led)
        status_row.addStretch()

        layout = QVBoxLayout()
        layout.addLayout(status_row)
        layout.addLayout(nav_row)
        layout.addLayout(dialpad_column)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.call_details = CallDetailsPanel()
        self.call_details_dock = QDockWidget("Call Details", self)
        self.call_details_dock.setWidget(self.call_details)
        self.call_details_dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        self.call_details_dock.setFixedWidth(260)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.call_details_dock)

        self.log_panel = CallLogPanel()
        self.log_dock = QDockWidget("Call Log", self)
        self.log_dock.setWidget(self.log_panel)
        self.log_dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        self.log_dock.setFixedWidth(260)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.log_dock)
        self.log_panel.entryActivated.connect(self.number_edit.setText)

        self._connect_signals()
        restore_saved_devices(self.sip_engine)

    def _connect_signals(self) -> None:
        self.call_button.clicked.connect(self._on_call_clicked)
        self.hangup_button.clicked.connect(self._on_hangup_clicked)
        self.backspace_button.clicked.connect(self._on_backspace_clicked)
        self.mute_button.clicked.connect(self._on_mute_clicked)
        self.sip_engine.registrationStateChanged.connect(self._on_registration_state_changed)
        self.sip_engine.callStateChanged.connect(self._on_call_state_changed)
        self.sip_engine.callEnded.connect(self._on_call_ended)
        self.sip_engine.incomingCall.connect(self._on_incoming_call)
        self.settings_button.clicked.connect(self._on_settings_clicked)
        self.contacts_button.clicked.connect(self._on_contacts_clicked)
        self.log_button.clicked.connect(self._on_log_clicked)

    def keyPressEvent(self, event) -> None:
        text = event.text()
        if text in self.digit_buttons:
            self._on_digit_clicked(text)
        else:
            super().keyPressEvent(event)

    def _on_digit_clicked(self, digit: str) -> None:
        if self._active_call is not None:
            self.sip_engine.send_dtmf(self._active_call, digit)
        else:
            self.number_edit.setText(self.number_edit.text() + digit)

    def _on_backspace_clicked(self) -> None:
        self.number_edit.setText(self.number_edit.text()[:-1])

    def _set_sip_status_led(self, is_ok: bool, text: str) -> None:
        color = "#2fa84f" if is_ok else "#a83b2f"
        self.sip_status_led.setStyleSheet(f"background-color: {color}; border-radius: 7px;")
        self.sip_status_led.setToolTip(text)

    def _on_registration_state_changed(self, text: str) -> None:
        self._set_sip_status_led(is_ok=(text == "200 OK"), text=text)

    def _on_call_state_changed(self, text: str) -> None:
        self.call_details.set_state_text(text)

    def _set_dtmf_mode(self, enabled: bool) -> None:
        for button in self.digit_buttons.values():
            button.setProperty("dtmfMode", enabled)
            button.style().unpolish(button)
            button.style().polish(button)

    def _contact_name_for(self, number: str | None) -> str:
        for contact in contacts.load_contacts():
            if contact.number == number:
                return contact.name
        return ""

    def _on_call_clicked(self) -> None:
        number = self.number_edit.text()
        self._active_call = self.sip_engine.make_call(number)
        self._call_direction = "outgoing"
        self._call_number = number
        self._call_start_time = datetime.now()
        self.hangup_button.setEnabled(True)
        self.mute_button.setEnabled(True)
        self._set_dtmf_mode(True)

        name = self._contact_name_for(number)
        self.call_details.set_active_call(name, number)

    def _on_hangup_clicked(self) -> None:
        if self._active_call is not None:
            self.sip_engine.hangup(self._active_call)
        self._on_call_ended()

    def _on_mute_clicked(self) -> None:
        if self._active_call is not None:
            self.sip_engine.set_mute(self._active_call, self.mute_button.isChecked())

    def _on_call_ended(self) -> None:
        if self.incoming_popup is not None:
            self._close_incoming_popup()
            if self._call_direction == "incoming":
                self._call_direction = "missed"
        self._active_call = None
        self.hangup_button.setEnabled(False)
        self.mute_button.setEnabled(False)
        self.mute_button.setChecked(False)
        self._set_dtmf_mode(False)
        self.call_details.set_idle()
        self._log_completed_call()

    def _log_completed_call(self) -> None:
        if self._call_direction is None:
            return
        duration = 0
        if self._call_direction != "missed" and self._call_start_time is not None:
            duration = int((datetime.now() - self._call_start_time).total_seconds())
        name = self._contact_name_for(self._call_number)
        entry = call_log.CallLogEntry(
            number=self._call_number or "",
            name=name,
            direction=self._call_direction,
            timestamp=datetime.now().isoformat(),
            duration_seconds=duration,
        )
        call_log.append_call_log_entry(entry)
        self.log_panel._reload_list()
        self._call_direction = None
        self._call_number = None
        self._call_start_time = None

    def _on_incoming_call(self, call) -> None:
        if self.incoming_popup is not None:
            self._close_incoming_popup()
        self._active_call = call
        self._call_direction = "incoming"
        self._call_number = self.sip_engine.get_remote_number(call)
        self._call_start_time = datetime.now()

        name = self._contact_name_for(self._call_number)
        self.incoming_popup = IncomingCallPopup(name, self._call_number or "")
        self.incoming_popup.answered.connect(self._on_incoming_call_answered)
        self.incoming_popup.declined.connect(self._on_incoming_call_declined)
        ringtone.play_ringtone()
        self.incoming_popup.show()

    def _on_incoming_call_answered(self) -> None:
        self._close_incoming_popup()
        self.sip_engine.answer(self._active_call)
        self.hangup_button.setEnabled(True)
        self.mute_button.setEnabled(True)
        self._set_dtmf_mode(True)
        name = self._contact_name_for(self._call_number)
        self.call_details.set_active_call(name, self._call_number or "")

    def _on_incoming_call_declined(self) -> None:
        self._close_incoming_popup()
        self._call_direction = "missed"
        self.sip_engine.decline(self._active_call)
        self._on_call_ended()

    def _close_incoming_popup(self) -> None:
        ringtone.stop_ringtone()
        popup = self.incoming_popup
        self.incoming_popup = None
        if popup is not None:
            popup.close()
            popup.setParent(self)
            popup.deleteLater()

    def _on_settings_clicked(self) -> None:
        dialog = SettingsDialog(self.sip_engine, self)
        dialog.accountSaved.connect(self._on_account_saved)
        dialog.exec()

    def _on_contacts_clicked(self) -> None:
        dialog = ContactsDialog(self)
        dialog.contactSelected.connect(self.number_edit.setText)
        dialog.exec()

    def _on_log_clicked(self) -> None:
        self.log_dock.setVisible(not self.log_dock.isVisible())

    def _on_account_saved(self, cfg: config.AccountConfig) -> None:
        password = config.get_password(cfg.username) or ""
        self.sip_engine.register(cfg.host, cfg.username, password)
