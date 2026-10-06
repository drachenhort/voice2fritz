from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWizardPage,
)

from voice2fritz import config
from voice2fritz.i18n import tr
from voice2fritz.network import describe_address
from voice2fritz.registration import REGISTRATION_TIMEOUT_MS, classify_registration

DEFAULT_HOST = "fritz.box"

_GREEN = "#2fa84f"
_RED = "#d0453a"
_ORANGE = "#d08a2c"


class ConnectPage(QWizardPage):
    """Saves the IP phone account, registers, and reports the FRITZ!Box's answer inline."""

    def __init__(self, sip_engine, parent=None):
        super().__init__(parent)
        self.sip_engine = sip_engine
        self.setTitle(tr("Connect"))
        self.setSubTitle(tr("Enter the username and password of the IP phone you just created."))

        self.host_edit = QLineEdit()
        self.username_edit = QLineEdit()
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        existing_account = config.load_config()
        self.host_edit.setText(existing_account.host if existing_account is not None else DEFAULT_HOST)
        if existing_account is not None:
            self.username_edit.setText(existing_account.username)

        self.connect_button = QPushButton(tr("Connect"))
        self.connect_button.setObjectName("addButton")
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        self.vpn_label = QLabel()
        self.vpn_label.setWordWrap(True)
        self.vpn_label.setStyleSheet(f"color: {_ORANGE};")
        self.vpn_label.hide()

        form = QFormLayout()
        form.addRow(tr("Host"), self.host_edit)
        form.addRow(tr("Username"), self.username_edit)
        form.addRow(tr("Password"), self.password_edit)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.connect_button)
        layout.addWidget(self.status_label)
        layout.addWidget(self.vpn_label)
        layout.addStretch()

        self._connected = False
        # The account of the Connect press still waiting for an answer, else None.
        self._pending: config.AccountConfig | None = None
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(REGISTRATION_TIMEOUT_MS)
        self._timer.timeout.connect(self._on_timeout)

        for edit in (self.host_edit, self.username_edit, self.password_edit):
            edit.textChanged.connect(self._on_fields_changed)
        self.connect_button.clicked.connect(self._on_connect)
        sip_engine.registrationStateChanged.connect(self._on_registration_state_changed)
        self._update_connect_button()

    def host(self) -> str:
        return self.host_edit.text().strip() or DEFAULT_HOST

    def isComplete(self) -> bool:
        return self._connected

    def _fields_filled(self) -> bool:
        return all(edit.text().strip() for edit in (self.host_edit, self.username_edit, self.password_edit))

    def _update_connect_button(self) -> None:
        self.connect_button.setEnabled(self._fields_filled() and self._pending is None)

    def _set_status(self, text: str, color: str | None) -> None:
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color};" if color else "")

    def _set_connected(self, connected: bool) -> None:
        if connected != self._connected:
            self._connected = connected
            self.completeChanged.emit()

    def _on_fields_changed(self) -> None:
        # A shown result (or a pending one) no longer matches the fields.
        self._pending = None
        self._timer.stop()
        self._set_status("", None)
        self.vpn_label.hide()
        self._set_connected(False)
        self._update_connect_button()

    def _on_connect(self) -> None:
        cfg = config.AccountConfig(host=self.host_edit.text().strip(), username=self.username_edit.text().strip())
        password = self.password_edit.text()
        config.save_account(cfg, password)
        self.vpn_label.hide()
        self._set_connected(False)
        self._pending = cfg
        self._set_status(tr("Connecting..."), None)
        self._update_connect_button()
        self._timer.start()
        try:
            self.sip_engine.register(cfg.host, cfg.username, password)
        except Exception as exc:
            detail = getattr(exc, "reason", "") or str(exc)
            self._finish(self._could_not_connect(detail), _RED)

    def _on_registration_state_changed(self, text: str) -> None:
        if self._pending is None:
            return
        account = f"{self._pending.username}@{self._pending.host}"
        result = classify_registration(text)
        if result == "ok":
            self._finish(tr("Connected as {account}.", account=account), _GREEN)
            self._show_vpn_warning_if_needed()
            self._set_connected(True)
        elif result == "rejected":
            self._finish(
                tr("The FRITZ!Box rejected the login. Use the username and password of the IP phone, not the FRITZ!Box login."),
                _RED,
            )
        else:
            self._finish(self._could_not_connect(text), _RED)

    def _on_timeout(self) -> None:
        if self._pending is None:
            return
        host = self._pending.host
        self._finish(
            tr("No answer from {host}. Try 192.168.178.1, and check that this computer is not on the guest WLAN.", host=host),
            _RED,
        )

    def _could_not_connect(self, detail: str) -> str:
        return tr(
            "Could not connect: {detail}. Check the host, and that this computer is not on the guest WLAN.",
            detail=detail,
        )

    def _finish(self, text: str, color: str) -> None:
        self._pending = None
        self._timer.stop()
        self._set_status(text, color)
        self._update_connect_button()

    def _show_vpn_warning_if_needed(self) -> None:
        address = self.sip_engine.media_address
        if address is not None and describe_address(address).kind == "VPN":
            self.vpn_label.setText(
                tr("Call audio goes through the VPN; the FRITZ!Box may not reach it. Turn off the VPN and restart voice2fritz.")
            )
            self.vpn_label.show()
