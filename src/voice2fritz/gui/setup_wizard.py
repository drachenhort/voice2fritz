from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWizard,
    QWizardPage,
)

from voice2fritz import config
from voice2fritz.gui.audio_setup_widget import AudioSetupWidget
from voice2fritz.i18n import current_language, tr
from voice2fritz.network import describe_address
from voice2fritz.registration import REGISTRATION_TIMEOUT_MS, classify_registration

DEFAULT_HOST = "fritz.box"

_GREEN = "#2fa84f"
_RED = "#d0453a"
_ORANGE = "#d08a2c"
_GUIDE_BASE_URL = "https://github.com/drachenhort/voice2fritz/blob/master/docs/"


def guide_url() -> str:
    """Troubleshooting section of the FRITZ!Box setup guide, in the UI language."""
    if current_language() == "de":
        return _GUIDE_BASE_URL + "fritzbox-setup.de.md#fehlersuche"
    return _GUIDE_BASE_URL + "fritzbox-setup.md#troubleshooting"


def _text_label(html: str) -> QLabel:
    label = QLabel(html)
    label.setWordWrap(True)
    label.setOpenExternalLinks(True)
    return label


def _list_html(items: list[str], ordered: bool) -> str:
    tag = "ol" if ordered else "ul"
    return f"<{tag}>" + "".join(f"<li>{item}</li>" for item in items) + f"</{tag}>"


class _InfoPage(QWizardPage):
    """A page of explanations: an intro, a list, an optional note and "Open FRITZ!Box"."""

    def __init__(self, title, subtitle, items, ordered, note=None, open_fritzbox=None, parent=None):
        super().__init__(parent)
        self.setTitle(title)
        self.setSubTitle(subtitle)
        layout = QVBoxLayout(self)
        layout.addWidget(_text_label(_list_html(items, ordered)))
        if note is not None:
            layout.addWidget(_text_label(note))
        self.open_button = None
        if open_fritzbox is not None:
            self.open_button = QPushButton(tr("Open FRITZ!Box"))
            self.open_button.clicked.connect(open_fritzbox)
            layout.addWidget(self.open_button)
        layout.addStretch()


class AudioPage(QWizardPage):
    def __init__(self, sip_engine, parent=None):
        super().__init__(parent)
        self.setTitle(tr("Audio"))
        self.setSubTitle(tr("Choose your headset, then test it."))
        self.audio = AudioSetupWidget(sip_engine)
        layout = QVBoxLayout(self)
        layout.addWidget(self.audio)
        layout.addStretch()


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


class SetupWizard(QWizard):
    """Walks a first-time user through the FRITZ!Box IP phone setup and configures voice2fritz."""

    def __init__(self, sip_engine, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("voice2fritz setup"))
        # Classic style follows the app palette; the modern style paints a white header.
        self.setWizardStyle(QWizard.WizardStyle.ClassicStyle)
        self.setOption(QWizard.WizardOption.NoBackButtonOnStartPage, True)
        self.setButtonText(QWizard.WizardButton.BackButton, tr("Back"))
        self.setButtonText(QWizard.WizardButton.NextButton, tr("Next"))
        self.setButtonText(QWizard.WizardButton.FinishButton, tr("Finish"))
        self.setButtonText(QWizard.WizardButton.CancelButton, tr("Cancel"))

        self.connect_page = ConnectPage(sip_engine)
        self.audio_page = AudioPage(sip_engine)

        self.addPage(
            _InfoPage(
                tr("Welcome"),
                tr("This wizard connects voice2fritz to your FRITZ!Box as an IP phone, step by step. Before you start, check that:"),
                [
                    tr("This computer is on your home network, by cable or WLAN. The guest WLAN will not work."),
                    tr("Any VPN is turned off for now."),
                    tr("You know the password for the FRITZ!Box web interface. It is often printed on a sticker on the bottom of the box."),
                    tr("Your headset is plugged in."),
                ],
                ordered=False,
            )
        )
        self.addPage(
            _InfoPage(
                tr("Check your phone number"),
                tr("Your FRITZ!Box needs at least one phone number from your internet provider."),
                [
                    tr("Click <b>Open FRITZ!Box</b> below and log in."),
                    tr("Go to <b>Telephony → Own Numbers</b>."),
                    tr("Check that at least one number has a green dot."),
                ],
                ordered=True,
                note=tr(
                    "If the list is empty, your provider has not set up telephony yet. Most providers do this "
                    "automatically. If yours does not, use the FRITZ!Box wizard for adding a phone number, with the "
                    "details your provider sent you."
                ),
                open_fritzbox=self.open_fritzbox,
            )
        )
        self.addPage(
            _InfoPage(
                tr("Create an IP phone"),
                tr("voice2fritz connects to the FRITZ!Box as an IP phone. Create one for it."),
                [
                    tr("In the FRITZ!Box, go to <b>Telephony → Telephony Devices</b>."),
                    tr("Click <b>Configure New Device</b>."),
                    tr("Choose <b>Telephone (with and without answering machine)</b> and click <b>Next</b>."),
                    tr("Choose <b>LAN/WLAN (IP telephone)</b> and click <b>Next</b>."),
                    tr("Enter a name, for example <b>voice2fritz</b>."),
                    tr("Choose a <b>username</b> and a <b>password</b>, and write both down."),
                    tr("Choose the <b>outgoing number</b> that people see when you call them."),
                    tr("Choose which <b>incoming calls</b> should ring in voice2fritz."),
                    tr("Finish the wizard. You may need to confirm with a button press on the box or on a DECT handset."),
                ],
                ordered=True,
                note=tr(
                    "The username and password are new credentials only for voice2fritz. "
                    "They are not your FRITZ!Box login."
                ),
                open_fritzbox=self.open_fritzbox,
            )
        )
        self.addPage(self.connect_page)
        self.addPage(self.audio_page)
        self.addPage(
            _InfoPage(
                tr("Done"),
                tr("voice2fritz is connected. Make a few test calls:"),
                [
                    tr("<b>Internal:</b> dial the internal number of a DECT handset, for example <b>**610</b>. This costs nothing."),
                    tr("<b>External:</b> call your mobile phone and check that both sides hear each other."),
                    tr("<b>Incoming:</b> call your landline from your mobile phone."),
                ],
                ordered=False,
                note=tr(
                    'If something does not work, see the <a href="{url}">troubleshooting section of the setup guide</a>.',
                    url=guide_url(),
                ),
            )
        )

    def open_fritzbox(self) -> None:
        QDesktopServices.openUrl(QUrl(f"http://{self.connect_page.host()}"))

    def set_call_active(self, active: bool) -> None:
        self.audio_page.audio.set_call_active(active)
