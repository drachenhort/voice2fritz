# Dialpad Restyle + Call Details Dock Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restyle the dialpad to match the mockup (T9 letters, backspace button, full-width green Call button, two-line SIP status) and add an always-visible Call Details dock (name/state/duration/Mute/Speaker), stacked with Call Log on the left.

**Architecture:** New standalone `CallDetailsPanel(QWidget)` (own file, own tests, like `CallLogPanel`). `MainWindow` restyles its dialpad layout, splits `status_label` into two labels, moves `mute_button`/`playback_combo` into the new panel, and re-docks both Call Details and Call Log to the left.

**Tech Stack:** Python, PySide6 (existing stack, no new dependencies).

## Global Constraints

- No tab bar — Contacts and Settings stay as modal dialogs, unchanged.
- No Hold/Transfer/Video — not built, not part of this pass.
- Both docks move to the **left** side, stacked: Call Details above Call Log.
- `digit_buttons[digit]` (used for DTMF/dial wiring) keeps `.text()` equal to just the digit — T9 letters are a separate, non-interactive `QLabel`, never part of the button's own text or click handling.
- `mute_button` and `playback_combo` move from `MainWindow` directly onto `CallDetailsPanel` (`self.call_details.mute_button`, `self.call_details.speaker_combo`) — existing tests referencing `window.mute_button`/`window.playback_combo` must be updated to the new paths, not kept as aliases (spec's own testing section specifies the new paths explicitly).

---

## File Structure

```
voice2fritz/
  src/voice2fritz/
    gui/
      call_details_panel.py   (new)
      main_window.py            (modified: dialpad restyle, status split, dock placement)
    main.py                     (modified: set_account_host call)
  tests/
    test_call_details_panel.py  (new)
    test_main_window.py         (modified)
```

---

### Task 1: `CallDetailsPanel`

**Files:**
- Create: `src/voice2fritz/gui/call_details_panel.py`
- Test: `tests/test_call_details_panel.py`

**Interfaces:**
- Produces: `class CallDetailsPanel(QWidget)` with:
  - `name_label: QLabel`, `state_label: QLabel`, `duration_label: QLabel`
  - `mute_button: QPushButton` (checkable, disabled while idle)
  - `speaker_combo: QComboBox`
  - `set_active_call(name: str, number: str) -> None`
  - `set_idle() -> None`
  - `set_state_text(text: str) -> None`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_call_details_panel.py
from voice2fritz.gui.call_details_panel import CallDetailsPanel


def test_starts_idle(qtbot):
    panel = CallDetailsPanel()
    qtbot.addWidget(panel)

    assert panel.name_label.text() == "No active call"
    assert panel.duration_label.text() == ""
    assert not panel.mute_button.isEnabled()


def test_set_active_call_with_name(qtbot):
    panel = CallDetailsPanel()
    qtbot.addWidget(panel)

    panel.set_active_call("Anna Schmidt", "+4917612345678")

    assert panel.name_label.text() == "Anna Schmidt"
    assert panel.state_label.text() == "Active"
    assert panel.duration_label.text() == "0:00"
    assert panel.mute_button.isEnabled()


def test_set_active_call_without_name_shows_number(qtbot):
    panel = CallDetailsPanel()
    qtbot.addWidget(panel)

    panel.set_active_call("", "+4917612345678")

    assert panel.name_label.text() == "+4917612345678"


def test_set_idle_resets_everything(qtbot):
    panel = CallDetailsPanel()
    qtbot.addWidget(panel)
    panel.set_active_call("Anna Schmidt", "+4917612345678")
    panel.mute_button.setChecked(True)

    panel.set_idle()

    assert panel.name_label.text() == "No active call"
    assert panel.state_label.text() == ""
    assert panel.duration_label.text() == ""
    assert not panel.mute_button.isEnabled()
    assert not panel.mute_button.isChecked()


def test_set_state_text_updates_state_label(qtbot):
    panel = CallDetailsPanel()
    qtbot.addWidget(panel)
    panel.set_active_call("Anna Schmidt", "+4917612345678")

    panel.set_state_text("Ringing")

    assert panel.state_label.text() == "Ringing"


def test_duration_label_ticks_up(qtbot):
    panel = CallDetailsPanel()
    qtbot.addWidget(panel)
    panel.set_active_call("Anna Schmidt", "+4917612345678")

    qtbot.wait(1100)

    assert panel.duration_label.text() == "0:01"


def test_set_idle_stops_the_timer(qtbot):
    panel = CallDetailsPanel()
    qtbot.addWidget(panel)
    panel.set_active_call("Anna Schmidt", "+4917612345678")
    qtbot.wait(1100)
    panel.set_idle()

    qtbot.wait(1100)

    assert panel.duration_label.text() == ""
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/pytest tests/test_call_details_panel.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'voice2fritz.gui.call_details_panel'`

- [ ] **Step 3: Write `src/voice2fritz/gui/call_details_panel.py`**

```python
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class CallDetailsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.name_label = QLabel()
        self.name_label.setStyleSheet("font-weight: bold; font-size: 15px;")
        self.state_label = QLabel()
        self.duration_label = QLabel()
        self.duration_label.setStyleSheet("color: #8a8f98;")

        self.mute_button = QPushButton("🔇")
        self.mute_button.setToolTip("Mute")
        self.mute_button.setCheckable(True)

        self.speaker_combo = QComboBox()

        speaker_row = QHBoxLayout()
        speaker_row.addWidget(QLabel("Speaker:"))
        speaker_row.addWidget(self.speaker_combo)

        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.addWidget(self.name_label)
        layout.addWidget(self.state_label)
        layout.addWidget(self.duration_label)
        layout.addWidget(self.mute_button)
        layout.addLayout(speaker_row)
        layout.addStretch()

        self._seconds = 0
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)

        self.set_idle()

    def set_active_call(self, name: str, number: str) -> None:
        self.name_label.setText(name if name else number)
        self.state_label.setText("Active")
        self._seconds = 0
        self.duration_label.setText("0:00")
        self.mute_button.setEnabled(True)
        self._timer.start()

    def set_idle(self) -> None:
        self._timer.stop()
        self.name_label.setText("No active call")
        self.state_label.setText("")
        self.duration_label.setText("")
        self.mute_button.setEnabled(False)
        self.mute_button.setChecked(False)

    def set_state_text(self, text: str) -> None:
        self.state_label.setText(text)

    def _tick(self) -> None:
        self._seconds += 1
        minutes, secs = divmod(self._seconds, 60)
        self.duration_label.setText(f"{minutes}:{secs:02d}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/pytest tests/test_call_details_panel.py -v`
Expected: PASS (7 passed — note this test file takes ~2.2 real seconds
due to the two `qtbot.wait(1100)` calls, which is expected and correct
for testing real timer behavior, not a hang).

- [ ] **Step 5: Commit**

```bash
git add src/voice2fritz/gui/call_details_panel.py tests/test_call_details_panel.py
git commit -m "feat: add CallDetailsPanel with live call duration"
```

---

### Task 2: Wire `CallDetailsPanel` into `MainWindow`, restyle the dialpad

**Files:**
- Modify: `src/voice2fritz/gui/main_window.py`
- Modify: `src/voice2fritz/main.py`
- Modify: `tests/test_main_window.py`

**Interfaces:**
- Consumes: `CallDetailsPanel` (Task 1).
- Produces: `MainWindow.call_details: CallDetailsPanel`,
  `MainWindow.sip_status_label: QLabel`, `MainWindow.account_label: QLabel`,
  `MainWindow.backspace_button: QPushButton`,
  `MainWindow.set_account_host(host: str) -> None`. Removes
  `MainWindow.mute_button`, `MainWindow.playback_combo`,
  `MainWindow.status_label` (replaced by the above).

- [ ] **Step 1: Update existing tests that reference the widgets being moved/renamed**

In `tests/test_main_window.py`:

Replace every `window.playback_combo` with `window.call_details.speaker_combo`
(three occurrences: in `test_device_combos_populated_from_engine`,
`test_initial_device_selection_applied_at_startup`,
`test_restores_saved_device_selection_on_startup`).

Replace every `window.mute_button` with `window.call_details.mute_button`
(occurrences in `test_mute_button_toggles_engine_mute`,
`test_incoming_call_accept_answers_and_enables_controls`,
`test_incoming_call_reject_hangs_up_and_resets_state`).

Replace the body of `test_registration_state_updates_status_label`:

```python
def test_registration_state_updates_status_label(qtbot):
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    engine.registrationStateChanged.emit("200 OK")

    assert window.sip_status_label.text() == "SIP Status: 200 OK"
```

- [ ] **Step 2: Add the new failing tests**

Add to `tests/test_main_window.py`:

```python
def test_backspace_button_removes_last_character(qtbot):
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    window.number_edit.setText("0123")
    window.backspace_button.click()

    assert window.number_edit.text() == "012"


def test_set_account_host_updates_account_label(qtbot):
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    window.set_account_host("fritz.box")

    assert window.account_label.text() == "Account: fritz.box"


def test_outgoing_call_updates_call_details_panel(qtbot):
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    window.number_edit.setText("+4917612345678")
    window.call_button.click()

    assert window.call_details.name_label.text() == "+4917612345678"
    assert window.call_details.state_label.text() == "Active"

    window.hangup_button.click()

    assert window.call_details.name_label.text() == "No active call"


def test_call_details_docks_stacked_on_left(qtbot):
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)
    window.show()

    from PySide6.QtCore import Qt

    assert window.dockWidgetArea(window.call_details_dock) == Qt.DockWidgetArea.LeftDockWidgetArea
    assert window.dockWidgetArea(window.log_dock) == Qt.DockWidgetArea.LeftDockWidgetArea
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/pytest tests/test_main_window.py -v`
Expected: FAIL — `AttributeError` on `window.call_details`,
`window.sip_status_label`, `window.backspace_button`, etc.

- [ ] **Step 4: Rewrite `MainWindow.__init__` and related methods**

In `src/voice2fritz/gui/main_window.py`, update the imports:

```python
from datetime import datetime

from PySide6.QtCore import Qt
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
from voice2fritz.gui.call_details_panel import CallDetailsPanel
from voice2fritz.gui.call_log_panel import CallLogPanel
from voice2fritz.gui.contacts_dialog import ContactsDialog
from voice2fritz.gui.settings_dialog import SettingsDialog

_T9_LETTERS = {
    "1": "", "2": "ABC", "3": "DEF",
    "4": "GHI", "5": "JKL", "6": "MNO",
    "7": "PQRS", "8": "TUV", "9": "WXYZ",
    "*": "", "0": "+", "#": "",
}
```

Replace the entire body of `__init__` from `self.number_edit = QLineEdit()`
through `self.setCentralWidget(container)` with:

```python
        self.number_edit = QLineEdit()
        self.number_edit.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.backspace_button = QPushButton("⌫")
        self.backspace_button.setToolTip("Backspace")

        number_row = QHBoxLayout()
        number_row.addWidget(self.number_edit)
        number_row.addWidget(self.backspace_button)

        self.digit_buttons: dict[str, QPushButton] = {}
        dialpad_grid = QGridLayout()
        dialpad_rows = [
            ["1", "2", "3"],
            ["4", "5", "6"],
            ["7", "8", "9"],
            ["*", "0", "#"],
        ]
        for row, digits in enumerate(dialpad_rows):
            for col, digit in enumerate(digits):
                button = QPushButton(digit)
                button.clicked.connect(lambda checked=False, d=digit: self._on_digit_clicked(d))

                letters_label = QLabel(_T9_LETTERS[digit])
                letters_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                letters_label.setStyleSheet("color: #8a8f98; font-size: 9px;")

                cell = QVBoxLayout()
                cell.setSpacing(0)
                cell.addWidget(button)
                cell.addWidget(letters_label)
                cell_widget = QWidget()
                cell_widget.setLayout(cell)

                dialpad_grid.addWidget(cell_widget, row, col)
                self.digit_buttons[digit] = button

        self.call_button = QPushButton("📞 CALL")
        self.call_button.setObjectName("callButton")
        self.call_button.setToolTip("Call")

        dialpad_column = QVBoxLayout()
        dialpad_column.addLayout(number_row)
        dialpad_column.addLayout(dialpad_grid)
        dialpad_column.addWidget(self.call_button)

        self.hangup_button = QPushButton("✕")
        self.hangup_button.setToolTip("Hang up")
        self.hangup_button.setEnabled(False)
        self.settings_button = QPushButton("⚙")
        self.settings_button.setToolTip("Settings")
        self.contacts_button = QPushButton("Contacts")
        self.log_button = QPushButton("Log")

        controls_column = QVBoxLayout()
        controls_column.addWidget(self.hangup_button)
        controls_column.addWidget(self.settings_button)
        controls_column.addWidget(self.contacts_button)
        controls_column.addWidget(self.log_button)

        top_row = QHBoxLayout()
        top_row.addLayout(dialpad_column)
        top_row.addLayout(controls_column)

        self.capture_combo = QComboBox()

        device_row = QHBoxLayout()
        device_row.addWidget(QLabel("Mic:"))
        device_row.addWidget(self.capture_combo)

        self.sip_status_label = QLabel("SIP Status: Not registered")
        self.account_label = QLabel("Account: —")

        layout = QVBoxLayout()
        layout.addWidget(self.sip_status_label)
        layout.addWidget(self.account_label)
        layout.addLayout(top_row)
        layout.addLayout(device_row)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
```

Note: `self.playback_combo` no longer exists on `MainWindow` at all — it
now lives solely as `self.call_details.speaker_combo`, created in the
dock-setup block below. `self.mute_button` no longer exists on
`MainWindow` either — use `self.call_details.mute_button`.

Replace the dock-setup block at the end of `__init__` (currently
`self.log_panel = CallLogPanel()` through
`self.log_panel.entryActivated.connect(self.number_edit.setText)`) with:

```python
        self.call_details = CallDetailsPanel()
        self.call_details_dock = QDockWidget("Call Details", self)
        self.call_details_dock.setWidget(self.call_details)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.call_details_dock)

        self.log_panel = CallLogPanel()
        self.log_dock = QDockWidget("Call Log", self)
        self.log_dock.setWidget(self.log_panel)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.log_dock)
        self.log_panel.entryActivated.connect(self.number_edit.setText)
```

- [ ] **Step 5: Update `_populate_devices` and `_restore_device_selection`
  to use `self.call_details.speaker_combo`**

Replace `_populate_devices`:

```python
    def _populate_devices(self) -> None:
        devices = self.sip_engine.list_devices()
        for device in input_devices(devices):
            self.capture_combo.addItem(device.name, device.id)
        for device in output_devices(devices):
            self.call_details.speaker_combo.addItem(device.name, device.id)
```

Replace `_restore_device_selection`'s playback half — the whole method
becomes:

```python
    def _restore_device_selection(self) -> None:
        capture_name, playback_name = config.load_device_selection()

        if capture_name is not None:
            index = self.capture_combo.findText(capture_name)
            if index >= 0:
                self.capture_combo.setCurrentIndex(index)
        if self.capture_combo.count() > 0:
            self._on_capture_changed(self.capture_combo.currentIndex())

        if playback_name is not None:
            index = self.call_details.speaker_combo.findText(playback_name)
            if index >= 0:
                self.call_details.speaker_combo.setCurrentIndex(index)
        if self.call_details.speaker_combo.count() > 0:
            self._on_playback_changed(self.call_details.speaker_combo.currentIndex())
```

Note: `_populate_devices()` and `_restore_device_selection()` are called
from `__init__` (unchanged call sites), but now reference
`self.call_details`, which must exist before they run. Move the dock
creation block from Step 4 (the `self.call_details = CallDetailsPanel()`
through `self.log_panel.entryActivated.connect(...)` lines) to **before**
`self._populate_devices()` / `self._connect_signals()` /
`self._restore_device_selection()` are called, i.e. right after
`self.setCentralWidget(container)` and before those three calls — not
after them as in the previous (Call-Log-only) ordering.

- [ ] **Step 6: Update `_connect_signals`, `_on_capture_changed`/`_on_playback_changed`, `_save_device_selection`**

```python
    def _connect_signals(self) -> None:
        self.call_button.clicked.connect(self._on_call_clicked)
        self.hangup_button.clicked.connect(self._on_hangup_clicked)
        self.backspace_button.clicked.connect(self._on_backspace_clicked)
        self.call_details.mute_button.clicked.connect(self._on_mute_clicked)
        self.capture_combo.currentIndexChanged.connect(self._on_capture_changed)
        self.call_details.speaker_combo.currentIndexChanged.connect(self._on_playback_changed)
        self.sip_engine.registrationStateChanged.connect(self._on_registration_state_changed)
        self.sip_engine.callStateChanged.connect(self._on_call_state_changed)
        self.sip_engine.callEnded.connect(self._on_call_ended)
        self.sip_engine.incomingCall.connect(self._on_incoming_call)
        self.settings_button.clicked.connect(self._on_settings_clicked)
        self.contacts_button.clicked.connect(self._on_contacts_clicked)
        self.log_button.clicked.connect(self._on_log_clicked)
```

Add two new small handler methods, near `_on_digit_clicked`:

```python
    def _on_backspace_clicked(self) -> None:
        self.number_edit.setText(self.number_edit.text()[:-1])

    def _on_registration_state_changed(self, text: str) -> None:
        self.sip_status_label.setText(f"SIP Status: {text}")

    def _on_call_state_changed(self, text: str) -> None:
        self.sip_status_label.setText(f"SIP Status: {text}")
        self.call_details.set_state_text(text)

    def set_account_host(self, host: str) -> None:
        self.account_label.setText(f"Account: {host}")
```

Replace `_on_capture_changed`/`_on_playback_changed`/`_save_device_selection`:

```python
    def _on_capture_changed(self, index: int) -> None:
        if index >= 0:
            self.sip_engine.select_capture_device(self.capture_combo.itemData(index))
            self._save_device_selection()

    def _on_playback_changed(self, index: int) -> None:
        if index >= 0:
            self.sip_engine.select_playback_device(self.call_details.speaker_combo.itemData(index))
            self._save_device_selection()

    def _save_device_selection(self) -> None:
        capture_name = self.capture_combo.currentText() or None
        playback_name = self.call_details.speaker_combo.currentText() or None
        config.save_device_selection(capture_name, playback_name)
```

- [ ] **Step 7: Update the call-lifecycle handlers to drive `CallDetailsPanel`**

Replace `_on_call_clicked`:

```python
    def _on_call_clicked(self) -> None:
        number = self.number_edit.text()
        self._active_call = self.sip_engine.make_call(number)
        self._call_direction = "outgoing"
        self._call_number = number
        self._call_start_time = datetime.now()
        self.hangup_button.setEnabled(True)
        self._set_dtmf_mode(True)

        name = ""
        for contact in contacts.load_contacts():
            if contact.number == number:
                name = contact.name
                break
        self.call_details.set_active_call(name, number)
```

Replace `_on_mute_clicked`:

```python
    def _on_mute_clicked(self) -> None:
        if self._active_call is not None:
            self.sip_engine.set_mute(self._active_call, self.call_details.mute_button.isChecked())
```

Replace `_on_call_ended`:

```python
    def _on_call_ended(self) -> None:
        self._active_call = None
        self.hangup_button.setEnabled(False)
        self._set_dtmf_mode(False)
        self.call_details.set_idle()
        self._log_completed_call()
```

Replace `_on_incoming_call`:

```python
    def _on_incoming_call(self, call) -> None:
        self._active_call = call
        self._call_direction = "incoming"
        self._call_number = self.sip_engine.get_remote_number(call)
        self._call_start_time = datetime.now()
        answer = QMessageBox.question(
            self,
            "Incoming call",
            "Incoming call. Answer?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.sip_engine.answer(self._active_call)
            self.hangup_button.setEnabled(True)
            self._set_dtmf_mode(True)
            name = ""
            for contact in contacts.load_contacts():
                if contact.number == self._call_number:
                    name = contact.name
                    break
            self.call_details.set_active_call(name, self._call_number)
        else:
            self._call_direction = "missed"
            self.sip_engine.hangup(self._active_call)
            self._on_call_ended()
```

- [ ] **Step 8: Wire `set_account_host` from `main.py`**

In `src/voice2fritz/main.py`, after `window = MainWindow(sip_engine)`
and before `window.show()`, add:

```python
    window.set_account_host(account.host)
```

Also, in `_on_account_saved` in `main_window.py`, add a call to keep the
label correct if the account changes via Settings mid-session:

```python
    def _on_account_saved(self, cfg: config.AccountConfig) -> None:
        password = config.get_password(cfg.username) or ""
        self.sip_engine.register(cfg.host, cfg.username, password)
        self.set_account_host(cfg.host)
```

- [ ] **Step 9: Run tests to verify they pass**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/pytest tests/test_main_window.py -v`
Expected: PASS, all tests in the file.

- [ ] **Step 10: Run the full suite to confirm no regressions**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/pytest -v`
Expected: PASS, all passing, zero failing.

- [ ] **Step 11: Manual verification against real hardware**

With the real FRITZ!Box 7590:
1. Run `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/python -m voice2fritz.main`.
2. Confirm both docks (Call Details above Call Log) appear stacked on
   the **left**, dialpad is the central/right content.
3. Confirm each dialpad digit shows its T9 letters beneath it, and the
   `#`/`+`/blank cases match the mapping.
4. Confirm the number field's backspace button removes digits.
5. Confirm the Call button reads "📞 CALL" and spans the dialpad's
   width.
6. Confirm the top shows two lines: "SIP Status: ..." and
   "Account: ...". Confirm the account line shows the right host on
   startup.
7. Make an outgoing call. Confirm Call Details shows the number (or
   contact name if in Contacts), state "Active", and a duration counting
   up once per second. Mute in Call Details actually mutes (same
   behavior as before, just relocated).
8. Hang up — confirm Call Details returns to "No active call" and the
   duration stops/clears.
9. Receive and answer an incoming call — same checks as step 7 for the
   incoming case, using the caller's number/name.
10. Confirm the Speaker dropdown (now inside Call Details) still
    switches playback device correctly and the choice still persists
    across restarts (same underlying `config.save_device_selection`,
    just relocated).

If any pjsua2/PJSIP behavior differs from expectations here (e.g. exact
`callStateChanged` text used for `state_label`), adjust
`_on_call_state_changed`'s text handling accordingly — expected
hardware-specific verification work, not a plan defect, consistent with
this project's other pjsua2-touching tasks.

- [ ] **Step 12: Commit**

```bash
git add src/voice2fritz/gui/main_window.py src/voice2fritz/main.py tests/test_main_window.py
git commit -m "feat: restyle dialpad, add Call Details dock, move docks to the left"
```

---

## Self-Review Notes

- **Spec coverage:** T9 letters as decorative labels, digit buttons unchanged (Task 2, Step 4) ✓; backspace button (Task 2, Steps 4/6/9) ✓; full-width green Call button (Task 2, Step 4) ✓; two-line SIP status/account header (Task 2, Steps 4/6/8) ✓; `CallDetailsPanel` with name/state/duration/mute/speaker and idle/active states (Task 1) ✓; Mute and Speaker relocated into Call Details, all existing device-selection/mute behavior preserved (Task 2, Steps 5–7) ✓; both docks stacked on the left (Task 2, Step 4) ✓; No Hold/Transfer/Video anywhere ✓; manual verification covers every piece above against real hardware (Task 2, Step 11) ✓.
- **Placeholder scan:** none — every step has full code or concrete manual-verification instructions.
- **Type consistency:** `CallDetailsPanel(parent=None)` and its methods (`set_active_call(name, number)`, `set_idle()`, `set_state_text(text)`) match identically between Task 1's definition and Task 2's call sites in `_on_call_clicked`/`_on_incoming_call`/`_on_call_ended`/`_on_call_state_changed`. `self.call_details.mute_button`/`self.call_details.speaker_combo` attribute paths match between Task 1's widget names and every Task 2 reference (device methods, `_connect_signals`, tests). `sip_status_label`/`account_label`/`backspace_button`/`set_account_host` names match between their Step 4/6/8 definitions and the Step 2 tests.
