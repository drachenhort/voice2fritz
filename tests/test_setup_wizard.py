import pytest
from PySide6.QtCore import QObject, Signal

from voice2fritz import config
from voice2fritz.gui import setup_wizard as setup_wizard_module
from voice2fritz.gui.setup_wizard import ConnectPage
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
