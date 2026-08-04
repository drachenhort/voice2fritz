# FritzBox Phonebook Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the user browse their FritzBox's phonebook via TR-064 and click a contact to fill the dial field.

**Architecture:** `tr064.py` fetches and parses the phonebook (stdlib `urllib` + `xml.etree.ElementTree`, no new dependency), with the XML-parsing logic factored into a pure, testable function. `config.py` gains FritzBox-specific credential storage, reusing the existing SIP account's host. `settings_dialog.py` gains two fields for those credentials. A new `contacts_dialog.py` shows the fetched list and reports the chosen number back to `main_window.py` via a signal.

**Tech Stack:** Python stdlib (`urllib`, `xml.etree.ElementTree`), PySide6 (existing stack, no new dependencies).

## Global Constraints

- No new pip dependencies — HTTP and XML handling both via Python stdlib.
- FritzBox TR-064 credentials (username + password) are separate from the SIP account credentials, even though they share the same host. Password stored in keyring under a distinct key (`f"fritzbox:{username}"`) so it can never collide with a SIP password stored under the same username string.
- Read-only, browse-and-dial only. No editing, no caller-ID lookup on incoming calls, no local caching/syncing of the phonebook to disk — out of scope for this plan.
- Network/auth failures must not crash the app — shown via `QMessageBox`, dialog stays open with an empty list.
- `tr064.get_phonebook`'s network calls have no automated test (real FritzBox required) — verified manually against the user's FritzBox 7590. Its XML-parsing logic (`parse_phonebook_xml`) IS unit-tested with a canned XML string, following the same pure/impure split as `audio.py`.

---

## File Structure

```
voice2fritz/
  src/voice2fritz/
    tr064.py                    (new)
    config.py                   (modified: FritzBox credential storage)
    gui/
      settings_dialog.py         (modified: FritzBox credential fields)
      contacts_dialog.py         (new)
      main_window.py             (modified: Contacts button + wiring)
  tests/
    test_tr064.py                (new)
    test_config.py               (modified)
    test_settings_dialog.py      (modified)
    test_contacts_dialog.py      (new)
```

---

### Task 1: `tr064.py` — phonebook fetch + parse, `config.py` credential storage

**Files:**
- Create: `src/voice2fritz/tr064.py`
- Test: `tests/test_tr064.py`
- Modify: `src/voice2fritz/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces:
  - `@dataclass Contact(name: str, numbers: list[str])`
  - `parse_phonebook_xml(xml_text: str) -> list[Contact]` — pure, no network.
  - `get_phonebook(host: str, username: str, password: str) -> list[Contact]` — network + SOAP + parse. Raises on failure (network error, auth error, malformed response) rather than swallowing errors — callers (Task 3's `ContactsDialog`) catch broadly around this call.
  - `config.load_fritzbox_username(path=DEFAULT_CONFIG_PATH) -> str | None`
  - `config.save_fritzbox_username(username: str, path=DEFAULT_CONFIG_PATH) -> None`
  - `config.get_fritzbox_password(username: str) -> str | None`
  - `config.set_fritzbox_password(username: str, password: str) -> None`

- [ ] **Step 1: Write the failing test for `parse_phonebook_xml`**

```python
# tests/test_tr064.py
from voice2fritz.tr064 import Contact, parse_phonebook_xml

SAMPLE_PHONEBOOK_XML = """<?xml version="1.0" encoding="utf-8"?>
<phonebooks>
  <phonebook>
    <contact>
      <person>
        <realName>Anna Schmidt</realName>
      </person>
      <telephony>
        <number type="home">+4917612345678</number>
        <number type="mobile">+4917698765432</number>
      </telephony>
    </contact>
    <contact>
      <person>
        <realName>Ben Weber</realName>
      </person>
      <telephony>
        <number type="mobile">+4930123456</number>
      </telephony>
    </contact>
  </phonebook>
</phonebooks>
"""


def test_parse_phonebook_xml_extracts_name_and_numbers():
    contacts = parse_phonebook_xml(SAMPLE_PHONEBOOK_XML)

    assert contacts == [
        Contact(name="Anna Schmidt", numbers=["+4917612345678", "+4917698765432"]),
        Contact(name="Ben Weber", numbers=["+4930123456"]),
    ]


def test_parse_phonebook_xml_empty_phonebook():
    xml_text = """<?xml version="1.0" encoding="utf-8"?>
<phonebooks><phonebook></phonebook></phonebooks>"""

    assert parse_phonebook_xml(xml_text) == []


def test_parse_phonebook_xml_contact_without_numbers():
    xml_text = """<?xml version="1.0" encoding="utf-8"?>
<phonebooks>
  <phonebook>
    <contact>
      <person><realName>No Number Guy</realName></person>
      <telephony></telephony>
    </contact>
  </phonebook>
</phonebooks>"""

    assert parse_phonebook_xml(xml_text) == [Contact(name="No Number Guy", numbers=[])]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/pytest tests/test_tr064.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'voice2fritz.tr064'`

- [ ] **Step 3: Write `src/voice2fritz/tr064.py`**

```python
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from urllib.request import (
    HTTPDigestAuthHandler,
    HTTPPasswordMgrWithDefaultRealm,
    Request,
    build_opener,
)

TR064_PORT = 49000
SERVICE_TYPE = "urn:dslforum-org:service:X_AVM-DE_OnTel:1"
CONTROL_PATH = "/upnp/control/x_contact"


@dataclass
class Contact:
    name: str
    numbers: list[str]


def parse_phonebook_xml(xml_text: str) -> list[Contact]:
    root = ET.fromstring(xml_text)
    contacts = []
    for contact_el in root.iter("contact"):
        person_el = contact_el.find("person")
        name = person_el.findtext("realName", default="") if person_el is not None else ""

        numbers = []
        telephony_el = contact_el.find("telephony")
        if telephony_el is not None:
            for number_el in telephony_el.findall("number"):
                if number_el.text:
                    numbers.append(number_el.text.strip())

        contacts.append(Contact(name=name, numbers=numbers))
    return contacts


def _soap_request(opener, host: str, action: str, body_xml: str) -> str:
    url = f"http://{host}:{TR064_PORT}{CONTROL_PATH}"
    envelope = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" '
        's:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'
        f"<s:Body>{body_xml}</s:Body></s:Envelope>"
    ).encode("utf-8")
    request = Request(
        url,
        data=envelope,
        headers={
            "Content-Type": 'text/xml; charset="utf-8"',
            "SOAPAction": f'"{SERVICE_TYPE}#{action}"',
        },
    )
    with opener.open(request, timeout=10) as response:
        return response.read().decode("utf-8")


def get_phonebook(host: str, username: str, password: str) -> list[Contact]:
    password_manager = HTTPPasswordMgrWithDefaultRealm()
    password_manager.add_password(None, f"http://{host}:{TR064_PORT}/", username, password)
    opener = build_opener(HTTPDigestAuthHandler(password_manager))

    list_body = f'<u:GetPhonebookList xmlns:u="{SERVICE_TYPE}" />'
    list_response = _soap_request(opener, host, "GetPhonebookList", list_body)
    list_root = ET.fromstring(list_response)
    ids_el = list_root.find(".//NewPhonebookList")
    phonebook_id = ids_el.text.split(",")[0].strip() if ids_el is not None and ids_el.text else "0"

    get_body = f'<u:GetPhonebook xmlns:u="{SERVICE_TYPE}"><NewPhonebookID>{phonebook_id}</NewPhonebookID></u:GetPhonebook>'
    get_response = _soap_request(opener, host, "GetPhonebook", get_body)
    get_root = ET.fromstring(get_response)
    url_el = get_root.find(".//NewPhonebookURL")
    if url_el is None or not url_el.text:
        raise ValueError("FritzBox did not return a phonebook URL")

    with opener.open(url_el.text, timeout=10) as response:
        xml_text = response.read().decode("utf-8")

    return parse_phonebook_xml(xml_text)
```

**Note for implementer/manual verification:** FritzBox's exact SOAP
response element names and the phonebook URL's own auth scheme can vary
slightly by firmware version. If Step 8 (Task 4's manual verification)
reveals a mismatch, adjust `get_phonebook` accordingly — this is expected
verification work against real hardware, not a plan defect, same as
`sip_engine.py`'s equivalent note in the v1 plan.

- [ ] **Step 4: Run test to verify it passes**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/pytest tests/test_tr064.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Write the failing tests for FritzBox credential storage**

Add to `tests/test_config.py`'s import block:

```python
from voice2fritz.config import (
    AccountConfig,
    load_config,
    save_config,
    load_device_selection,
    save_device_selection,
    load_fritzbox_username,
    save_fritzbox_username,
    get_fritzbox_password,
    set_fritzbox_password,
    get_password,
    set_password,
)
```

Add these test functions (near the device-selection tests):

```python
def test_save_and_load_fritzbox_username_round_trip(tmp_path):
    path = tmp_path / "config.json"

    save_fritzbox_username("fritzuser", path)

    assert load_fritzbox_username(path) == "fritzuser"


def test_load_fritzbox_username_missing_file_returns_none(tmp_path):
    path = tmp_path / "does-not-exist.json"
    assert load_fritzbox_username(path) is None


def test_save_fritzbox_username_preserves_existing_account(tmp_path):
    path = tmp_path / "config.json"
    cfg = AccountConfig(host="fritz.box", username="user123")
    save_config(cfg, path)

    save_fritzbox_username("fritzuser", path)

    assert load_config(path) == cfg
    assert load_fritzbox_username(path) == "fritzuser"


def test_set_and_get_fritzbox_password_uses_distinct_keyring_key(monkeypatch):
    store: dict[tuple[str, str], str] = {}

    def fake_set_password(service, username, password):
        store[(service, username)] = password

    def fake_get_password(service, username):
        return store.get((service, username))

    monkeypatch.setattr("voice2fritz.config.keyring.set_password", fake_set_password)
    monkeypatch.setattr("voice2fritz.config.keyring.get_password", fake_get_password)

    set_password("user123", "sip-secret")
    set_fritzbox_password("user123", "fritzbox-secret")

    assert get_password("user123") == "sip-secret"
    assert get_fritzbox_password("user123") == "fritzbox-secret"
```

- [ ] **Step 6: Run tests to verify they fail**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/pytest tests/test_config.py -v`
Expected: FAIL with `ImportError: cannot import name 'load_fritzbox_username'`

- [ ] **Step 7: Add the FritzBox credential functions to `config.py`**

Add to `src/voice2fritz/config.py`, after `save_device_selection`:

```python
FRITZBOX_KEYRING_PREFIX = "fritzbox:"


def load_fritzbox_username(path: Path = DEFAULT_CONFIG_PATH) -> str | None:
    data = _read_raw(path)
    return data.get("fritzbox_username")


def save_fritzbox_username(username: str, path: Path = DEFAULT_CONFIG_PATH) -> None:
    data = _read_raw(path)
    data["fritzbox_username"] = username
    _write_raw(data, path)


def get_fritzbox_password(username: str) -> str | None:
    return keyring.get_password(SERVICE_NAME, f"{FRITZBOX_KEYRING_PREFIX}{username}")


def set_fritzbox_password(username: str, password: str) -> None:
    keyring.set_password(SERVICE_NAME, f"{FRITZBOX_KEYRING_PREFIX}{username}", password)
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/pytest tests/test_config.py tests/test_tr064.py -v`
Expected: PASS (all passing, no regressions)

- [ ] **Step 9: Commit**

```bash
git add src/voice2fritz/tr064.py src/voice2fritz/config.py tests/test_tr064.py tests/test_config.py
git commit -m "feat: fetch/parse FritzBox phonebook via TR-064, store FritzBox credentials"
```

---

### Task 2: FritzBox credential fields in `SettingsDialog`

**Files:**
- Modify: `src/voice2fritz/gui/settings_dialog.py`
- Modify: `tests/test_settings_dialog.py`

**Interfaces:**
- Consumes: `config.save_fritzbox_username`, `config.set_fritzbox_password` (Task 1).
- Produces: `SettingsDialog.fritzbox_username_edit: QLineEdit`, `SettingsDialog.fritzbox_password_edit: QLineEdit` — new widgets, saved on the same `save_button` click as the existing SIP fields.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_settings_dialog.py`:

```python
def test_save_button_persists_fritzbox_credentials(qtbot, tmp_path, monkeypatch):
    saved_usernames = []
    saved_passwords = []

    monkeypatch.setattr(config, "save_config", lambda cfg, path=config.DEFAULT_CONFIG_PATH: None)
    monkeypatch.setattr(config, "set_password", lambda username, password: None)
    monkeypatch.setattr(config, "save_fritzbox_username", lambda username, path=config.DEFAULT_CONFIG_PATH: saved_usernames.append(username))
    monkeypatch.setattr(config, "set_fritzbox_password", lambda username, password: saved_passwords.append((username, password)))

    dialog = SettingsDialog()
    qtbot.addWidget(dialog)

    dialog.host_edit.setText("fritz.box")
    dialog.username_edit.setText("sipuser")
    dialog.password_edit.setText("sip-secret")
    dialog.fritzbox_username_edit.setText("fritzuser")
    dialog.fritzbox_password_edit.setText("fritzbox-secret")

    with qtbot.waitSignal(dialog.accountSaved, timeout=1000):
        dialog.save_button.click()

    assert saved_usernames == ["fritzuser"]
    assert saved_passwords == [("fritzuser", "fritzbox-secret")]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/pytest tests/test_settings_dialog.py -v -k fritzbox`
Expected: FAIL with `AttributeError: 'SettingsDialog' object has no attribute 'fritzbox_username_edit'`

- [ ] **Step 3: Add the fields to `SettingsDialog`**

In `src/voice2fritz/gui/settings_dialog.py`, replace the body of `__init__` from
`self.host_edit = QLineEdit()` through `layout.addWidget(self.save_button)`
with:

```python
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
```

Replace `_on_save`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/pytest tests/test_settings_dialog.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Run the full suite to confirm no regressions**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/pytest -v`
Expected: PASS, 43 passed (35 existing before this plan + 3 from Task 1's `test_tr064.py` + 4 from Task 1's `test_config.py` additions + 1 from this task's `test_settings_dialog.py` addition), zero failing.

- [ ] **Step 6: Commit**

```bash
git add src/voice2fritz/gui/settings_dialog.py tests/test_settings_dialog.py
git commit -m "feat: add FritzBox credential fields to settings dialog"
```

---

### Task 3: `ContactsDialog`

**Files:**
- Create: `src/voice2fritz/gui/contacts_dialog.py`
- Test: `tests/test_contacts_dialog.py`

**Interfaces:**
- Consumes: `config.load_fritzbox_username`, `config.get_fritzbox_password` (Task 1), `tr064.get_phonebook`, `tr064.Contact` (Task 1).
- Produces: `class ContactsDialog(QDialog)` with:
  - Constructor: `ContactsDialog(host: str, parent=None)`
  - Signal: `contactSelected = Signal(str)` — emitted with the chosen number.
  - Widgets: `contact_list: QListWidget`, `select_button: QPushButton`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_contacts_dialog.py
from voice2fritz import config as config_module, tr064
from voice2fritz.gui.contacts_dialog import ContactsDialog


def test_populates_list_from_fetched_contacts(qtbot, monkeypatch):
    monkeypatch.setattr(config_module, "load_fritzbox_username", lambda path=config_module.DEFAULT_CONFIG_PATH: "fritzuser")
    monkeypatch.setattr(config_module, "get_fritzbox_password", lambda username: "secret")
    monkeypatch.setattr(
        tr064,
        "get_phonebook",
        lambda host, username, password: [
            tr064.Contact(name="Anna Schmidt", numbers=["+4917612345678", "+4917698765432"]),
            tr064.Contact(name="Ben Weber", numbers=["+4930123456"]),
        ],
    )

    dialog = ContactsDialog("fritz.box")
    qtbot.addWidget(dialog)

    assert dialog.contact_list.count() == 3
    assert dialog.contact_list.item(0).text() == "Anna Schmidt — +4917612345678"
    assert dialog.contact_list.item(2).text() == "Ben Weber — +4930123456"


def test_double_click_emits_selected_number_and_closes(qtbot, monkeypatch):
    monkeypatch.setattr(config_module, "load_fritzbox_username", lambda path=config_module.DEFAULT_CONFIG_PATH: "fritzuser")
    monkeypatch.setattr(config_module, "get_fritzbox_password", lambda username: "secret")
    monkeypatch.setattr(
        tr064,
        "get_phonebook",
        lambda host, username, password: [tr064.Contact(name="Anna Schmidt", numbers=["+4917612345678"])],
    )

    dialog = ContactsDialog("fritz.box")
    qtbot.addWidget(dialog)

    with qtbot.waitSignal(dialog.contactSelected, timeout=1000) as blocker:
        dialog._on_item_activated(dialog.contact_list.item(0))

    assert blocker.args == ["+4917612345678"]


def test_no_fritzbox_username_shows_warning_and_empty_list(qtbot, monkeypatch):
    monkeypatch.setattr(config_module, "load_fritzbox_username", lambda path=config_module.DEFAULT_CONFIG_PATH: None)

    dialog = ContactsDialog("fritz.box")
    qtbot.addWidget(dialog)

    assert dialog.contact_list.count() == 0


def test_fetch_failure_shows_warning_and_leaves_list_empty(qtbot, monkeypatch):
    monkeypatch.setattr(config_module, "load_fritzbox_username", lambda path=config_module.DEFAULT_CONFIG_PATH: "fritzuser")
    monkeypatch.setattr(config_module, "get_fritzbox_password", lambda username: "secret")

    def raise_error(host, username, password):
        raise ValueError("network error")

    monkeypatch.setattr(tr064, "get_phonebook", raise_error)

    dialog = ContactsDialog("fritz.box")
    qtbot.addWidget(dialog)

    assert dialog.contact_list.count() == 0
```

These tests monkeypatch `QMessageBox.warning` implicitly is NOT needed —
`QMessageBox.warning` is modal and blocks; since these tests run
headless (`QT_QPA_PLATFORM=offscreen`, set in `tests/conftest.py`), a
real modal dialog would hang the test. Add this fixture at the top of
`tests/test_contacts_dialog.py`, before the test functions:

```python
import pytest
from PySide6.QtWidgets import QMessageBox


@pytest.fixture(autouse=True)
def no_modal_warnings(monkeypatch):
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/pytest tests/test_contacts_dialog.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'voice2fritz.gui.contacts_dialog'`

- [ ] **Step 3: Write `src/voice2fritz/gui/contacts_dialog.py`**

```python
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDialog, QListWidget, QListWidgetItem, QMessageBox, QPushButton, QVBoxLayout

from voice2fritz import config, tr064


class ContactsDialog(QDialog):
    contactSelected = Signal(str)

    def __init__(self, host: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Contacts")
        self.host = host
        self._numbers_by_row: list[str] = []

        self.contact_list = QListWidget()
        self.select_button = QPushButton("Select")

        layout = QVBoxLayout(self)
        layout.addWidget(self.contact_list)
        layout.addWidget(self.select_button)

        self.contact_list.itemDoubleClicked.connect(self._on_item_activated)
        self.select_button.clicked.connect(self._on_select_clicked)

        self._load_contacts()

    def _load_contacts(self) -> None:
        username = config.load_fritzbox_username()
        if username is None:
            QMessageBox.warning(self, "Contacts", "FritzBox credentials not configured — set them in Settings.")
            return

        password = config.get_fritzbox_password(username) or ""
        try:
            contacts = tr064.get_phonebook(self.host, username, password)
        except Exception as exc:
            QMessageBox.warning(self, "Contacts", f"Could not load contacts: {exc}")
            return

        for contact in contacts:
            for number in contact.numbers:
                self.contact_list.addItem(QListWidgetItem(f"{contact.name} — {number}"))
                self._numbers_by_row.append(number)

    def _on_item_activated(self, item: QListWidgetItem) -> None:
        self._select_row(self.contact_list.row(item))

    def _on_select_clicked(self) -> None:
        row = self.contact_list.currentRow()
        if row >= 0:
            self._select_row(row)

    def _select_row(self, row: int) -> None:
        self.contactSelected.emit(self._numbers_by_row[row])
        self.accept()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/pytest tests/test_contacts_dialog.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/voice2fritz/gui/contacts_dialog.py tests/test_contacts_dialog.py
git commit -m "feat: add ContactsDialog fetching and listing the FritzBox phonebook"
```

---

### Task 4: Wire `ContactsDialog` into `MainWindow`

**Files:**
- Modify: `src/voice2fritz/gui/main_window.py`
- Modify: `tests/test_main_window.py`

**Interfaces:**
- Consumes: `ContactsDialog(host, parent)`, `ContactsDialog.contactSelected` (Task 3); `config.load_config` (existing).
- Produces: `MainWindow.contacts_button: QPushButton`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_main_window.py`:

```python
def test_contacts_button_opens_dialog_and_fills_number_on_selection(qtbot, monkeypatch):
    from PySide6.QtCore import QObject, Signal

    monkeypatch.setattr(config_module, "load_config", lambda path=config_module.DEFAULT_CONFIG_PATH: config_module.AccountConfig(host="fritz.box", username="user123"))

    class FakeContactsDialogQt(QObject):
        contactSelected = Signal(str)

        def __init__(self, host, parent=None):
            super().__init__()
            self.host = host
            FakeContactsDialogQt.last_instance = self

        def exec(self):
            return None

    monkeypatch.setattr("voice2fritz.gui.main_window.ContactsDialog", FakeContactsDialogQt)

    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    window.contacts_button.click()

    assert FakeContactsDialogQt.last_instance.host == "fritz.box"

    FakeContactsDialogQt.last_instance.contactSelected.emit("+4917612345678")

    assert window.number_edit.text() == "+4917612345678"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/pytest tests/test_main_window.py -v -k contacts`
Expected: FAIL with `AttributeError: 'MainWindow' object has no attribute 'contacts_button'`

- [ ] **Step 3: Wire the button in `MainWindow`**

In `src/voice2fritz/gui/main_window.py`, add the import:

```python
from voice2fritz.gui.contacts_dialog import ContactsDialog
```

Add `self.contacts_button = QPushButton("Contacts")` right after
`self.settings_button = QPushButton("Settings")` (in the settings dialog
button block near `settings_button`'s creation), and add it to
`controls_column` right after `controls_column.addWidget(self.settings_button)`:

```python
        controls_column.addWidget(self.contacts_button)
```

In `_connect_signals`, add:

```python
        self.contacts_button.clicked.connect(self._on_contacts_clicked)
```

Add the handler, next to `_on_settings_clicked`:

```python
    def _on_contacts_clicked(self) -> None:
        account = config.load_config()
        host = account.host if account is not None else ""
        dialog = ContactsDialog(host, self)
        dialog.contactSelected.connect(self.number_edit.setText)
        dialog.exec()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/pytest tests/test_main_window.py -v`
Expected: PASS, all tests in the file.

- [ ] **Step 5: Run the full suite to confirm no regressions**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/pytest -v`
Expected: PASS, all passing, zero failing.

- [ ] **Step 6: Manual verification against real hardware**

With the real FRITZ!Box 7590 already used for prior verification:
1. Run `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/python -m voice2fritz.main`.
2. Open Settings, fill in the FritzBox web-login username/password (the
   one used to log into `fritz.box`'s web UI — separate from the SIP
   username/password already there), Save.
3. Click Contacts. Confirm the real phonebook loads with correct
   names/numbers. If it fails, inspect the actual SOAP response
   (`curl`/browser against `http://fritz.box:49000/...` or add a temporary
   print in `tr064.py`) and adjust `get_phonebook`/`parse_phonebook_xml`
   to match — this is expected hardware-specific debugging, not
   necessarily a plan defect.
4. Double-click a contact, confirm the dial field fills with the correct
   number and the dialog closes.
5. Click Call, confirm it actually dials that number correctly (reuses
   the existing, already-verified call flow).

- [ ] **Step 7: Commit**

```bash
git add src/voice2fritz/gui/main_window.py tests/test_main_window.py
git commit -m "feat: wire Contacts button into main window"
```

---

## Self-Review Notes

- **Spec coverage:** `tr064.py` fetch+parse (Task 1) ✓; FritzBox credential storage with distinct keyring key (Task 1) ✓; settings dialog fields (Task 2) ✓; `ContactsDialog` list+select+error-handling (Task 3) ✓; main window wiring (Task 4) ✓; manual verification against real FritzBox 7590 (Task 4, Step 6) ✓; testing approach (pure `parse_phonebook_xml` unit-tested, `get_phonebook` manual, config functions unit-tested, dialog unit-tested with monkeypatched `tr064.get_phonebook`) matches spec exactly ✓.
- **Placeholder scan:** none — every step has full code or concrete manual-verification instructions.
- **Type consistency:** `send_dtmf`-style precedent followed — `Contact(name, numbers)` fields match between `tr064.py` (Task 1) and `contacts_dialog.py`/`test_contacts_dialog.py` (Task 3). `ContactsDialog(host, parent=None)` constructor signature matches between Task 3's definition and Task 4's instantiation. `contactSelected` signal name and `str` payload type match between Task 3 and Task 4.
