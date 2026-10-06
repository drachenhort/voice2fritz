import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QWizard

from voice2fritz import config
from voice2fritz.gui import setup_wizard as setup_wizard_module
from voice2fritz.gui.audio_setup_widget import AudioSetupWidget
from voice2fritz.gui.setup_wizard import ConnectPage, SetupWizard
from voice2fritz.i18n import set_language
from voice2fritz.network import AddressInfo


class FakeSipEngine(QObject):
    registrationStateChanged = Signal(str)

    def __init__(self):
        super().__init__()
        self.registrations = []
        self.events = []
        self.media_address = None
        self.fail_with = None

    def register(self, host, username, password):
        if self.fail_with is not None:
            raise self.fail_with
        self.registrations.append((host, username, password))

    def list_devices(self):
        return []

    def select_capture_device(self, device_id):
        pass

    def select_playback_device(self, device_id):
        pass

    def start_level_monitor(self):
        self.events.append("monitor on")

    def stop_level_monitor(self):
        self.events.append("monitor off")

    def capture_level(self):
        return 0.0

    def start_echo_recording(self, path):
        self.events.append("record")

    def stop_echo_recording(self):
        self.events.append("stop record")

    def start_echo_playback(self, path):
        self.events.append("play")

    def stop_echo_playback(self):
        self.events.append("stop play")


@pytest.fixture(autouse=True)
def no_config_files(monkeypatch):
    saved = []
    monkeypatch.setattr(config, "load_config", lambda path=config.DEFAULT_CONFIG_PATH: None)
    monkeypatch.setattr(config, "save_account", lambda cfg, password, path=config.DEFAULT_CONFIG_PATH: saved.append((cfg, password)))
    monkeypatch.setattr(config, "load_device_selection", lambda path=config.DEFAULT_CONFIG_PATH: (None, None))
    monkeypatch.setattr(config, "save_device_selection", lambda capture, playback, path=config.DEFAULT_CONFIG_PATH: None)
    return saved


@pytest.fixture
def engine():
    return FakeSipEngine()


@pytest.fixture
def page(qtbot, engine):
    page = ConnectPage(engine)
    qtbot.addWidget(page)
    return page


def _fill(page, host="fritz.box", username="620", password="secret12"):
    page.host_edit.setText(host)
    page.username_edit.setText(username)
    page.password_edit.setText(password)


def test_host_defaults_to_fritz_box(page):
    assert page.host_edit.text() == "fritz.box"
    assert page.username_edit.text() == ""
    assert page.password_edit.text() == ""


def test_saved_account_is_prefilled_without_password(qtbot, engine, monkeypatch):
    monkeypatch.setattr(
        config, "load_config", lambda path=config.DEFAULT_CONFIG_PATH: config.AccountConfig("192.168.178.1", "620")
    )
    page = ConnectPage(engine)
    qtbot.addWidget(page)

    assert page.host_edit.text() == "192.168.178.1"
    assert page.username_edit.text() == "620"
    assert page.password_edit.text() == ""


def test_connect_needs_all_three_fields(page):
    _fill(page, password="")
    assert not page.connect_button.isEnabled()

    page.password_edit.setText("secret12")
    assert page.connect_button.isEnabled()


def test_connect_saves_and_registers_with_stripped_values(page, engine, no_config_files):
    _fill(page, host="  fritz.box ", username=" 620 ")

    page.connect_button.click()

    assert no_config_files == [(config.AccountConfig("fritz.box", "620"), "secret12")]
    assert engine.registrations == [("fritz.box", "620", "secret12")]
    assert page.status_label.text() == "Connecting..."
    assert not page.connect_button.isEnabled()
    assert page._timer.isActive()
    assert not page.isComplete()


def test_successful_registration_completes_the_page(page, engine, qtbot):
    _fill(page)
    page.connect_button.click()

    with qtbot.waitSignal(page.completeChanged, timeout=1000):
        engine.registrationStateChanged.emit("200 OK")

    assert page.status_label.text() == "Connected as 620@fritz.box."
    assert page.isComplete()
    assert page.connect_button.isEnabled()
    assert not page._timer.isActive()
    assert page.vpn_label.isHidden()


def test_rejected_login_explains_which_credentials_to_use(page, engine):
    _fill(page)
    page.connect_button.click()

    engine.registrationStateChanged.emit("401 Unauthorized")

    assert page.status_label.text() == (
        "The FRITZ!Box rejected the login. Use the username and password of the IP phone, not the FRITZ!Box login."
    )
    assert not page.isComplete()
    assert page.connect_button.isEnabled()


def test_other_failure_shows_the_status(page, engine):
    _fill(page)
    page.connect_button.click()

    engine.registrationStateChanged.emit("503 Service Unavailable")

    assert page.status_label.text() == (
        "Could not connect: 503 Service Unavailable. Check the host, and that this computer is not on the guest WLAN."
    )
    assert not page.isComplete()


def test_register_error_is_shown_on_the_page(page, engine):
    class RegistrationError(Exception):
        reason = "Invalid URI (PJSIP_EINVALIDURI)"

    engine.fail_with = RegistrationError()
    _fill(page, host="bad host")

    page.connect_button.click()

    assert page.status_label.text() == (
        "Could not connect: Invalid URI (PJSIP_EINVALIDURI). Check the host, and that this computer is not on the guest WLAN."
    )
    assert not page._timer.isActive()
    assert page.connect_button.isEnabled()


def test_no_answer_suggests_the_ip_address(page):
    _fill(page)
    page.connect_button.click()

    page._timer.timeout.emit()

    assert page.status_label.text() == (
        "No answer from fritz.box. Try 192.168.178.1, and check that this computer is not on the guest WLAN."
    )
    assert not page.isComplete()
    assert page.connect_button.isEnabled()


def test_vpn_address_adds_a_warning(page, engine, monkeypatch):
    monkeypatch.setattr(setup_wizard_module, "describe_address", lambda address: AddressInfo(address, "tailscale0", "VPN"))
    engine.media_address = "100.64.0.5"
    _fill(page)
    page.connect_button.click()

    engine.registrationStateChanged.emit("200 OK")

    assert not page.vpn_label.isHidden()
    assert page.vpn_label.text().startswith("Call audio goes through the VPN")
    assert page.isComplete()


def test_only_the_first_result_after_connect_counts(page, engine):
    _fill(page)
    page.connect_button.click()
    engine.registrationStateChanged.emit("200 OK")

    engine.registrationStateChanged.emit("408 Request Timeout")  # PJSIP refresh failing later

    assert page.status_label.text() == "Connected as 620@fritz.box."
    assert page.isComplete()


def test_updates_before_connect_are_ignored(page, engine):
    engine.registrationStateChanged.emit("200 OK")  # the old account still refreshing

    assert page.status_label.text() == ""
    assert not page.isComplete()


def test_editing_a_field_after_success_requires_a_new_connect(page, engine):
    _fill(page)
    page.connect_button.click()
    engine.registrationStateChanged.emit("200 OK")

    page.username_edit.setText("621")

    assert not page.isComplete()
    assert page.status_label.text() == ""


def test_result_arriving_after_an_edit_is_ignored(page, engine):
    _fill(page)
    page.connect_button.click()
    page.username_edit.setText("621")  # user changes their mind while waiting

    engine.registrationStateChanged.emit("200 OK")

    assert not page.isComplete()
    assert not page._timer.isActive()
    assert page.connect_button.isEnabled()


@pytest.fixture
def wizard(qtbot, engine):
    wizard = SetupWizard(engine)
    qtbot.addWidget(wizard)
    return wizard


@pytest.fixture
def opened_urls(monkeypatch):
    urls = []
    monkeypatch.setattr(setup_wizard_module.QDesktopServices, "openUrl", staticmethod(lambda url: urls.append(url.toString())))
    return urls


def test_wizard_has_six_pages_in_order(wizard):
    titles = [wizard.page(page_id).title() for page_id in wizard.pageIds()]
    assert titles == ["Welcome", "Check your phone number", "Create an IP phone", "Connect", "Audio", "Done"]


def test_wizard_is_not_modal(wizard):
    assert not wizard.isModal()


def test_next_is_blocked_on_connect_page_until_connected(wizard, engine):
    wizard.show()
    for _ in range(3):
        wizard.next()
    assert wizard.currentPage() is wizard.connect_page
    assert not wizard.button(QWizard.WizardButton.NextButton).isEnabled()

    _fill(wizard.connect_page)
    wizard.connect_page.connect_button.click()
    engine.registrationStateChanged.emit("200 OK")

    assert wizard.button(QWizard.WizardButton.NextButton).isEnabled()
    wizard.next()
    assert wizard.currentPage() is wizard.audio_page


def test_back_works_on_connect_page(wizard):
    wizard.show()
    for _ in range(3):
        wizard.next()

    wizard.back()

    assert wizard.currentPage().title() == "Create an IP phone"


def test_open_fritzbox_uses_the_host_field(wizard, opened_urls):
    wizard.connect_page.host_edit.setText(" 192.168.178.1 ")

    wizard.open_fritzbox()

    assert opened_urls == ["http://192.168.178.1"]


def test_open_fritzbox_falls_back_to_fritz_box(wizard, opened_urls):
    wizard.connect_page.host_edit.setText("")

    wizard.open_fritzbox()

    assert opened_urls == ["http://fritz.box"]


def test_info_pages_have_an_open_fritzbox_button(wizard, opened_urls):
    page = wizard.page(wizard.pageIds()[1])

    page.open_button.click()

    assert opened_urls == ["http://fritz.box"]


def test_audio_page_holds_the_audio_widget(wizard):
    assert isinstance(wizard.audio_page.audio, AudioSetupWidget)


def test_call_stops_the_wizard_echo_test(wizard, engine):
    audio = wizard.audio_page.audio
    audio.echo_test_button.click()

    wizard.set_call_active(True)

    assert audio.echo_test_status.text() == "Test cancelled."
    assert not audio.echo_test_button.isEnabled()


def test_guide_link_follows_the_language():
    try:
        assert setup_wizard_module.guide_url().endswith("/docs/fritzbox-setup.md#troubleshooting")
        set_language("de")
        assert setup_wizard_module.guide_url().endswith("/docs/fritzbox-setup.de.md#fehlersuche")
    finally:
        set_language("en")
