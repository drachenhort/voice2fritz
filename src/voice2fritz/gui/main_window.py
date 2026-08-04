from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDockWidget,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from voice2fritz import call_log, config, contacts
from voice2fritz.audio import input_devices, output_devices
from voice2fritz.gui.call_log_panel import CallLogPanel
from voice2fritz.gui.contacts_dialog import ContactsDialog
from voice2fritz.gui.settings_dialog import SettingsDialog


class MainWindow(QMainWindow):
    def __init__(self, sip_engine, parent=None):
        super().__init__(parent)
        self.setWindowTitle("voice2fritz")
        self.sip_engine = sip_engine
        self._active_call = None
        self._call_direction: str | None = None
        self._call_number: str | None = None
        self._call_start_time: datetime | None = None

        self.number_edit = QLineEdit()
        self.number_edit.setAlignment(Qt.AlignmentFlag.AlignRight)

        self.digit_buttons: dict[str, QPushButton] = {}
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
                button.clicked.connect(lambda checked=False, d=digit: self._on_digit_clicked(d))
                dialpad_grid.addWidget(button, row, col)
                self.digit_buttons[digit] = button

        dialpad_column = QVBoxLayout()
        dialpad_column.addWidget(self.number_edit)
        dialpad_column.addLayout(dialpad_grid)

        self.call_button = QPushButton("📞")
        self.call_button.setObjectName("callButton")
        self.call_button.setToolTip("Call")
        self.hangup_button = QPushButton("✕")
        self.hangup_button.setToolTip("Hang up")
        self.hangup_button.setEnabled(False)
        self.mute_button = QPushButton("🔇")
        self.mute_button.setToolTip("Mute")
        self.mute_button.setCheckable(True)
        self.mute_button.setEnabled(False)
        self.settings_button = QPushButton("⚙")
        self.settings_button.setToolTip("Settings")
        self.contacts_button = QPushButton("Contacts")
        self.log_button = QPushButton("Log")

        controls_column = QVBoxLayout()
        controls_column.addWidget(self.call_button)
        controls_column.addWidget(self.hangup_button)
        controls_column.addWidget(self.mute_button)
        controls_column.addWidget(self.settings_button)
        controls_column.addWidget(self.contacts_button)
        controls_column.addWidget(self.log_button)

        top_row = QHBoxLayout()
        top_row.addLayout(dialpad_column)
        top_row.addLayout(controls_column)

        self.capture_combo = QComboBox()
        self.playback_combo = QComboBox()
        self.status_label = QLabel("Not registered")

        device_row = QHBoxLayout()
        device_row.addWidget(QLabel("Mic:"))
        device_row.addWidget(self.capture_combo)
        device_row.addWidget(QLabel("Speaker:"))
        device_row.addWidget(self.playback_combo)

        layout = QVBoxLayout()
        layout.addWidget(self.status_label)
        layout.addLayout(top_row)
        layout.addLayout(device_row)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self._populate_devices()
        self._connect_signals()
        self._restore_device_selection()

        self.log_panel = CallLogPanel()
        self.log_dock = QDockWidget("Call Log", self)
        self.log_dock.setWidget(self.log_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.log_dock)
        self.log_panel.entryActivated.connect(self.number_edit.setText)

    def _populate_devices(self) -> None:
        devices = self.sip_engine.list_devices()
        for device in input_devices(devices):
            self.capture_combo.addItem(device.name, device.id)
        for device in output_devices(devices):
            self.playback_combo.addItem(device.name, device.id)

    def _restore_device_selection(self) -> None:
        capture_name, playback_name = config.load_device_selection()

        if capture_name is not None:
            index = self.capture_combo.findText(capture_name)
            if index >= 0:
                self.capture_combo.setCurrentIndex(index)
        if self.capture_combo.count() > 0:
            self._on_capture_changed(self.capture_combo.currentIndex())

        if playback_name is not None:
            index = self.playback_combo.findText(playback_name)
            if index >= 0:
                self.playback_combo.setCurrentIndex(index)
        if self.playback_combo.count() > 0:
            self._on_playback_changed(self.playback_combo.currentIndex())

    def _connect_signals(self) -> None:
        self.call_button.clicked.connect(self._on_call_clicked)
        self.hangup_button.clicked.connect(self._on_hangup_clicked)
        self.mute_button.clicked.connect(self._on_mute_clicked)
        self.capture_combo.currentIndexChanged.connect(self._on_capture_changed)
        self.playback_combo.currentIndexChanged.connect(self._on_playback_changed)
        self.sip_engine.registrationStateChanged.connect(self.status_label.setText)
        self.sip_engine.callStateChanged.connect(self.status_label.setText)
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

    def _set_dtmf_mode(self, enabled: bool) -> None:
        for button in self.digit_buttons.values():
            button.setProperty("dtmfMode", enabled)
            button.style().unpolish(button)
            button.style().polish(button)

    def _on_call_clicked(self) -> None:
        number = self.number_edit.text()
        self._active_call = self.sip_engine.make_call(number)
        self._call_direction = "outgoing"
        self._call_number = number
        self._call_start_time = datetime.now()
        self.hangup_button.setEnabled(True)
        self.mute_button.setEnabled(True)
        self._set_dtmf_mode(True)

    def _on_hangup_clicked(self) -> None:
        if self._active_call is not None:
            self.sip_engine.hangup(self._active_call)
        self._on_call_ended()

    def _on_mute_clicked(self) -> None:
        if self._active_call is not None:
            self.sip_engine.set_mute(self._active_call, self.mute_button.isChecked())

    def _on_call_ended(self) -> None:
        self._active_call = None
        self.hangup_button.setEnabled(False)
        self.mute_button.setEnabled(False)
        self.mute_button.setChecked(False)
        self._set_dtmf_mode(False)
        self._log_completed_call()

    def _log_completed_call(self) -> None:
        if self._call_direction is None:
            return
        duration = 0
        if self._call_direction != "missed" and self._call_start_time is not None:
            duration = int((datetime.now() - self._call_start_time).total_seconds())
        name = ""
        for contact in contacts.load_contacts():
            if contact.number == self._call_number:
                name = contact.name
                break
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
        self._active_call = call
        self._call_direction = "incoming"
        self._call_number = self.sip_engine.get_remote_number(call)
        self._call_start_time = datetime.now()
        answer = QMessageBox.question(
            self,
            "Incoming call",
            "Incoming call. Answer?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.sip_engine.answer(self._active_call)
            self.hangup_button.setEnabled(True)
            self.mute_button.setEnabled(True)
            self._set_dtmf_mode(True)
        else:
            self._call_direction = "missed"
            self.sip_engine.hangup(self._active_call)
            self._on_call_ended()

    def _on_settings_clicked(self) -> None:
        dialog = SettingsDialog(self)
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

    def _on_capture_changed(self, index: int) -> None:
        if index >= 0:
            self.sip_engine.select_capture_device(self.capture_combo.itemData(index))
            self._save_device_selection()

    def _on_playback_changed(self, index: int) -> None:
        if index >= 0:
            self.sip_engine.select_playback_device(self.playback_combo.itemData(index))
            self._save_device_selection()

    def _save_device_selection(self) -> None:
        capture_name = self.capture_combo.currentText() or None
        playback_name = self.playback_combo.currentText() or None
        config.save_device_selection(capture_name, playback_name)
