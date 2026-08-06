from PySide6.QtCore import Signal
from PySide6.QtWidgets import QCheckBox, QComboBox, QFormLayout, QLineEdit, QPushButton, QVBoxLayout, QWidget

from voice2fritz import config
from voice2fritz.audio import populate_and_restore_devices


class SettingsPanel(QWidget):
    accountSaved = Signal(config.AccountConfig)

    def __init__(self, sip_engine, parent=None):
        super().__init__(parent)
        self.sip_engine = sip_engine

        self.host_edit = QLineEdit()
        self.username_edit = QLineEdit()
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.save_button = QPushButton("Save")
        self.save_button.setObjectName("addButton")
        self.google_priority_checkbox = QCheckBox("Google sync overwrites local contacts with the same name")
        self.google_priority_checkbox.setChecked(config.load_google_sync_overwrites_local())

        existing_account = config.load_config()
        if existing_account is not None:
            self.host_edit.setText(existing_account.host)
            self.username_edit.setText(existing_account.username)

        self.capture_combo = QComboBox()
        self.speaker_combo = QComboBox()

        form = QFormLayout()
        form.addRow("Host", self.host_edit)
        form.addRow("Username", self.username_edit)
        form.addRow("Password", self.password_edit)
        form.addRow("Mic", self.capture_combo)
        form.addRow("Speaker", self.speaker_combo)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.google_priority_checkbox)
        layout.addWidget(self.save_button)
        layout.addStretch()

        self.save_button.clicked.connect(self._on_save)

        populate_and_restore_devices(self.sip_engine, self.capture_combo, self.speaker_combo)

        self.capture_combo.currentIndexChanged.connect(self._on_capture_changed)
        self.speaker_combo.currentIndexChanged.connect(self._on_playback_changed)

    def _on_save(self) -> None:
        cfg = config.AccountConfig(
            host=self.host_edit.text(),
            username=self.username_edit.text(),
        )
        config.save_config(cfg)
        if self.password_edit.text():
            config.set_password(cfg.username, self.password_edit.text())
        config.save_google_sync_overwrites_local(self.google_priority_checkbox.isChecked())
        self.accountSaved.emit(cfg)

    def _on_capture_changed(self, index: int) -> None:
        if index >= 0:
            self.sip_engine.select_capture_device(self.capture_combo.itemData(index))
            self._save_device_selection()

    def _on_playback_changed(self, index: int) -> None:
        if index >= 0:
            self.sip_engine.select_playback_device(self.speaker_combo.itemData(index))
            self._save_device_selection()

    def _save_device_selection(self) -> None:
        capture_name = self.capture_combo.currentText() or None
        playback_name = self.speaker_combo.currentText() or None
        config.save_device_selection(capture_name, playback_name)
