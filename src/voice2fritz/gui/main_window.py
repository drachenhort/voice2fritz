from datetime import datetime

from PySide6.QtCore import QRect, Qt, QTimer
from PySide6.QtGui import QAction, QColor, QFont, QPainter
from PySide6.QtWidgets import (
    QApplication,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from voice2fritz import call_log, config, contacts, ringtone
from voice2fritz.audio import restore_saved_devices
from voice2fritz.gui.call_details_panel import CallDetailsPanel
from voice2fritz.gui.call_log_panel import CallLogPanel
from voice2fritz.gui.contacts_panel import ContactsPanel
from voice2fritz.gui.incoming_call_popup import IncomingCallPopup
from voice2fritz.gui.nav_rail import NavRail
from voice2fritz.gui.settings_panel import SettingsPanel

_T9_LETTERS = {
    "1": "", "2": "ABC", "3": "DEF",
    "4": "GHI", "5": "JKL", "6": "MNO",
    "7": "PQRS", "8": "TUV", "9": "WXYZ",
    "*": "", "0": "+", "#": "",
}

_KEY_FLASH_MS = 120


class DialpadButton(QPushButton):
    """A keypad key that paints its T9 letters itself.

    text() stays the bare digit — send_dtmf reads it — so the letters can't
    live in the button text. They're painted into the strip that the QSS
    padding-bottom frees up under the digit.
    """

    def __init__(self, digit: str, letters: str, parent=None):
        super().__init__(digit, parent)
        self.letters = letters
        self.setObjectName("dialpadButton")
        if digit in ("*", "#"):
            self.setProperty("symbolKey", True)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if not self.letters:
            return

        painter = QPainter(self)
        font = self.font()
        font.setPixelSize(11)
        font.setBold(False)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.0)
        painter.setFont(font)
        painter.setPen(QColor("#ffffff" if self.isDown() else "#8a8f98"))

        strip = QRect(0, self.height() - 20, self.width(), 16)
        painter.drawText(strip, Qt.AlignmentFlag.AlignCenter, self.letters)
        painter.end()

    def flash(self) -> None:
        """Briefly show the pressed state, for keyboard-driven presses."""
        self.setDown(True)
        QTimer.singleShot(_KEY_FLASH_MS, self._clear_flash)

    def _clear_flash(self) -> None:
        self.setDown(False)


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

        self.digit_buttons: dict[str, DialpadButton] = {}
        dialpad_grid = QGridLayout()
        dialpad_grid.setHorizontalSpacing(6)
        dialpad_grid.setVerticalSpacing(6)
        dialpad_grid.setContentsMargins(0, 0, 0, 0)
        dialpad_rows = [
            ["1", "2", "3"],
            ["4", "5", "6"],
            ["7", "8", "9"],
            ["*", "0", "#"],
        ]
        for row, digits in enumerate(dialpad_rows):
            dialpad_grid.setRowStretch(row, 1)
            for col, digit in enumerate(digits):
                button = DialpadButton(digit, _T9_LETTERS[digit])
                button.setMinimumSize(64, 54)
                button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                button.clicked.connect(lambda checked=False, d=digit: self._on_digit_clicked(d))

                dialpad_grid.addWidget(button, row, col)
                self.digit_buttons[digit] = button
        for col in range(3):
            dialpad_grid.setColumnStretch(col, 1)

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

        dialpad_column = QVBoxLayout()
        dialpad_column.addLayout(number_row)
        dialpad_column.addLayout(dialpad_grid, 1)
        dialpad_column.addWidget(self.call_button)

        dialpad_page = QWidget()
        dialpad_page.setLayout(dialpad_column)

        self.log_panel = CallLogPanel()
        self.contacts_panel = ContactsPanel()
        self.settings_panel = SettingsPanel(self.sip_engine)

        self.pages = QStackedWidget()
        self.pages.addWidget(dialpad_page)
        self.pages.addWidget(self.contacts_panel)
        self.pages.addWidget(self.log_panel)
        self.pages.addWidget(self.settings_panel)

        self.nav_rail = NavRail()
        self.nav_rail.pageSelected.connect(self.pages.setCurrentIndex)

        self.log_panel.entryActivated.connect(self.number_edit.setText)
        self.contacts_panel.contactSelected.connect(self.number_edit.setText)
        self.settings_panel.accountSaved.connect(self._on_account_saved)

        self.sip_status_led = QLabel()
        self.sip_status_led.setFixedSize(14, 14)
        self._set_sip_status_led(is_ok=False, text="Not registered")

        status_row = QHBoxLayout()
        status_row.addWidget(self.sip_status_led)
        status_row.addStretch()

        self.call_details = CallDetailsPanel()
        self.call_bar = QWidget()
        self.call_bar.setObjectName("callBar")
        call_bar_row = QHBoxLayout(self.call_bar)
        call_bar_row.addWidget(self.call_details)
        call_bar_row.addStretch()
        call_bar_row.addWidget(self.hangup_button)
        call_bar_row.addWidget(self.mute_button)
        self.call_bar.setVisible(False)

        content_column = QVBoxLayout()
        content_column.addLayout(status_row)
        content_column.addWidget(self.call_bar)
        content_column.addWidget(self.pages, 1)

        body_row = QHBoxLayout()
        body_row.addWidget(self.nav_rail)
        body_row.addLayout(content_column, 1)

        container = QWidget()
        container.setLayout(body_row)
        self.setCentralWidget(container)

        self._connect_signals()
        restore_saved_devices(self.sip_engine)

        self._show_window_action = QAction("Show voice2fritz", self)
        self._show_window_action.triggered.connect(self._show_and_raise)
        self._quit_action = QAction("Quit", self)
        self._quit_action.triggered.connect(self._on_tray_quit)

        tray_menu = QMenu(self)
        tray_menu.addAction(self._show_window_action)
        tray_menu.addAction(self._quit_action)

        self.tray_icon = QSystemTrayIcon(self.windowIcon(), self)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _connect_signals(self) -> None:
        self.call_button.clicked.connect(self._on_call_clicked)
        self.hangup_button.clicked.connect(self._on_hangup_clicked)
        self.backspace_button.clicked.connect(self._on_backspace_clicked)
        self.mute_button.clicked.connect(self._on_mute_clicked)
        self.sip_engine.registrationStateChanged.connect(self._on_registration_state_changed)
        self.sip_engine.callStateChanged.connect(self._on_call_state_changed)
        self.sip_engine.callEnded.connect(self._on_call_ended)
        self.sip_engine.incomingCall.connect(self._on_incoming_call)

    def keyPressEvent(self, event) -> None:
        text = event.text()
        if text in self.digit_buttons:
            self.digit_buttons[text].flash()
            self._on_digit_clicked(text)
        else:
            super().keyPressEvent(event)

    def _show_and_raise(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    def _on_tray_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._show_and_raise()

    def _on_tray_quit(self) -> None:
        QApplication.instance().quit()

    def _show_close_dialog(self) -> str:
        box = QMessageBox(self)
        box.setWindowTitle("Close voice2fritz?")
        box.setText("Quit voice2fritz, or keep it running in the tray?")
        quit_button = box.addButton("Quit", QMessageBox.ButtonRole.AcceptRole)
        tray_button = box.addButton("Minimize to Tray", QMessageBox.ButtonRole.ActionRole)
        box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(tray_button)
        box.exec()
        clicked = box.clickedButton()
        if clicked is quit_button:
            return "quit"
        if clicked is tray_button:
            return "tray"
        return "cancel"

    def closeEvent(self, event) -> None:
        choice = self._show_close_dialog()
        if choice == "quit":
            event.accept()
            QApplication.instance().quit()
        elif choice == "tray":
            event.ignore()
            self.hide()
        else:
            event.ignore()

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
        number = self.number_edit.text().strip()
        if not number:
            return
        self._active_call = self.sip_engine.make_call(number)
        self._call_direction = "outgoing"
        self._call_number = number
        self._call_start_time = datetime.now()
        self.hangup_button.setEnabled(True)
        self.mute_button.setEnabled(True)
        self._set_dtmf_mode(True)
        self.call_bar.setVisible(True)

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
        self.call_bar.setVisible(False)
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
        self._show_and_raise()
        self._close_incoming_popup()
        self.sip_engine.answer(self._active_call)
        self.hangup_button.setEnabled(True)
        self.mute_button.setEnabled(True)
        self._set_dtmf_mode(True)
        self.call_bar.setVisible(True)
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

    def _on_account_saved(self, cfg: config.AccountConfig) -> None:
        password = config.get_password(cfg.username) or ""
        self.sip_engine.register(cfg.host, cfg.username, password)
