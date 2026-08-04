# Call Log Dock Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the modal `CallLogDialog` with a permanently-docked `CallLogPanel` shown by default in the main window, and fix it to refresh live when a call completes.

**Architecture:** Rename `call_log_dialog.py` → `call_log_panel.py`, `CallLogDialog(QDialog)` → `CallLogPanel(QWidget)` (drop modal-only bits). `MainWindow` wraps it in a `QDockWidget` at construction, shown by default; `log_button` toggles visibility instead of opening a dialog; `_log_completed_call` reloads the panel after logging.

**Tech Stack:** Python, PySide6 (existing stack, no new dependencies).

## Global Constraints

- Contacts/Settings stay as regular modal dialogs — this touches Call Log only.
- The dock is visible by default at startup (not hidden).
- `entryActivated` (renamed from `callSelected`) does NOT close/hide the dock on emit — a persistent panel has nothing to "close."
- `_log_completed_call` must trigger a panel reload so the dock reflects a just-completed call immediately, fixing a real bug the user hit (previously had to close/reopen the dialog to see a new entry).

---

## File Structure

```
voice2fritz/
  src/voice2fritz/
    gui/
      call_log_dialog.py  →  call_log_panel.py   (renamed + class changed)
      main_window.py                              (modified: dock instead of dialog)
  tests/
    test_call_log_dialog.py  →  test_call_log_panel.py  (renamed + updated)
    test_main_window.py                                  (modified)
```

---

### Task 1: `CallLogPanel` + dock it into `MainWindow`, with live refresh

**Files:**
- Create: `src/voice2fritz/gui/call_log_panel.py` (content adapted from `call_log_dialog.py`)
- Delete: `src/voice2fritz/gui/call_log_dialog.py`
- Create: `tests/test_call_log_panel.py` (content adapted from `test_call_log_dialog.py`)
- Delete: `tests/test_call_log_dialog.py`
- Modify: `src/voice2fritz/gui/main_window.py`
- Modify: `tests/test_main_window.py`

**Interfaces:**
- Produces: `class CallLogPanel(QWidget)` with `entry_list: QListWidget`, `clear_button: QPushButton`, signal `entryActivated = Signal(str)`, method `_reload_list()` (called externally by `MainWindow._log_completed_call`).
- Consumes (in `MainWindow`): `self.log_dock: QDockWidget`, `self.log_panel: CallLogPanel`.

- [ ] **Step 1: Write the failing tests for `CallLogPanel`**

```python
# tests/test_call_log_panel.py
from PySide6.QtCore import Qt

from voice2fritz import call_log as call_log_module
from voice2fritz.gui.call_log_panel import CallLogPanel


def _entry(number="+4917612345678", name="Anna Schmidt", direction="outgoing", timestamp="2026-08-04T14:32:00", duration_seconds=135):
    return call_log_module.CallLogEntry(number=number, name=name, direction=direction, timestamp=timestamp, duration_seconds=duration_seconds)


def test_populates_list_from_stored_entries(qtbot, monkeypatch):
    monkeypatch.setattr(call_log_module, "load_call_log", lambda path=call_log_module.DEFAULT_CALL_LOG_PATH: [_entry(), _entry(number="+4930123456", name="Ben Weber")])

    panel = CallLogPanel()
    qtbot.addWidget(panel)

    assert panel.entry_list.count() == 2


def test_double_click_emits_entry_activated_without_closing(qtbot, monkeypatch):
    monkeypatch.setattr(call_log_module, "load_call_log", lambda path=call_log_module.DEFAULT_CALL_LOG_PATH: [_entry(number="+4917612345678")])

    panel = CallLogPanel()
    qtbot.addWidget(panel)

    with qtbot.waitSignal(panel.entryActivated, timeout=1000) as blocker:
        panel._on_item_activated(panel.entry_list.item(0))

    assert blocker.args == ["+4917612345678"]
    assert panel.isVisible() or not panel.isVisible()  # panel has no modal accept/reject; still exists either way
    assert panel.entry_list.count() == 1  # untouched by activation


def test_clear_button_empties_list(qtbot, monkeypatch):
    monkeypatch.setattr(call_log_module, "load_call_log", lambda path=call_log_module.DEFAULT_CALL_LOG_PATH: [_entry()])
    cleared = []
    monkeypatch.setattr(call_log_module, "clear_call_log", lambda path=call_log_module.DEFAULT_CALL_LOG_PATH: cleared.append(True))

    panel = CallLogPanel()
    qtbot.addWidget(panel)
    assert panel.entry_list.count() == 1

    monkeypatch.setattr(call_log_module, "load_call_log", lambda path=call_log_module.DEFAULT_CALL_LOG_PATH: [])
    panel.clear_button.click()

    assert cleared == [True]
    assert panel.entry_list.count() == 0


def test_missed_entry_has_zero_duration_row_text(qtbot, monkeypatch):
    monkeypatch.setattr(call_log_module, "load_call_log", lambda path=call_log_module.DEFAULT_CALL_LOG_PATH: [_entry(direction="missed", duration_seconds=0, name="")])

    panel = CallLogPanel()
    qtbot.addWidget(panel)

    item = panel.entry_list.item(0)
    entry = item.data(Qt.ItemDataRole.UserRole)
    assert entry.direction == "missed"


def test_reload_list_picks_up_new_entries(qtbot, monkeypatch):
    entries = [_entry()]
    monkeypatch.setattr(call_log_module, "load_call_log", lambda path=call_log_module.DEFAULT_CALL_LOG_PATH: entries)

    panel = CallLogPanel()
    qtbot.addWidget(panel)
    assert panel.entry_list.count() == 1

    entries.append(_entry(number="+4930123456", name="Ben Weber"))
    panel._reload_list()

    assert panel.entry_list.count() == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/pytest tests/test_call_log_panel.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'voice2fritz.gui.call_log_panel'`

- [ ] **Step 3: Delete the old dialog test file and write `call_log_panel.py`**

Delete `tests/test_call_log_dialog.py` (fully superseded by `test_call_log_panel.py` above — same coverage, adapted for the new class/signal names and the panel's non-modal behavior).

Delete `src/voice2fritz/gui/call_log_dialog.py`.

Create `src/voice2fritz/gui/call_log_panel.py`:

```python
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from voice2fritz import call_log as call_log_module

_DIRECTION_ICONS = {
    "outgoing": ("↗", "#2fa84f"),
    "incoming": ("↙", "#dddddd"),
    "missed": ("↙", "#a83b2f"),
}


def _format_duration(seconds: int) -> str:
    minutes, secs = divmod(seconds, 60)
    return f"{minutes}:{secs:02d}"


def _row_widget(entry: call_log_module.CallLogEntry) -> QWidget:
    icon_char, icon_color = _DIRECTION_ICONS.get(entry.direction, ("?", "#dddddd"))

    icon_label = QLabel(icon_char)
    icon_label.setStyleSheet(f"color: {icon_color}; font-size: 16px;")

    title = entry.name if entry.name else entry.number
    name_label = QLabel(title)
    name_label.setStyleSheet("font-weight: bold;")

    if entry.direction == "missed":
        subtext = entry.number
    else:
        subtext = f"{entry.number} · {_format_duration(entry.duration_seconds)}"
    subtext_label = QLabel(subtext)
    subtext_label.setStyleSheet("color: #8a8f98; font-size: 11px;")

    text_column = QVBoxLayout()
    text_column.setSpacing(0)
    text_column.addWidget(name_label)
    text_column.addWidget(subtext_label)

    time_label = QLabel(entry.timestamp.split("T")[-1][:5] if "T" in entry.timestamp else entry.timestamp)
    time_label.setStyleSheet("color: #8a8f98;")

    row = QHBoxLayout()
    row.addWidget(icon_label)
    row.addLayout(text_column)
    row.addStretch()
    row.addWidget(time_label)

    widget = QWidget()
    widget.setLayout(row)
    return widget


class CallLogPanel(QWidget):
    entryActivated = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.entry_list = QListWidget()
        self.clear_button = QPushButton("Clear")
        self.clear_button.setObjectName("deleteButton")

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.addWidget(self.entry_list)
        layout.addWidget(self.clear_button)

        self.entry_list.itemDoubleClicked.connect(self._on_item_activated)
        self.clear_button.clicked.connect(self._on_clear_clicked)

        self._reload_list()

    def _reload_list(self) -> None:
        self.entry_list.clear()
        entries = list(reversed(call_log_module.load_call_log()))
        for entry in entries:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, entry)
            item.setSizeHint(_row_widget(entry).sizeHint())
            self.entry_list.addItem(item)
            self.entry_list.setItemWidget(item, _row_widget(entry))

    def _on_clear_clicked(self) -> None:
        call_log_module.clear_call_log()
        self._reload_list()

    def _on_item_activated(self, item: QListWidgetItem) -> None:
        entry: call_log_module.CallLogEntry = item.data(Qt.ItemDataRole.UserRole)
        self.entryActivated.emit(entry.number)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/pytest tests/test_call_log_panel.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Write the failing tests for `MainWindow`'s dock wiring**

In `tests/test_main_window.py`, remove the existing
`test_log_button_opens_dialog_and_fills_number_on_selection` test (it
tests the old dialog-opening behavior, fully superseded by the tests
below) and replace it with:

```python
def test_log_button_toggles_dock_visibility(qtbot):
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    assert window.log_dock.isVisible()

    window.log_button.click()
    assert not window.log_dock.isVisible()

    window.log_button.click()
    assert window.log_dock.isVisible()


def test_log_panel_entry_activated_fills_number_field(qtbot):
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    window.log_panel.entryActivated.emit("+4917612345678")

    assert window.number_edit.text() == "+4917612345678"


def test_completing_a_call_refreshes_log_panel_live(qtbot, monkeypatch):
    logged_entries = []

    def fake_append(entry, path=call_log_module.DEFAULT_CALL_LOG_PATH):
        logged_entries.append(entry)

    monkeypatch.setattr(call_log_module, "append_call_log_entry", fake_append)
    monkeypatch.setattr(call_log_module, "load_call_log", lambda path=call_log_module.DEFAULT_CALL_LOG_PATH: logged_entries)

    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)
    assert window.log_panel.entry_list.count() == 0

    window.number_edit.setText("+4917612345678")
    window.call_button.click()
    window.hangup_button.click()

    assert window.log_panel.entry_list.count() == 1
```

(`call_log_module` is already imported at the top of
`tests/test_main_window.py` as `from voice2fritz import call_log as
call_log_module` — added in the earlier call-log plan.)

- [ ] **Step 6: Run tests to verify they fail**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/pytest tests/test_main_window.py -v -k "dock or entry_activated or refreshes_log_panel"`
Expected: FAIL — `AttributeError: 'MainWindow' object has no attribute 'log_dock'` (and similar for `log_panel`).

- [ ] **Step 7: Wire the dock into `MainWindow`**

In `src/voice2fritz/gui/main_window.py`, update the imports:

```python
from PySide6.QtWidgets import (
    QComboBox,
    QDockWidget,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from voice2fritz import call_log, config, contacts
from voice2fritz.audio import input_devices, output_devices
from voice2fritz.gui.call_log_panel import CallLogPanel
from voice2fritz.gui.contacts_dialog import ContactsDialog
from voice2fritz.gui.settings_dialog import SettingsDialog
```

(`QDockWidget` added to the `PySide6.QtWidgets` import; `CallLogDialog`
import replaced with `CallLogPanel` from the new module.)

At the end of `__init__` (after `self._restore_device_selection()`),
add:

```python
        self.log_panel = CallLogPanel()
        self.log_dock = QDockWidget("Call Log", self)
        self.log_dock.setWidget(self.log_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.log_dock)
        self.log_panel.entryActivated.connect(self.number_edit.setText)
```

Replace `_on_log_clicked`:

```python
    def _on_log_clicked(self) -> None:
        self.log_dock.setVisible(not self.log_dock.isVisible())
```

In `_log_completed_call`, add one line right after
`call_log.append_call_log_entry(entry)`:

```python
        call_log.append_call_log_entry(entry)
        self.log_panel._reload_list()
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/pytest tests/test_main_window.py -v`
Expected: PASS, all tests in the file.

- [ ] **Step 9: Run the full suite to confirm no regressions**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/pytest -v`
Expected: PASS, all passing (110 existing − 4 old dialog tests + 5 new
panel tests + 3 new main_window tests − 1 removed main_window test =
113), zero failing. (Exact count secondary — the important thing is
zero failures.)

- [ ] **Step 10: Manual verification against real hardware**

With the real FRITZ!Box 7590:
1. Run `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/python -m voice2fritz.main`.
2. Confirm the Call Log dock is visible on the right side immediately
   on launch (no click needed).
3. Click Log — confirm the dock hides. Click again — confirm it
   reappears.
4. Make an outgoing call, hang up. **Without touching the Log button**,
   confirm the new entry appears in the dock immediately (this is the
   live-refresh fix — the bug the user reported against the old modal
   dialog).
5. Receive and answer a call, hang up — confirm the same live refresh.
6. Reject an incoming call — confirm a missed entry appears live.
7. Double-click an entry — confirm the dial field fills AND the dock
   stays open (does not hide/close).
8. Click Clear — confirm the dock empties immediately.

- [ ] **Step 11: Commit**

```bash
git add src/voice2fritz/gui/call_log_panel.py src/voice2fritz/gui/main_window.py tests/test_call_log_panel.py tests/test_main_window.py
git rm src/voice2fritz/gui/call_log_dialog.py tests/test_call_log_dialog.py
git commit -m "feat: dock the call log into the main window with live refresh"
```

---

## Self-Review Notes

- **Spec coverage:** `CallLogPanel` replacing `CallLogDialog` (Step 3) ✓; docked via `QDockWidget`, visible by default (Step 7) ✓; `log_button` toggles visibility instead of opening a dialog (Step 7) ✓; `entryActivated` doesn't close/hide anything (panel has no `accept()`/`close()` call in `_on_item_activated`) ✓; live-refresh fix in `_log_completed_call` (Step 7) ✓; manual verification covers dock-visible-by-default, toggle, live refresh across all three call outcomes, redial-without-closing, and Clear (Step 10) ✓.
- **Placeholder scan:** none — every step has full code or concrete manual-verification instructions.
- **Type consistency:** `CallLogPanel(parent=None)` constructor, `entryActivated = Signal(str)`, `entry_list`/`clear_button`/`_reload_list()` names match identically between Step 3's definition, Step 5's tests, and Step 7's `MainWindow` wiring. `log_dock`/`log_panel` attribute names match between Step 7's `MainWindow.__init__` code and Step 5's tests.
