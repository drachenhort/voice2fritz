# Google Contacts Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the user pull contacts from their Google account (Android phone) into voice2fritz's local phonebook, one-way, with a Settings toggle controlling whether Google or a manually-added local contact wins on a name conflict.

**Architecture:** `contacts.py` gains a `source` marker on each entry and a single diff-and-replace function implementing the priority rules. `config.py` gains a boolean setting for the priority toggle. A new `google_contacts.py` handles OAuth (via Google's official libraries) and fetches/groups Google contacts, then drives the diff-and-replace function per name. `ContactsDialog` gets a "Sync Google" button; `SettingsDialog` gets the priority checkbox.

**Tech Stack:** Python, PySide6 (existing stack). New dependencies: `google-auth`, `google-auth-oauthlib`, `google-api-python-client` — justified in the design spec (OAuth correctness/security over hand-rolling it).

## Global Constraints

- One-way sync only: Google → local. Nothing is ever pushed back to Google.
- `Contact.source` is `"local"` for manually-added entries, `"google"` for sync-created ones. Missing `source` in old `contacts.json` files defaults to `"local"`.
- Name-conflict priority is a Settings checkbox, default **checked** (Google wins, can overwrite a local contact with the same name) — this default was the user's explicit choice, not an assumption.
- `google_client_secret.json` and `google_token.json` live in `~/.config/voice2fritz/`, never committed to the repo (public on GitHub).
- No automated test for the real OAuth flow (`_get_credentials`) — requires a real browser and Google account, verified manually. The pagination/grouping (`_fetch_google_contacts`) and diff-and-replace orchestration (`_sync_from_grouped`, `contacts.sync_contact_for_name`) ARE unit-tested with fake/injected objects, no real network.

---

## File Structure

```
voice2fritz/
  src/voice2fritz/
    contacts.py                  (modified: source field, sync_contact_for_name)
    config.py                    (modified: priority setting)
    google_contacts.py           (new)
    gui/
      settings_dialog.py          (modified: priority checkbox)
      contacts_dialog.py          (modified: Sync Google button)
  pyproject.toml                 (modified: new dependencies)
  README.md / README.de.md       (modified: Google Cloud setup walkthrough)
  tests/
    test_contacts.py              (modified)
    test_config.py                (modified)
    test_settings_dialog.py       (modified)
    test_google_contacts.py       (new)
    test_contacts_dialog.py       (modified)
```

---

### Task 1: `Contact.source`, priority logic, priority setting

**Files:**
- Modify: `src/voice2fritz/contacts.py`
- Test: `tests/test_contacts.py`
- Modify: `src/voice2fritz/config.py`
- Test: `tests/test_config.py`
- Modify: `src/voice2fritz/gui/settings_dialog.py`
- Test: `tests/test_settings_dialog.py`

**Interfaces:**
- Produces:
  - `contacts.Contact(name: str, number: str, source: str = "local")`
  - `contacts.sync_contact_for_name(name: str, numbers: list[str], overwrite_local: bool, path=DEFAULT_CONTACTS_PATH) -> bool` — returns `True` if it changed anything.
  - `config.load_google_sync_overwrites_local(path=DEFAULT_CONFIG_PATH) -> bool` (default `True`)
  - `config.save_google_sync_overwrites_local(value: bool, path=DEFAULT_CONFIG_PATH) -> None`
  - `SettingsDialog.google_priority_checkbox: QCheckBox`

- [ ] **Step 1: Write the failing tests for `contacts.py`**

Add to `tests/test_contacts.py`'s import block:

```python
from voice2fritz.contacts import Contact, add_contact, delete_contact, load_contacts, save_contacts, sync_contact_for_name
```

Add these tests:

```python
def test_load_contacts_defaults_missing_source_to_local(tmp_path):
    import json

    path = tmp_path / "contacts.json"
    path.write_text(json.dumps([{"name": "Anna Schmidt", "number": "+4917612345678"}]))

    assert load_contacts(path) == [Contact(name="Anna Schmidt", number="+4917612345678", source="local")]


def test_sync_contact_for_name_adds_new_google_contact(tmp_path):
    path = tmp_path / "contacts.json"

    changed = sync_contact_for_name("Anna Schmidt", ["+4917612345678"], overwrite_local=True, path=path)

    assert changed is True
    assert load_contacts(path) == [Contact(name="Anna Schmidt", number="+4917612345678", source="google")]


def test_sync_contact_for_name_replaces_changed_google_numbers(tmp_path):
    path = tmp_path / "contacts.json"
    save_contacts([Contact(name="Anna Schmidt", number="+4917612345678", source="google")], path)

    changed = sync_contact_for_name("Anna Schmidt", ["+4917699999999"], overwrite_local=True, path=path)

    assert changed is True
    assert load_contacts(path) == [Contact(name="Anna Schmidt", number="+4917699999999", source="google")]


def test_sync_contact_for_name_noop_when_unchanged(tmp_path):
    path = tmp_path / "contacts.json"
    save_contacts([Contact(name="Anna Schmidt", number="+4917612345678", source="google")], path)

    changed = sync_contact_for_name("Anna Schmidt", ["+4917612345678"], overwrite_local=True, path=path)

    assert changed is False
    assert load_contacts(path) == [Contact(name="Anna Schmidt", number="+4917612345678", source="google")]


def test_sync_contact_for_name_local_wins_skips_entirely(tmp_path):
    path = tmp_path / "contacts.json"
    save_contacts([Contact(name="Anna Schmidt", number="+4917600000000", source="local")], path)

    changed = sync_contact_for_name("Anna Schmidt", ["+4917612345678"], overwrite_local=False, path=path)

    assert changed is False
    assert load_contacts(path) == [Contact(name="Anna Schmidt", number="+4917600000000", source="local")]


def test_sync_contact_for_name_google_wins_overwrites_local(tmp_path):
    path = tmp_path / "contacts.json"
    save_contacts([Contact(name="Anna Schmidt", number="+4917600000000", source="local")], path)

    changed = sync_contact_for_name("Anna Schmidt", ["+4917612345678"], overwrite_local=True, path=path)

    assert changed is True
    assert load_contacts(path) == [Contact(name="Anna Schmidt", number="+4917612345678", source="google")]


def test_sync_contact_for_name_ignores_number_order_for_noop_check(tmp_path):
    path = tmp_path / "contacts.json"
    save_contacts(
        [
            Contact(name="Anna Schmidt", number="+4917612345678", source="google"),
            Contact(name="Anna Schmidt", number="+4917698765432", source="google"),
        ],
        path,
    )

    changed = sync_contact_for_name("Anna Schmidt", ["+4917698765432", "+4917612345678"], overwrite_local=True, path=path)

    assert changed is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/pytest tests/test_contacts.py -v`
Expected: FAIL — `Contact(..., source=...)` raises `TypeError: unexpected keyword argument 'source'`, `sync_contact_for_name` doesn't exist.

- [ ] **Step 3: Update `src/voice2fritz/contacts.py`**

Replace the whole file:

```python
import json
from dataclasses import asdict, dataclass
from pathlib import Path

DEFAULT_CONTACTS_PATH = Path.home() / ".config" / "voice2fritz" / "contacts.json"


@dataclass
class Contact:
    name: str
    number: str
    source: str = "local"


def load_contacts(path: Path = DEFAULT_CONTACTS_PATH) -> list[Contact]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        return []
    return [
        Contact(name=item["name"], number=item["number"], source=item.get("source", "local"))
        for item in data
    ]


def save_contacts(contacts: list[Contact], path: Path = DEFAULT_CONTACTS_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([asdict(contact) for contact in contacts]))


def add_contact(name: str, number: str, path: Path = DEFAULT_CONTACTS_PATH) -> None:
    contacts = load_contacts(path)
    contacts.append(Contact(name=name, number=number))
    save_contacts(contacts, path)


def delete_contact(index: int, path: Path = DEFAULT_CONTACTS_PATH) -> None:
    contacts = load_contacts(path)
    if 0 <= index < len(contacts):
        del contacts[index]
        save_contacts(contacts, path)


def sync_contact_for_name(
    name: str,
    numbers: list[str],
    overwrite_local: bool,
    path: Path = DEFAULT_CONTACTS_PATH,
) -> bool:
    all_contacts = load_contacts(path)
    has_local = any(c.name == name and c.source == "local" for c in all_contacts)

    if has_local and not overwrite_local:
        return False

    existing_google_numbers = {c.number for c in all_contacts if c.name == name and c.source == "google"}

    if not has_local and existing_google_numbers == set(numbers):
        return False

    remaining = [c for c in all_contacts if c.name != name]
    remaining.extend(Contact(name=name, number=number, source="google") for number in numbers)
    save_contacts(remaining, path)
    return True
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/pytest tests/test_contacts.py -v`
Expected: PASS (14 passed: 7 existing + 7 new)

- [ ] **Step 5: Write the failing tests for `config.py`**

Add to `tests/test_config.py`'s import block:

```python
from voice2fritz.config import (
    ...,  # keep existing imports
    load_google_sync_overwrites_local,
    save_google_sync_overwrites_local,
)
```

Add these tests:

```python
def test_load_google_sync_overwrites_local_defaults_to_true(tmp_path):
    path = tmp_path / "does-not-exist.json"
    assert load_google_sync_overwrites_local(path) is True


def test_save_and_load_google_sync_overwrites_local_round_trip(tmp_path):
    path = tmp_path / "config.json"

    save_google_sync_overwrites_local(False, path)

    assert load_google_sync_overwrites_local(path) is False


def test_save_google_sync_overwrites_local_preserves_existing_account(tmp_path):
    path = tmp_path / "config.json"
    cfg = AccountConfig(host="fritz.box", username="user123")
    save_config(cfg, path)

    save_google_sync_overwrites_local(False, path)

    assert load_config(path) == cfg
    assert load_google_sync_overwrites_local(path) is False
```

- [ ] **Step 6: Run tests to verify they fail**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/pytest tests/test_config.py -v`
Expected: FAIL with `ImportError: cannot import name 'load_google_sync_overwrites_local'`

- [ ] **Step 7: Add the setting functions to `config.py`**

Add to `src/voice2fritz/config.py`, after `save_device_selection`:

```python
def load_google_sync_overwrites_local(path: Path = DEFAULT_CONFIG_PATH) -> bool:
    data = _read_raw(path)
    return data.get("google_sync_overwrites_local", True)


def save_google_sync_overwrites_local(value: bool, path: Path = DEFAULT_CONFIG_PATH) -> None:
    data = _read_raw(path)
    data["google_sync_overwrites_local"] = value
    _write_raw(data, path)
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/pytest tests/test_config.py -v`
Expected: PASS (all passing, no regressions)

- [ ] **Step 9: Write the failing test for the settings checkbox**

Add to `tests/test_settings_dialog.py`:

```python
def test_save_button_persists_google_priority_setting(qtbot, tmp_path, monkeypatch):
    saved_values = []

    monkeypatch.setattr(config, "save_config", lambda cfg, path=config.DEFAULT_CONFIG_PATH: None)
    monkeypatch.setattr(config, "set_password", lambda username, password: None)
    monkeypatch.setattr(config, "save_google_sync_overwrites_local", lambda value, path=config.DEFAULT_CONFIG_PATH: saved_values.append(value))

    dialog = SettingsDialog()
    qtbot.addWidget(dialog)

    dialog.host_edit.setText("fritz.box")
    dialog.username_edit.setText("user123")
    dialog.password_edit.setText("hunter2")
    dialog.google_priority_checkbox.setChecked(False)

    with qtbot.waitSignal(dialog.accountSaved, timeout=1000):
        dialog.save_button.click()

    assert saved_values == [False]
```

- [ ] **Step 10: Run test to verify it fails**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/pytest tests/test_settings_dialog.py -v -k google_priority`
Expected: FAIL with `AttributeError: 'SettingsDialog' object has no attribute 'google_priority_checkbox'`

- [ ] **Step 11: Add the checkbox to `SettingsDialog`**

In `src/voice2fritz/gui/settings_dialog.py`, add `QCheckBox` to the import:

```python
from PySide6.QtWidgets import QCheckBox, QDialog, QFormLayout, QLineEdit, QPushButton, QVBoxLayout
```

Add the checkbox after `self.save_button = QPushButton("Save")`:

```python
        self.google_priority_checkbox = QCheckBox("Google sync overwrites local contacts with the same name")
        self.google_priority_checkbox.setChecked(True)
```

Add it to the layout, after `layout.addLayout(form)`:

```python
        layout.addWidget(self.google_priority_checkbox)
```

(so `layout.addLayout(form)` is followed by `layout.addWidget(self.google_priority_checkbox)` then `layout.addWidget(self.save_button)`)

In `_on_save`, add before `self.accountSaved.emit(cfg)`:

```python
        config.save_google_sync_overwrites_local(self.google_priority_checkbox.isChecked())
```

- [ ] **Step 12: Run tests to verify they pass**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/pytest tests/test_settings_dialog.py -v`
Expected: PASS (2 passed)

- [ ] **Step 13: Run the full suite to confirm no regressions**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/pytest -v`
Expected: PASS, all passing, zero failing.

- [ ] **Step 14: Commit**

```bash
git add src/voice2fritz/contacts.py src/voice2fritz/config.py src/voice2fritz/gui/settings_dialog.py tests/test_contacts.py tests/test_config.py tests/test_settings_dialog.py
git commit -m "feat: add contact source tracking and Google-sync priority setting"
```

---

### Task 2: `google_contacts.py` — OAuth, fetch, sync orchestration

**Files:**
- Create: `src/voice2fritz/google_contacts.py`
- Test: `tests/test_google_contacts.py`
- Modify: `pyproject.toml`

**Interfaces:**
- Consumes: `contacts.sync_contact_for_name`, `contacts.DEFAULT_CONTACTS_PATH` (Task 1); `config.load_google_sync_overwrites_local` (Task 1).
- Produces:
  - `google_contacts.TOKEN_PATH`, `google_contacts.CLIENT_SECRET_PATH`, `google_contacts.SCOPES`
  - `google_contacts._get_credentials() -> Credentials` (no automated test — real OAuth)
  - `google_contacts._fetch_google_contacts(service) -> dict[str, list[str]]` (unit-tested)
  - `google_contacts._sync_from_grouped(grouped: dict[str, list[str]], overwrite_local: bool, path=contacts.DEFAULT_CONTACTS_PATH) -> int` (unit-tested)
  - `google_contacts.sync_google_contacts() -> int` (no automated test — calls the above, real OAuth + network)

- [ ] **Step 1: Add the new dependencies to `pyproject.toml`**

In `pyproject.toml`, change the `dependencies` list to:

```toml
dependencies = [
    "PySide6>=6.6",
    "keyring>=24",
    "google-auth>=2.30",
    "google-auth-oauthlib>=1.2",
    "google-api-python-client>=2.130",
]
```

Then install them:

```bash
.venv/bin/pip install -e ".[dev]"
```

- [ ] **Step 2: Write the failing tests**

```python
# tests/test_google_contacts.py
from voice2fritz.contacts import Contact, load_contacts, save_contacts
from voice2fritz.google_contacts import _fetch_google_contacts, _sync_from_grouped


class _FakeRequest:
    def __init__(self, page):
        self._page = page

    def execute(self):
        return self._page


class _FakeService:
    def __init__(self, pages_by_token):
        self._pages_by_token = pages_by_token

    def people(self):
        return self

    def connections(self):
        return self

    def list(self, resourceName, personFields, pageSize, pageToken=None):
        return _FakeRequest(self._pages_by_token[pageToken])


def test_fetch_google_contacts_paginates_and_groups_by_name():
    page0 = {
        "connections": [
            {"names": [{"displayName": "Anna Schmidt"}], "phoneNumbers": [{"value": "+4917612345678"}]},
        ],
        "nextPageToken": "tok1",
    }
    page1 = {
        "connections": [
            {"names": [{"displayName": "Anna Schmidt"}], "phoneNumbers": [{"value": "+4917698765432"}]},
            {"names": [{"displayName": "Ben Weber"}], "phoneNumbers": [{"value": "+4930123456"}]},
        ],
    }
    service = _FakeService({None: page0, "tok1": page1})

    result = _fetch_google_contacts(service)

    assert result == {
        "Anna Schmidt": ["+4917612345678", "+4917698765432"],
        "Ben Weber": ["+4930123456"],
    }


def test_fetch_google_contacts_skips_entries_without_name_or_number():
    page0 = {
        "connections": [
            {"names": [], "phoneNumbers": [{"value": "+4917612345678"}]},
            {"names": [{"displayName": "No Number"}], "phoneNumbers": []},
        ],
    }
    service = _FakeService({None: page0})

    assert _fetch_google_contacts(service) == {}


def test_sync_from_grouped_adds_and_counts_changes(tmp_path):
    path = tmp_path / "contacts.json"
    grouped = {"Anna Schmidt": ["+4917612345678"], "Ben Weber": ["+4930123456"]}

    count = _sync_from_grouped(grouped, overwrite_local=True, path=path)

    assert count == 2
    assert load_contacts(path) == [
        Contact(name="Anna Schmidt", number="+4917612345678", source="google"),
        Contact(name="Ben Weber", number="+4930123456", source="google"),
    ]


def test_sync_from_grouped_skips_local_wins_names(tmp_path):
    path = tmp_path / "contacts.json"
    save_contacts([Contact(name="Anna Schmidt", number="+4917600000000", source="local")], path)
    grouped = {"Anna Schmidt": ["+4917612345678"]}

    count = _sync_from_grouped(grouped, overwrite_local=False, path=path)

    assert count == 0
    assert load_contacts(path) == [Contact(name="Anna Schmidt", number="+4917600000000", source="local")]
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/pytest tests/test_google_contacts.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'voice2fritz.google_contacts'`

- [ ] **Step 4: Write `src/voice2fritz/google_contacts.py`**

```python
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from voice2fritz import config, contacts

TOKEN_PATH = Path.home() / ".config" / "voice2fritz" / "google_token.json"
CLIENT_SECRET_PATH = Path.home() / ".config" / "voice2fritz" / "google_client_secret.json"
SCOPES = ["https://www.googleapis.com/auth/contacts.readonly"]


def _get_credentials() -> Credentials:
    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())

    if not creds or not creds.valid:
        if not CLIENT_SECRET_PATH.exists():
            raise FileNotFoundError(
                f"Google client secret not found at {CLIENT_SECRET_PATH}. "
                "See the README for how to create one."
            )
        flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET_PATH), SCOPES)
        creds = flow.run_local_server(port=0)

    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(creds.to_json())
    return creds


def _fetch_google_contacts(service) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    page_token = None

    while True:
        response = (
            service.people()
            .connections()
            .list(
                resourceName="people/me",
                personFields="names,phoneNumbers",
                pageSize=1000,
                pageToken=page_token,
            )
            .execute()
        )

        for person in response.get("connections", []):
            names = person.get("names") or []
            phone_numbers = person.get("phoneNumbers") or []
            if not names or not phone_numbers:
                continue
            name = names[0].get("displayName", "")
            numbers = [pn["value"] for pn in phone_numbers if pn.get("value")]
            if name and numbers:
                grouped.setdefault(name, []).extend(numbers)

        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return grouped


def _sync_from_grouped(
    grouped: dict[str, list[str]],
    overwrite_local: bool,
    path: Path = contacts.DEFAULT_CONTACTS_PATH,
) -> int:
    changed = 0
    for name, numbers in grouped.items():
        if contacts.sync_contact_for_name(name, numbers, overwrite_local, path):
            changed += 1
    return changed


def sync_google_contacts() -> int:
    creds = _get_credentials()
    service = build("people", "v1", credentials=creds)
    grouped = _fetch_google_contacts(service)
    overwrite_local = config.load_google_sync_overwrites_local()
    return _sync_from_grouped(grouped, overwrite_local)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/pytest tests/test_google_contacts.py -v`
Expected: PASS (4 passed)

- [ ] **Step 6: Run the full suite to confirm no regressions**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/pytest -v`
Expected: PASS, all passing, zero failing.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml src/voice2fritz/google_contacts.py tests/test_google_contacts.py
git commit -m "feat: fetch and merge Google contacts via People API"
```

---

### Task 3: Wire "Sync Google" into `ContactsDialog`, README setup docs, manual verification

**Files:**
- Modify: `src/voice2fritz/gui/contacts_dialog.py`
- Test: `tests/test_contacts_dialog.py`
- Modify: `README.md`, `README.de.md`

**Interfaces:**
- Consumes: `google_contacts.sync_google_contacts` (Task 2).
- Produces: `ContactsDialog.sync_button: QPushButton`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_contacts_dialog.py`:

```python
def test_sync_button_reloads_list_on_success(qtbot, monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    from voice2fritz.gui import contacts_dialog as contacts_dialog_module

    monkeypatch.setattr(
        contacts_module,
        "load_contacts",
        lambda path=contacts_module.DEFAULT_CONTACTS_PATH: [contacts_module.Contact(name="Anna Schmidt", number="+4917612345678", source="google")],
    )
    monkeypatch.setattr(contacts_dialog_module.google_contacts, "sync_google_contacts", lambda: 1)
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)

    dialog = ContactsDialog()
    qtbot.addWidget(dialog)

    dialog.sync_button.click()

    assert dialog.contact_list.count() == 1
    assert dialog.contact_list.item(0).text() == "Anna Schmidt — +4917612345678"


def test_sync_button_shows_warning_on_failure(qtbot, monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    from voice2fritz.gui import contacts_dialog as contacts_dialog_module

    monkeypatch.setattr(contacts_module, "load_contacts", lambda path=contacts_module.DEFAULT_CONTACTS_PATH: [])

    def raise_error():
        raise ValueError("auth failed")

    monkeypatch.setattr(contacts_dialog_module.google_contacts, "sync_google_contacts", raise_error)
    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: warnings.append(a))

    dialog = ContactsDialog()
    qtbot.addWidget(dialog)

    dialog.sync_button.click()

    assert len(warnings) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/pytest tests/test_contacts_dialog.py -v -k sync_button`
Expected: FAIL with `AttributeError: 'ContactsDialog' object has no attribute 'sync_button'`

- [ ] **Step 3: Wire the button in `ContactsDialog`**

In `src/voice2fritz/gui/contacts_dialog.py`, update the imports:

```python
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from voice2fritz import contacts as contacts_module
from voice2fritz import google_contacts
```

Add `self.sync_button = QPushButton("Sync Google")` right after
`self.select_button = QPushButton("Select")`, and add it to `button_row`:

```python
        button_row.addWidget(self.sync_button)
```

Connect it in the signal-connection block:

```python
        self.sync_button.clicked.connect(self._on_sync_clicked)
```

Add the handler, next to `_on_delete_clicked`:

```python
    def _on_sync_clicked(self) -> None:
        try:
            count = google_contacts.sync_google_contacts()
        except Exception as exc:
            QMessageBox.warning(self, "Contacts", f"Could not sync Google contacts: {exc}")
            return
        self._reload_list()
        QMessageBox.information(self, "Contacts", f"{count} contact(s) added or updated.")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/pytest tests/test_contacts_dialog.py -v`
Expected: PASS, all tests in the file.

- [ ] **Step 5: Run the full suite to confirm no regressions**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/pytest -v`
Expected: PASS, all passing, zero failing.

- [ ] **Step 6: Add the Google Cloud setup walkthrough to `README.md`**

Add a new section to `README.md`, after the existing pjsua2 build section:

```markdown
## Setting up Google Contacts sync (optional)

1. Go to the [Google Cloud Console](https://console.cloud.google.com/),
   create a new project (or reuse one).
2. Enable the **People API** for that project (APIs & Services → Library
   → search "People API" → Enable).
3. Go to APIs & Services → Credentials → Create Credentials → OAuth
   client ID. Choose application type **Desktop app**.
4. Download the resulting JSON file and save it as
   `~/.config/voice2fritz/google_client_secret.json`.
5. In voice2fritz, open Contacts → Sync Google. The first sync opens
   your browser for Google's consent screen; approve it. A token is
   saved to `~/.config/voice2fritz/google_token.json` so later syncs
   don't need the browser again.

Both files are local-only and never committed to source control — treat
`google_token.json` like a password, since it holds a refresh token for
your Google account.
```

- [ ] **Step 7: Add the same section to `README.de.md`**

```markdown
## Google-Kontakte-Synchronisation einrichten (optional)

1. In der [Google Cloud Console](https://console.cloud.google.com/) ein
   neues Projekt anlegen (oder ein bestehendes verwenden).
2. Für dieses Projekt die **People API** aktivieren (APIs & Dienste →
   Bibliothek → "People API" suchen → Aktivieren).
3. APIs & Dienste → Anmeldedaten → Anmeldedaten erstellen → OAuth-Client-ID.
   Anwendungstyp **Desktop-App** wählen.
4. Die heruntergeladene JSON-Datei unter
   `~/.config/voice2fritz/google_client_secret.json` speichern.
5. In voice2fritz: Kontakte → Sync Google öffnen. Beim ersten Sync öffnet
   sich der Browser für die Google-Zustimmung; bestätigen. Ein Token wird
   unter `~/.config/voice2fritz/google_token.json` gespeichert, damit
   spätere Syncs ohne Browser auskommen.

Beide Dateien bleiben lokal und werden nie ins Repository übernommen –
`google_token.json` wie ein Passwort behandeln, da es ein Refresh-Token
für den Google-Account enthält.
```

- [ ] **Step 8: Manual verification against a real Google account**

1. Follow the README walkthrough just added: create the Google Cloud
   project, enable the People API, create the Desktop app OAuth client,
   download `client_secret.json` to
   `~/.config/voice2fritz/google_client_secret.json`.
2. Run `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/python -m voice2fritz.main`.
3. Open Contacts, click "Sync Google". Confirm the browser opens for
   consent; approve it.
4. Confirm real Google contacts (from the Android phone's account)
   appear in the list with correct names/numbers.
5. Change a contact's phone number on the phone (or in Google Contacts
   directly), run Sync Google again, confirm the local entry's number
   updates rather than creating a duplicate row.
6. With the Settings checkbox checked (Google wins, default): add a
   local contact with the same name as an existing Google contact,
   sync, confirm the local entry gets replaced by the Google one.
7. Uncheck the Settings checkbox (local wins): repeat step 6, confirm
   the local entry survives unchanged and no Google-sourced entry for
   that name appears.
8. Run Sync Google a second time with no changes on the Google side;
   confirm no duplicate rows appear (idempotency).

If any step reveals a mismatch between the real People API response
shape and what `_fetch_google_contacts` expects, adjust it accordingly —
expected verification work against a real account, not a plan defect,
consistent with `sip_engine.py`'s and `tr064.py`'s equivalent notes.

- [ ] **Step 9: Commit**

```bash
git add src/voice2fritz/gui/contacts_dialog.py tests/test_contacts_dialog.py README.md README.de.md
git commit -m "feat: wire Sync Google button into Contacts dialog, document setup"
```

---

## Self-Review Notes

- **Spec coverage:** `source` field + backward-compat default (Task 1) ✓; `sync_contact_for_name` implementing all priority rules including the no-op/idempotency case (Task 1) ✓; priority setting + Settings checkbox, default checked (Task 1) ✓; OAuth flow, token caching, People API fetch/pagination/grouping (Task 2) ✓; new dependencies with justification (Task 2) ✓; diff-and-replace orchestration (Task 2) ✓; Sync Google button + error handling (Task 3) ✓; README setup walkthrough in both languages (Task 3) ✓; manual verification covering update-detection, both priority settings, and idempotency (Task 3, Step 8) ✓.
- **Placeholder scan:** none — every step has full code, full test code, or concrete manual-verification instructions.
- **Type consistency:** `sync_contact_for_name(name, numbers, overwrite_local, path)` signature matches identically between Task 1's definition, Task 2's `_sync_from_grouped` call site, and all tests. `_fetch_google_contacts(service) -> dict[str, list[str]]` return shape matches between Task 2's definition and `_sync_from_grouped`'s consumption of it. `Contact(name, number, source)` field names/defaults match across `contacts.py`, `google_contacts.py`, and all three modified/new test files.
