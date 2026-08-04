# Contacts Tab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "Contacts" tab alongside "Call Log" in the dock, so contacts
are reachable inline without opening the modal dialog. The modal dialog
(via the Contacts nav button) keeps working unchanged.

**Architecture:** Extract `ContactsDialog`'s content/logic into a new
`ContactsPanel(QWidget)`. `ContactsDialog` becomes a thin wrapper embedding
`ContactsPanel`, closing itself on selection. `MainWindow` wraps
`log_panel` and a new `contacts_panel` in a `QTabWidget` as the dock's
widget.

**Tech Stack:** PySide6 (QWidget/QDialog/QTabWidget), pytest + pytest-qt.

## Global Constraints

- `ContactsDialog`'s outward behavior (title, size, `contactSelected`
  signal, select-and-close) is unchanged from the caller's perspective.
- No change to `contacts.py` / `google_contacts.py` / data model.
- Existing `MainWindow` attributes (`log_panel`, `log_dock`,
  `contacts_button`) keep their names; `log_dock`'s widget changes from
  `CallLogPanel` directly to a `QTabWidget` containing it.
- `LD_LIBRARY_PATH=$HOME/.local/lib/pjsip` required for every pytest run.

---

### Task 1: Extract `ContactsPanel(QWidget)`

**Files:**
- Create: `src/voice2fritz/gui/contacts_panel.py`
- Test: `tests/test_contacts_panel.py`

**Interfaces:**
- Produces: `ContactsPanel(QWidget)` with `contactSelected = Signal(str)`,
  and attributes `contact_table`, `sort_combo`, `name_edit`, `type_edit`,
  `number_edit`, `add_button`, `delete_button`, `select_button`,
  `sync_button` — same names as `ContactsDialog` has today, so Task 2 can
  reuse them by delegation.
- Consumes: `voice2fritz.config`, `voice2fritz.contacts`,
  `voice2fritz.google_contacts` — same as the current dialog.

- [ ] **Step 1: Create the test file**

Create `tests/test_contacts_panel.py` — copy every test from
`tests/test_contacts_dialog.py` verbatim, with these substitutions:
- `from voice2fritz.gui.contacts_dialog import ContactsDialog` →
  `from voice2fritz.gui.contacts_panel import ContactsPanel`
- Every `ContactsDialog()` construction → `ContactsPanel()`
- Every local variable named `dialog` → `panel` (including the
  `_row_texts(dialog, row)` helper → `_row_texts(panel, row)`)
- Drop `test_double_click_emits_selected_number_and_closes`'s name — keep
  the test but rename it `test_double_click_emits_selected_number` since
  there's no dialog to close; the body (constructing, calling
  `_on_item_activated`, asserting `blocker.args`) is otherwise identical.
- `test_select_uses_sorted_row_not_storage_order` stays as-is (no close
  assertion in it already).

The full resulting file:

```python
import pytest

from voice2fritz import config as config_module
from voice2fritz import contacts as contacts_module
from voice2fritz.gui.contacts_panel import ContactsPanel


@pytest.fixture(autouse=True)
def no_sort_order_persistence(monkeypatch):
    monkeypatch.setattr(config_module, "load_contacts_sort_order", lambda path=config_module.DEFAULT_CONFIG_PATH: "name")
    monkeypatch.setattr(config_module, "save_contacts_sort_order", lambda value, path=config_module.DEFAULT_CONFIG_PATH: None)


def _row_texts(panel, row):
    return (
        panel.contact_table.item(row, 0).text(),
        panel.contact_table.item(row, 1).text(),
        panel.contact_table.item(row, 2).text(),
    )


def test_populates_table_from_stored_contacts(qtbot, monkeypatch):
    monkeypatch.setattr(
        contacts_module,
        "load_contacts",
        lambda path=contacts_module.DEFAULT_CONTACTS_PATH: [
            contacts_module.Contact(name="Anna Schmidt", number="+4917612345678", number_type="mobile"),
            contacts_module.Contact(name="Ben Weber", number="+4930123456"),
        ],
    )

    panel = ContactsPanel()
    qtbot.addWidget(panel)

    assert panel.contact_table.rowCount() == 2
    assert _row_texts(panel, 0) == ("Anna Schmidt", "mobile", "+4917612345678")
    assert _row_texts(panel, 1) == ("Ben Weber", "", "+4930123456")


def test_double_click_emits_selected_number(qtbot, monkeypatch):
    monkeypatch.setattr(
        contacts_module,
        "load_contacts",
        lambda path=contacts_module.DEFAULT_CONTACTS_PATH: [contacts_module.Contact(name="Anna Schmidt", number="+4917612345678")],
    )

    panel = ContactsPanel()
    qtbot.addWidget(panel)

    with qtbot.waitSignal(panel.contactSelected, timeout=1000) as blocker:
        panel._on_item_activated(panel.contact_table.item(0, 0))

    assert blocker.args == ["+4917612345678"]


def test_add_button_adds_contact_and_reloads_table(qtbot, monkeypatch):
    monkeypatch.setattr(contacts_module, "load_contacts", lambda path=contacts_module.DEFAULT_CONTACTS_PATH: [])
    added = []
    monkeypatch.setattr(
        contacts_module,
        "add_contact",
        lambda name, number, number_type="", path=contacts_module.DEFAULT_CONTACTS_PATH: added.append((name, number, number_type)),
    )

    panel = ContactsPanel()
    qtbot.addWidget(panel)

    panel.name_edit.setText("Anna Schmidt")
    panel.number_edit.setText("+4917612345678")
    panel.type_edit.setText("mobile")
    panel.add_button.click()

    assert added == [("Anna Schmidt", "+4917612345678", "mobile")]
    assert panel.name_edit.text() == ""
    assert panel.number_edit.text() == ""
    assert panel.type_edit.text() == ""


def test_add_button_works_without_type(qtbot, monkeypatch):
    monkeypatch.setattr(contacts_module, "load_contacts", lambda path=contacts_module.DEFAULT_CONTACTS_PATH: [])
    added = []
    monkeypatch.setattr(
        contacts_module,
        "add_contact",
        lambda name, number, number_type="", path=contacts_module.DEFAULT_CONTACTS_PATH: added.append((name, number, number_type)),
    )

    panel = ContactsPanel()
    qtbot.addWidget(panel)

    panel.name_edit.setText("Anna Schmidt")
    panel.number_edit.setText("+4917612345678")
    panel.add_button.click()

    assert added == [("Anna Schmidt", "+4917612345678", "")]


def test_add_button_does_nothing_with_empty_fields(qtbot, monkeypatch):
    monkeypatch.setattr(contacts_module, "load_contacts", lambda path=contacts_module.DEFAULT_CONTACTS_PATH: [])
    added = []
    monkeypatch.setattr(
        contacts_module,
        "add_contact",
        lambda name, number, number_type="", path=contacts_module.DEFAULT_CONTACTS_PATH: added.append((name, number, number_type)),
    )

    panel = ContactsPanel()
    qtbot.addWidget(panel)

    panel.add_button.click()

    assert added == []


def test_delete_button_removes_selected_contact(qtbot, monkeypatch):
    contact = contacts_module.Contact(name="Anna Schmidt", number="+4917612345678")
    monkeypatch.setattr(contacts_module, "load_contacts", lambda path=contacts_module.DEFAULT_CONTACTS_PATH: [contact])
    deleted = []
    monkeypatch.setattr(contacts_module, "delete_contact_by_value", lambda c, path=contacts_module.DEFAULT_CONTACTS_PATH: deleted.append(c))

    panel = ContactsPanel()
    qtbot.addWidget(panel)

    panel.contact_table.setCurrentCell(0, 0)
    panel.delete_button.click()

    assert deleted == [contact]


def test_table_sorted_by_name_by_default(qtbot, monkeypatch):
    monkeypatch.setattr(
        contacts_module,
        "load_contacts",
        lambda path=contacts_module.DEFAULT_CONTACTS_PATH: [
            contacts_module.Contact(name="Ben Weber", number="+4930123456"),
            contacts_module.Contact(name="Anna Schmidt", number="+4917612345678"),
        ],
    )

    panel = ContactsPanel()
    qtbot.addWidget(panel)

    assert _row_texts(panel, 0) == ("Anna Schmidt", "", "+4917612345678")
    assert _row_texts(panel, 1) == ("Ben Weber", "", "+4930123456")


def test_switching_sort_to_number_resorts_table_and_persists(qtbot, monkeypatch):
    monkeypatch.setattr(
        contacts_module,
        "load_contacts",
        lambda path=contacts_module.DEFAULT_CONTACTS_PATH: [
            contacts_module.Contact(name="Ben Weber", number="+4930123456"),
            contacts_module.Contact(name="Anna Schmidt", number="+4917612345678"),
        ],
    )
    saved = []
    monkeypatch.setattr(config_module, "save_contacts_sort_order", lambda value, path=config_module.DEFAULT_CONFIG_PATH: saved.append(value))

    panel = ContactsPanel()
    qtbot.addWidget(panel)

    panel.sort_combo.setCurrentIndex(panel.sort_combo.findData("number"))

    assert saved == ["number"]
    assert _row_texts(panel, 0) == ("Anna Schmidt", "", "+4917612345678")
    assert _row_texts(panel, 1) == ("Ben Weber", "", "+4930123456")


def test_sort_combo_initialized_from_saved_setting(qtbot, monkeypatch):
    monkeypatch.setattr(config_module, "load_contacts_sort_order", lambda path=config_module.DEFAULT_CONFIG_PATH: "number")
    monkeypatch.setattr(contacts_module, "load_contacts", lambda path=contacts_module.DEFAULT_CONTACTS_PATH: [])

    panel = ContactsPanel()
    qtbot.addWidget(panel)

    assert panel.sort_combo.currentData() == "number"


def test_select_uses_sorted_row_not_storage_order(qtbot, monkeypatch):
    monkeypatch.setattr(
        contacts_module,
        "load_contacts",
        lambda path=contacts_module.DEFAULT_CONTACTS_PATH: [
            contacts_module.Contact(name="Ben Weber", number="+4930123456"),
            contacts_module.Contact(name="Anna Schmidt", number="+4917612345678"),
        ],
    )

    panel = ContactsPanel()
    qtbot.addWidget(panel)

    with qtbot.waitSignal(panel.contactSelected, timeout=1000) as blocker:
        panel._on_item_activated(panel.contact_table.item(0, 0))

    assert blocker.args == ["+4917612345678"]


def test_sync_button_reloads_table_on_success(qtbot, monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    from voice2fritz.gui import contacts_panel as contacts_panel_module

    monkeypatch.setattr(
        contacts_module,
        "load_contacts",
        lambda path=contacts_module.DEFAULT_CONTACTS_PATH: [
            contacts_module.Contact(name="Anna Schmidt", number="+4917612345678", source="google", number_type="mobile")
        ],
    )
    monkeypatch.setattr(contacts_panel_module.google_contacts, "sync_google_contacts", lambda: 1)
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)

    panel = ContactsPanel()
    qtbot.addWidget(panel)

    panel.sync_button.click()

    assert panel.contact_table.rowCount() == 1
    assert _row_texts(panel, 0) == ("Anna Schmidt", "mobile", "+4917612345678")


def test_sync_button_shows_warning_on_failure(qtbot, monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    from voice2fritz.gui import contacts_panel as contacts_panel_module

    monkeypatch.setattr(contacts_module, "load_contacts", lambda path=contacts_module.DEFAULT_CONTACTS_PATH: [])

    def raise_error():
        raise ValueError("auth failed")

    monkeypatch.setattr(contacts_panel_module.google_contacts, "sync_google_contacts", raise_error)
    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: warnings.append(a))

    panel = ContactsPanel()
    qtbot.addWidget(panel)

    panel.sync_button.click()

    assert len(warnings) == 1
```

- [ ] **Step 2: Run to verify these fail (module doesn't exist yet)**

Run: `LD_LIBRARY_PATH=$HOME/.local/lib/pjsip pytest tests/test_contacts_panel.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'voice2fritz.gui.contacts_panel'`

- [ ] **Step 3: Create `contacts_panel.py`**

This is `ContactsDialog`'s current body with the class changed from
`QDialog` to `QWidget`, `contactSelected.emit(...)` kept, and `self.accept()`
removed from `_select_row` (no dialog to close):

```python
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from voice2fritz import config, contacts as contacts_module
from voice2fritz import google_contacts


class ContactsPanel(QWidget):
    contactSelected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._displayed_contacts: list[contacts_module.Contact] = []

        self.contact_table = QTableWidget(0, 3)
        self.contact_table.setHorizontalHeaderLabels(["Name", "Type", "Number"])
        self.contact_table.verticalHeader().setVisible(False)
        self.contact_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.contact_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.contact_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        header = self.contact_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)

        sort_label = QLabel("Sort by:")
        self.sort_combo = QComboBox()
        self.sort_combo.addItem("Name", "name")
        self.sort_combo.addItem("Number", "number")
        current_sort = config.load_contacts_sort_order()
        self.sort_combo.setCurrentIndex(self.sort_combo.findData(current_sort))

        sort_row = QHBoxLayout()
        sort_row.addWidget(sort_label)
        sort_row.addWidget(self.sort_combo)
        sort_row.addStretch()

        add_label = QLabel("Add contact")
        add_label.setObjectName("sectionLabel")

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Name")
        self.type_edit = QLineEdit()
        self.type_edit.setPlaceholderText("Type (optional)")
        self.number_edit = QLineEdit()
        self.number_edit.setPlaceholderText("Number")
        self.add_button = QPushButton("Add")
        self.add_button.setObjectName("addButton")

        add_row = QHBoxLayout()
        add_row.addWidget(self.name_edit)
        add_row.addWidget(self.type_edit)
        add_row.addWidget(self.number_edit)
        add_row.addWidget(self.add_button)

        self.delete_button = QPushButton("Delete")
        self.delete_button.setObjectName("deleteButton")
        self.select_button = QPushButton("Select")
        self.sync_button = QPushButton("Sync Google")

        button_row = QHBoxLayout()
        button_row.addWidget(self.delete_button)
        button_row.addWidget(self.select_button)
        button_row.addStretch()
        button_row.addWidget(self.sync_button)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.addLayout(sort_row)
        layout.addWidget(self.contact_table)
        layout.addWidget(add_label)
        layout.addLayout(add_row)
        layout.addLayout(button_row)

        self.contact_table.itemDoubleClicked.connect(self._on_item_activated)
        self.sort_combo.currentIndexChanged.connect(self._on_sort_changed)
        self.add_button.clicked.connect(self._on_add_clicked)
        self.delete_button.clicked.connect(self._on_delete_clicked)
        self.select_button.clicked.connect(self._on_select_clicked)
        self.sync_button.clicked.connect(self._on_sync_clicked)

        self._reload_list()

    def _sort_key(self, contact: contacts_module.Contact):
        field = self.sort_combo.currentData()
        if field == "number":
            return contact.number
        return contact.name.lower()

    def _reload_list(self) -> None:
        self._displayed_contacts = sorted(contacts_module.load_contacts(), key=self._sort_key)
        self.contact_table.setRowCount(len(self._displayed_contacts))
        for row, contact in enumerate(self._displayed_contacts):
            self.contact_table.setItem(row, 0, QTableWidgetItem(contact.name))
            self.contact_table.setItem(row, 1, QTableWidgetItem(contact.number_type))
            self.contact_table.setItem(row, 2, QTableWidgetItem(contact.number))

    def _on_sort_changed(self, index: int) -> None:
        config.save_contacts_sort_order(self.sort_combo.currentData())
        self._reload_list()

    def _on_add_clicked(self) -> None:
        name = self.name_edit.text().strip()
        number = self.number_edit.text().strip()
        number_type = self.type_edit.text().strip()
        if name and number:
            contacts_module.add_contact(name, number, number_type=number_type)
            self.name_edit.clear()
            self.number_edit.clear()
            self.type_edit.clear()
            self._reload_list()

    def _on_delete_clicked(self) -> None:
        row = self.contact_table.currentRow()
        if row >= 0:
            contacts_module.delete_contact_by_value(self._displayed_contacts[row])
            self._reload_list()

    def _on_sync_clicked(self) -> None:
        try:
            count = google_contacts.sync_google_contacts()
        except Exception as exc:
            QMessageBox.warning(self, "Contacts", f"Could not sync Google contacts: {exc}")
            return
        self._reload_list()
        QMessageBox.information(self, "Contacts", f"{count} contact(s) added or updated.")

    def _on_item_activated(self, item: QTableWidgetItem) -> None:
        self._select_row(item.row())

    def _on_select_clicked(self) -> None:
        row = self.contact_table.currentRow()
        if row >= 0:
            self._select_row(row)

    def _select_row(self, row: int) -> None:
        contact = self._displayed_contacts[row]
        self.contactSelected.emit(contact.number)
```

- [ ] **Step 4: Run to verify pass**

Run: `LD_LIBRARY_PATH=$HOME/.local/lib/pjsip pytest tests/test_contacts_panel.py -v`
Expected: PASS (14 tests)

- [ ] **Step 5: Commit**

```bash
git add src/voice2fritz/gui/contacts_panel.py tests/test_contacts_panel.py
git commit -m "feat: extract ContactsPanel widget from ContactsDialog"
```

---

### Task 2: `ContactsDialog` becomes a thin wrapper around `ContactsPanel`

**Files:**
- Modify: `src/voice2fritz/gui/contacts_dialog.py`
- Test: `tests/test_contacts_dialog.py`

**Interfaces:**
- Consumes: `ContactsPanel` (Task 1).
- Produces: `ContactsDialog` keeps `contactSelected = Signal(str)`,
  `setWindowTitle("Contacts")`, `resize(480, 480)`. Delegates all its
  former attributes (`contact_table`, `sort_combo`, `name_edit`, etc.) to
  `self.panel.<attr>` so existing external references (including this
  file's own tests) keep working without call-site changes elsewhere.

- [ ] **Step 1: Rewrite `contacts_dialog.py`**

```python
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDialog, QVBoxLayout

from voice2fritz.gui.contacts_panel import ContactsPanel


class ContactsDialog(QDialog):
    contactSelected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Contacts")
        self.resize(480, 480)

        self.panel = ContactsPanel()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.panel)

        self.panel.contactSelected.connect(self._on_contact_selected)

        # Kept for existing tests / call sites that reach through the
        # dialog directly instead of via self.panel.
        self.contact_table = self.panel.contact_table
        self.sort_combo = self.panel.sort_combo
        self.name_edit = self.panel.name_edit
        self.type_edit = self.panel.type_edit
        self.number_edit = self.panel.number_edit
        self.add_button = self.panel.add_button
        self.delete_button = self.panel.delete_button
        self.select_button = self.panel.select_button
        self.sync_button = self.panel.sync_button

    def _on_item_activated(self, item) -> None:
        self.panel._on_item_activated(item)

    def _on_contact_selected(self, number: str) -> None:
        self.contactSelected.emit(number)
        self.accept()
```

Note: `_on_item_activated` is kept as a thin delegate because
`test_double_click_emits_selected_number_and_closes` (Step 2 below) calls
`dialog._on_item_activated(...)` directly, same as the pre-existing test
did.

- [ ] **Step 2: Update `tests/test_contacts_dialog.py`**

Replace the whole file — same tests as before, but trimmed to only what's
specific to the dialog wrapper (open/close/forwarding behavior); the
content tests (table population, add/delete/sort/sync) now live in
`test_contacts_panel.py` from Task 1 and don't need duplicating here:

```python
import pytest

from voice2fritz import config as config_module
from voice2fritz import contacts as contacts_module
from voice2fritz.gui.contacts_dialog import ContactsDialog


@pytest.fixture(autouse=True)
def no_sort_order_persistence(monkeypatch):
    monkeypatch.setattr(config_module, "load_contacts_sort_order", lambda path=config_module.DEFAULT_CONFIG_PATH: "name")
    monkeypatch.setattr(config_module, "save_contacts_sort_order", lambda value, path=config_module.DEFAULT_CONFIG_PATH: None)


def test_wraps_a_contacts_panel_with_populated_table(qtbot, monkeypatch):
    monkeypatch.setattr(
        contacts_module,
        "load_contacts",
        lambda path=contacts_module.DEFAULT_CONTACTS_PATH: [
            contacts_module.Contact(name="Anna Schmidt", number="+4917612345678", number_type="mobile"),
        ],
    )

    dialog = ContactsDialog()
    qtbot.addWidget(dialog)

    assert dialog.contact_table.rowCount() == 1
    assert dialog.contact_table.item(0, 0).text() == "Anna Schmidt"


def test_double_click_emits_selected_number_and_closes(qtbot, monkeypatch):
    monkeypatch.setattr(
        contacts_module,
        "load_contacts",
        lambda path=contacts_module.DEFAULT_CONTACTS_PATH: [contacts_module.Contact(name="Anna Schmidt", number="+4917612345678")],
    )

    dialog = ContactsDialog()
    qtbot.addWidget(dialog)
    dialog.show()

    with qtbot.waitSignal(dialog.contactSelected, timeout=1000) as blocker:
        dialog._on_item_activated(dialog.contact_table.item(0, 0))

    assert blocker.args == ["+4917612345678"]
    assert not dialog.isVisible()
```

- [ ] **Step 3: Run tests**

Run: `LD_LIBRARY_PATH=$HOME/.local/lib/pjsip pytest tests/test_contacts_dialog.py tests/test_contacts_panel.py -v`
Expected: PASS (2 + 14 tests)

- [ ] **Step 4: Run the full test suite**

Run: `LD_LIBRARY_PATH=$HOME/.local/lib/pjsip pytest`
Expected: PASS, no regressions (checks `main.py` and anything else that
imports `ContactsDialog` still works — it does, constructor signature and
`contactSelected` signal are unchanged).

- [ ] **Step 5: Commit**

```bash
git add src/voice2fritz/gui/contacts_dialog.py tests/test_contacts_dialog.py
git commit -m "refactor: ContactsDialog wraps ContactsPanel instead of owning content"
```

---

### Task 3: Wire the Contacts tab into `MainWindow`

**Files:**
- Modify: `src/voice2fritz/gui/main_window.py`
- Test: `tests/test_main_window.py`

**Interfaces:**
- Consumes: `ContactsPanel` (Task 1).
- Produces: `MainWindow.contacts_panel: ContactsPanel` (new attribute,
  parallel to the existing `log_panel`). `log_dock`'s widget becomes a
  `QTabWidget`; `MainWindow.log_dock` and `MainWindow.log_panel` keep
  their names and behavior.

- [ ] **Step 1: Add the import**

In `main_window.py`, alongside the existing
`from voice2fritz.gui.contacts_dialog import ContactsDialog` line, add:

```python
from voice2fritz.gui.contacts_panel import ContactsPanel
```

- [ ] **Step 2: Replace the dock-construction block**

Current code (around where `self.log_panel = CallLogPanel()` through
`self.log_panel.entryActivated.connect(self.number_edit.setText)` sits):

```python
        self.log_panel = CallLogPanel()
        self.log_dock = QDockWidget("Call Log", self)
        self.log_dock.setWidget(self.log_panel)
        self.log_dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        self.log_dock.setFixedWidth(260)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.log_dock)
        self.log_panel.entryActivated.connect(self.number_edit.setText)
```

Replace with:

```python
        self.log_panel = CallLogPanel()
        self.contacts_panel = ContactsPanel()

        self.log_tabs = QTabWidget()
        self.log_tabs.addTab(self.log_panel, "Call Log")
        self.log_tabs.addTab(self.contacts_panel, "Contacts")

        self.log_dock = QDockWidget("", self)
        self.log_dock.setWidget(self.log_tabs)
        self.log_dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        self.log_dock.setFixedWidth(260)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.log_dock)

        self.log_panel.entryActivated.connect(self.number_edit.setText)
        self.contacts_panel.contactSelected.connect(self.number_edit.setText)
```

- [ ] **Step 3: Add `QTabWidget` to the imports**

At the top of `main_window.py`, add `QTabWidget` to the existing
`from PySide6.QtWidgets import (...)` block (alphabetical, after
`QPushButton`, before `QVBoxLayout`).

- [ ] **Step 4: Update `tests/test_main_window.py`**

Add a new test after `test_log_dock_is_always_visible`:

```python
def test_contacts_tab_selection_fills_number_field(qtbot):
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    window.contacts_panel.contactSelected.emit("+4917612345678")

    assert window.number_edit.text() == "+4917612345678"


def test_log_dock_holds_a_tab_widget_with_log_and_contacts(qtbot):
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    assert window.log_dock.widget() is window.log_tabs
    assert window.log_tabs.indexOf(window.log_panel) >= 0
    assert window.log_tabs.indexOf(window.contacts_panel) >= 0
```

- [ ] **Step 5: Run the full test suite**

Run: `LD_LIBRARY_PATH=$HOME/.local/lib/pjsip pytest`
Expected: PASS, all tests green.

- [ ] **Step 6: Commit**

```bash
git add src/voice2fritz/gui/main_window.py tests/test_main_window.py
git commit -m "feat: add Contacts tab alongside Call Log in the dock"
```

---

## Manual verification (GUI is visible in this session)

- [ ] Launch the app, confirm the dock shows two tabs: "Call Log" and
  "Contacts", dock title bar is blank.
- [ ] Click the Contacts tab, confirm the table/add/sync UI renders and
  behaves like the modal dialog did.
- [ ] Double-click a contact in the tab, confirm the number fills
  `number_edit` and the tab stays open (no dialog to close).
- [ ] Click the Contacts nav button, confirm the modal dialog still opens,
  and double-clicking a contact there still closes it.
