from PySide6.QtCore import Signal
from PySide6.QtWidgets import QCheckBox, QDialog, QFormLayout, QLineEdit, QPushButton, QVBoxLayout

from voice2fritz import config


class SettingsDialog(QDialog):
    accountSaved = Signal(config.AccountConfig)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("FRITZ!Box Account")

        self.host_edit = QLineEdit()
        self.username_edit = QLineEdit()
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.save_button = QPushButton("Save")
        self.google_priority_checkbox = QCheckBox("Google sync overwrites local contacts with the same name")
        self.google_priority_checkbox.setChecked(True)

        form = QFormLayout()
        form.addRow("Host", self.host_edit)
        form.addRow("Username", self.username_edit)
        form.addRow("Password", self.password_edit)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.google_priority_checkbox)
        layout.addWidget(self.save_button)

        self.save_button.clicked.connect(self._on_save)

    def _on_save(self) -> None:
        cfg = config.AccountConfig(
            host=self.host_edit.text(),
            username=self.username_edit.text(),
        )
        config.save_config(cfg)
        config.set_password(cfg.username, self.password_edit.text())
        config.save_google_sync_overwrites_local(self.google_priority_checkbox.isChecked())
        self.accountSaved.emit(cfg)
        self.accept()
