from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDialog, QFormLayout, QLineEdit, QPushButton, QVBoxLayout

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
        self.fritzbox_username_edit = QLineEdit()
        self.fritzbox_password_edit = QLineEdit()
        self.fritzbox_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.save_button = QPushButton("Save")

        form = QFormLayout()
        form.addRow("Host", self.host_edit)
        form.addRow("Username", self.username_edit)
        form.addRow("Password", self.password_edit)
        form.addRow("FritzBox Username", self.fritzbox_username_edit)
        form.addRow("FritzBox Password", self.fritzbox_password_edit)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.save_button)

        self.save_button.clicked.connect(self._on_save)

    def _on_save(self) -> None:
        cfg = config.AccountConfig(
            host=self.host_edit.text(),
            username=self.username_edit.text(),
        )
        config.save_config(cfg)
        config.set_password(cfg.username, self.password_edit.text())

        fritzbox_username = self.fritzbox_username_edit.text()
        if fritzbox_username:
            config.save_fritzbox_username(fritzbox_username)
            config.set_fritzbox_password(fritzbox_username, self.fritzbox_password_edit.text())

        self.accountSaved.emit(cfg)
        self.accept()
