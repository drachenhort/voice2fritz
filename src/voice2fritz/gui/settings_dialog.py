from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDialog, QVBoxLayout

from voice2fritz import config
from voice2fritz.gui.settings_panel import SettingsPanel


class SettingsDialog(QDialog):
    accountSaved = Signal(config.AccountConfig)

    def __init__(self, sip_engine, parent=None):
        super().__init__(parent)
        self.setWindowTitle("FRITZ!Box Account")

        self.panel = SettingsPanel(sip_engine)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.panel)

        self.panel.accountSaved.connect(self._on_account_saved)

        self.host_edit = self.panel.host_edit
        self.username_edit = self.panel.username_edit
        self.password_edit = self.panel.password_edit
        self.capture_combo = self.panel.capture_combo
        self.speaker_combo = self.panel.speaker_combo
        self.google_priority_checkbox = self.panel.google_priority_checkbox
        self.save_button = self.panel.save_button

    def _on_account_saved(self, cfg: config.AccountConfig) -> None:
        self.accountSaved.emit(cfg)
        self.accept()
