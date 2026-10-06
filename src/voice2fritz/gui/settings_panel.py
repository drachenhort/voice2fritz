from PySide6.QtCore import QLocale, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from voice2fritz import config
from voice2fritz.gui.audio_setup_widget import AudioSetupWidget
from voice2fritz.network import describe_address
from voice2fritz.i18n import LANGUAGES, language_from_locale, tr


class SettingsPanel(QWidget):
    accountSaved = Signal(config.AccountConfig)
    languageChanged = Signal(str)

    def __init__(self, sip_engine, parent=None):
        super().__init__(parent)
        self.sip_engine = sip_engine

        self.host_edit = QLineEdit()
        self.username_edit = QLineEdit()
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        # None until the FRITZ!Box has answered a registration with the saved password.
        self._password_status: str | None = None
        self.save_button = QPushButton(tr("Save"))
        self.save_button.setObjectName("addButton")
        self.google_priority_checkbox = QCheckBox(tr("Google sync overwrites local contacts with the same name"))
        self.google_priority_checkbox.setChecked(config.load_google_sync_overwrites_local())

        existing_account = config.load_config()
        if existing_account is not None:
            self.host_edit.setText(existing_account.host)
            self.username_edit.setText(existing_account.username)

        self.audio = AudioSetupWidget(sip_engine)
        # The audio controls used to live here; keep their names for callers.
        self.capture_combo = self.audio.capture_combo
        self.speaker_combo = self.audio.speaker_combo
        self.mic_level_bar = self.audio.mic_level_bar
        self.echo_test_button = self.audio.echo_test_button
        self.echo_test_status = self.audio.echo_test_status

        account_form = QFormLayout()
        account_form.addRow(tr("Host"), self.host_edit)
        account_form.addRow(tr("Username"), self.username_edit)
        account_form.addRow(tr("Password"), self.password_edit)

        self.call_audio_ip_label = QLabel()
        self.language_combo = QComboBox()
        for code, label in LANGUAGES.items():
            self.language_combo.addItem(label, code)
        self.language_combo.setCurrentIndex(max(0, self.language_combo.findData(config.load_language())))

        other_form = QFormLayout()
        other_form.addRow(tr("Call audio IP"), self.call_audio_ip_label)
        other_form.addRow(tr("Language"), self.language_combo)

        layout = QVBoxLayout(self)
        layout.addLayout(account_form)
        layout.addWidget(self.audio)
        layout.addLayout(other_form)
        layout.addWidget(self.google_priority_checkbox)
        layout.addWidget(self.save_button)
        layout.addStretch()

        self.save_button.clicked.connect(self._on_save)

        self.username_edit.textChanged.connect(self._update_password_hint)
        self._update_password_hint()

        self.language_combo.currentIndexChanged.connect(self._on_language_changed)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.update_call_audio_ip()

    def update_call_audio_ip(self) -> None:
        address = self.sip_engine.media_address
        if address is None:
            self.call_audio_ip_label.setText(tr("Not registered yet"))
            self.call_audio_ip_label.setStyleSheet("color: #8a8f98;")
            self.call_audio_ip_label.setToolTip("")
            return
        info = describe_address(address)
        if info.interface is None:
            # Network type is only known where interfaces can be inspected (Linux).
            self.call_audio_ip_label.setText(info.address)
        else:
            self.call_audio_ip_label.setText(f"{info.address} - {tr(info.kind)} ({info.interface})")
        if info.kind == "VPN":
            # The FRITZ!Box is on the LAN; audio routed through a VPN usually doesn't arrive.
            self.call_audio_ip_label.setStyleSheet("color: #d08a2c;")
            self.call_audio_ip_label.setToolTip(tr("Call audio goes through the VPN; the FRITZ!Box may not reach it."))
        else:
            self.call_audio_ip_label.setStyleSheet("")
            self.call_audio_ip_label.setToolTip(tr("Local address the FRITZ!Box sends call audio to."))

    def set_call_active(self, active: bool) -> None:
        self.audio.set_call_active(active)
        # Switching language restarts the app, which would drop the call.
        self.language_combo.setEnabled(not active)
        self.language_combo.setToolTip(tr("Not available during a call") if active else "")

    def _on_save(self) -> None:
        cfg = config.AccountConfig(
            host=self.host_edit.text(),
            username=self.username_edit.text(),
        )
        config.save_account(cfg, self.password_edit.text())
        # Never leave the password on screen; the hint reports its status instead.
        self.password_edit.clear()
        self._password_status = None
        self._update_password_hint()
        config.save_google_sync_overwrites_local(self.google_priority_checkbox.isChecked())
        self.accountSaved.emit(cfg)
        # Saving re-registers, which may pick a different local address.
        self.update_call_audio_ip()

    def set_registration_result(self, status: str | None) -> None:
        """Report how the FRITZ!Box answered the saved password: "ok", "rejected" or None (unknown)."""
        self._password_status = status
        self._update_password_hint()

    def _update_password_hint(self) -> None:
        username = self.username_edit.text()
        saved = bool(username) and bool(config.get_password(username))
        if not saved:
            hint, color = tr("No password saved"), None
        elif self._password_status == "ok":
            hint, color = tr("Password tested and working"), "#2fa84f"
        elif self._password_status == "rejected":
            hint, color = tr("Saved password was rejected - enter it again"), "#d0453a"
        else:
            hint, color = tr("Password saved (not tested yet)"), None
        self.password_edit.setPlaceholderText(hint)
        # A palette colour would lose against the app stylesheet; set it in QSS instead.
        self.password_edit.setStyleSheet(f"QLineEdit {{ placeholder-text-color: {color}; }}" if color else "")

    def _on_language_changed(self, index: int) -> None:
        language = self.language_combo.itemData(index)
        config.save_language(language)
        system_language = language_from_locale(QLocale.system().name())
        if language != system_language:
            # A deliberate choice against the system language: don't offer it at startup.
            config.save_declined_system_language(system_language)
        self.languageChanged.emit(language)
