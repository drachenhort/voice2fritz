# Controls Layout Rework Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Group MainWindow's non-dialpad controls into a designed nav row
(Settings/Contacts/Log) and a call-control row (Hangup/Mute), replacing the
current thrown-together vertical column + stray mute button atop the Call
Log dock.

**Architecture:** `CallDetailsPanel` becomes a pure display widget (drops
`mute_button`). `MainWindow` gains `mute_button` directly and owns its
enable/disable lifecycle alongside `hangup_button` (same call sites, no new
logic). `theme.py` gains one new QSS class, `navButton`, shared by all six
relocated buttons.

**Tech Stack:** PySide6 (QWidget/QHBoxLayout/QVBoxLayout/QPushButton), pytest + pytest-qt.

## Global Constraints

- No new functionality — pure layout/styling rework of existing buttons and signals.
- Dialpad grid, T9 letters, CALL button, number row, SIP status LED row:
  unchanged.
- Call Details dock / Call Log dock docking behavior, stacking, and
  visibility toggle: unchanged.
- Existing signal wiring (`hangup_button` → `_on_hangup_clicked`,
  `mute_button` → `_on_mute_clicked`, etc.) keeps the same target methods —
  only which widget owns the button and where it sits in layout changes.
- `LD_LIBRARY_PATH=$HOME/.local/lib/pjsip` required for every pytest run.

---

### Task 1: Add `navButton` QSS class

**Files:**
- Modify: `src/voice2fritz/gui/theme.py`

**Interfaces:**
- Produces: QSS object name `navButton`, used by Task 2/3 on six buttons
  (Settings, Contacts, Log, Hangup, Mute).

- [ ] **Step 1: Add the QSS rule**

Insert after the existing `QPushButton#dialpadButton` rule (theme.py:50-53):

```css
QPushButton#navButton {
    font-weight: 600;
    font-size: 14px;
    padding: 10px;
}
```

- [ ] **Step 2: Commit**

```bash
git add src/voice2fritz/gui/theme.py
git commit -m "style: add navButton QSS class"
```

No test needed — pure stylesheet addition, exercised visually in later tasks.

---

### Task 2: `CallDetailsPanel` becomes display-only

**Files:**
- Modify: `src/voice2fritz/gui/call_details_panel.py`
- Test: `tests/test_call_details_panel.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `CallDetailsPanel` no longer has `mute_button`. `set_active_call`
  and `set_idle` no longer touch mute enable/checked state — they only
  affect `name_label`/`state_label`/`duration_label`.

- [ ] **Step 1: Update the failing tests first**

Replace `tests/test_call_details_panel.py` in full:

```python
from voice2fritz.gui.call_details_panel import CallDetailsPanel


def test_starts_idle(qtbot):
    panel = CallDetailsPanel()
    qtbot.addWidget(panel)

    assert panel.name_label.text() == "No active call"
    assert panel.duration_label.text() == ""


def test_set_active_call_with_name(qtbot):
    panel = CallDetailsPanel()
    qtbot.addWidget(panel)

    panel.set_active_call("Anna Schmidt", "+4917612345678")

    assert panel.name_label.text() == "Anna Schmidt"
    assert panel.state_label.text() == "Active"
    assert panel.duration_label.text() == "0:00"


def test_set_active_call_without_name_shows_number(qtbot):
    panel = CallDetailsPanel()
    qtbot.addWidget(panel)

    panel.set_active_call("", "+4917612345678")

    assert panel.name_label.text() == "+4917612345678"


def test_set_idle_resets_everything(qtbot):
    panel = CallDetailsPanel()
    qtbot.addWidget(panel)
    panel.set_active_call("Anna Schmidt", "+4917612345678")

    panel.set_idle()

    assert panel.name_label.text() == "No active call"
    assert panel.state_label.text() == ""
    assert panel.duration_label.text() == ""


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

- [ ] **Step 2: Run to verify failures**

Run: `LD_LIBRARY_PATH=$HOME/.local/lib/pjsip pytest tests/test_call_details_panel.py -v`
Expected: passes as-is actually won't fail yet since mute_button still
exists and isn't asserted — this step just confirms the file runs clean
before the source change. Proceed to Step 3.

- [ ] **Step 3: Rewrite `call_details_panel.py`**

```python
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QLabel,
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

        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.addWidget(self.name_label)
        layout.addWidget(self.state_label)
        layout.addWidget(self.duration_label)
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
        self._timer.start()

    def set_idle(self) -> None:
        self._timer.stop()
        self.name_label.setText("No active call")
        self.state_label.setText("")
        self.duration_label.setText("")

    def set_state_text(self, text: str) -> None:
        self.state_label.setText(text)

    def _tick(self) -> None:
        self._seconds += 1
        minutes, secs = divmod(self._seconds, 60)
        self.duration_label.setText(f"{minutes}:{secs:02d}")
```

- [ ] **Step 4: Run tests to verify pass**

Run: `LD_LIBRARY_PATH=$HOME/.local/lib/pjsip pytest tests/test_call_details_panel.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add src/voice2fritz/gui/call_details_panel.py tests/test_call_details_panel.py
git commit -m "refactor: make CallDetailsPanel display-only, drop mute_button"
```

---

### Task 3: Rework `MainWindow` layout — nav row, call-control row, mute ownership

**Files:**
- Modify: `src/voice2fritz/gui/main_window.py`
- Test: `tests/test_main_window.py`

**Interfaces:**
- Consumes: `CallDetailsPanel` (Task 2, no `mute_button`), `navButton` QSS
  object name (Task 1).
- Produces: `MainWindow.mute_button` (new attribute, replaces
  `MainWindow.call_details.mute_button` at every call site).
  `MainWindow.hangup_button`, `.settings_button`, `.contacts_button`,
  `.log_button` keep their existing names — only their layout position and
  QSS object name change.

- [ ] **Step 1: Update test references from `window.call_details.mute_button` to `window.mute_button`**

In `tests/test_main_window.py`, replace every occurrence of
`window.call_details.mute_button` with `window.mute_button` (4 occurrences,
at the lines containing: `window.call_details.mute_button.click()`,
`assert window.call_details.mute_button.isEnabled()` ×2,
`assert not window.call_details.mute_button.isEnabled()` — one of the
`isEnabled()` assertions is `assert not ...`, the other plain `assert ...`).

Concretely, in `test_mute_button_toggles_engine_mute`:
```python
    window.mute_button.click()
```

In the incoming-call-answered test:
```python
    assert window.mute_button.isEnabled()
```

In the incoming-call-reject test:
```python
    assert not window.mute_button.isEnabled()
```

- [ ] **Step 2: Run to verify these 3 tests fail**

Run: `LD_LIBRARY_PATH=$HOME/.local/lib/pjsip pytest tests/test_main_window.py -v -k "mute or incoming_call_answer or incoming_call_reject"`
Expected: FAIL — `MainWindow` has no attribute `mute_button` yet.

- [ ] **Step 3: Rewrite the layout section of `main_window.py`**

Replace lines 43-123 (from `self.number_edit = QLineEdit()` through
`self.setCentralWidget(container)`) with:

```python
        self.number_edit = QLineEdit()
        self.number_edit.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.backspace_button = QPushButton("⌫")
        self.backspace_button.setToolTip("Backspace")

        number_row = QHBoxLayout()
        number_row.addWidget(self.number_edit)
        number_row.addWidget(self.backspace_button)

        self.digit_buttons: dict[str, QPushButton] = {}
        self.digit_letter_labels: dict[str, QLabel] = {}
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
                button.setObjectName("dialpadButton")
                button.clicked.connect(lambda checked=False, d=digit: self._on_digit_clicked(d))

                letters_label = QLabel(_T9_LETTERS[digit])
                letters_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                letters_label.setStyleSheet("color: #8a8f98; font-size: 11px;")

                cell = QVBoxLayout()
                cell.setSpacing(0)
                cell.addWidget(button)
                cell.addWidget(letters_label)
                cell_widget = QWidget()
                cell_widget.setLayout(cell)

                dialpad_grid.addWidget(cell_widget, row, col)
                self.digit_buttons[digit] = button
                self.digit_letter_labels[digit] = letters_label

        self.call_button = QPushButton("📞 CALL")
        self.call_button.setObjectName("callButton")
        self.call_button.setToolTip("Call")

        self.hangup_button = QPushButton("✕ Hangup")
        self.hangup_button.setObjectName("navButton")
        self.hangup_button.setToolTip("Hang up")
        self.hangup_button.setEnabled(False)
        self.mute_button = QPushButton("🔇 Mute")
        self.mute_button.setObjectName("navButton")
        self.mute_button.setToolTip("Mute")
        self.mute_button.setCheckable(True)
        self.mute_button.setEnabled(False)

        call_control_row = QHBoxLayout()
        call_control_row.addWidget(self.hangup_button)
        call_control_row.addWidget(self.mute_button)

        dialpad_column = QVBoxLayout()
        dialpad_column.addLayout(number_row)
        dialpad_column.addLayout(dialpad_grid)
        dialpad_column.addWidget(self.call_button)
        dialpad_column.addLayout(call_control_row)

        self.settings_button = QPushButton("⚙ Settings")
        self.settings_button.setObjectName("navButton")
        self.settings_button.setToolTip("Settings")
        self.contacts_button = QPushButton("Contacts")
        self.contacts_button.setObjectName("navButton")
        self.log_button = QPushButton("Log")
        self.log_button.setObjectName("navButton")

        nav_row = QHBoxLayout()
        nav_row.addWidget(self.settings_button)
        nav_row.addWidget(self.contacts_button)
        nav_row.addWidget(self.log_button)

        self.sip_status_led = QLabel()
        self.sip_status_led.setFixedSize(14, 14)
        self._set_sip_status_led(is_ok=False, text="Not registered")

        status_row = QHBoxLayout()
        status_row.addWidget(self.sip_status_led)
        status_row.addStretch()

        layout = QVBoxLayout()
        layout.addLayout(status_row)
        layout.addLayout(nav_row)
        layout.addLayout(dialpad_column)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
```

Note what's removed versus the old code: `top_row`, `controls_column`, and
the old un-suffixed Hangup/Settings/Contacts/Log button construction (no
`navButton` object name, no icon+label text) are gone, replaced above.

- [ ] **Step 4: Wire `mute_button` in `_connect_signals`**

In `_connect_signals` (main_window.py, currently line 147), change:

```python
        self.call_details.mute_button.clicked.connect(self._on_mute_clicked)
```
to:
```python
        self.mute_button.clicked.connect(self._on_mute_clicked)
```

- [ ] **Step 5: Update mute enable/disable call sites**

`_on_mute_clicked` (uses `self.call_details.mute_button.isChecked()`):
```python
    def _on_mute_clicked(self) -> None:
        if self._active_call is not None:
            self.sip_engine.set_mute(self._active_call, self.mute_button.isChecked())
```

`_on_call_clicked` — after `self.hangup_button.setEnabled(True)`, add:
```python
        self.mute_button.setEnabled(True)
```

`_on_call_ended` — after `self.hangup_button.setEnabled(False)`, add:
```python
        self.mute_button.setEnabled(False)
        self.mute_button.setChecked(False)
```

`_on_incoming_call_answered` — after `self.hangup_button.setEnabled(True)`, add:
```python
        self.mute_button.setEnabled(True)
```

- [ ] **Step 6: Run the full main_window test suite**

Run: `LD_LIBRARY_PATH=$HOME/.local/lib/pjsip pytest tests/test_main_window.py -v`
Expected: PASS (all tests)

- [ ] **Step 7: Run the full test suite**

Run: `LD_LIBRARY_PATH=$HOME/.local/lib/pjsip pytest`
Expected: PASS (all tests, no regressions elsewhere)

- [ ] **Step 8: Commit**

```bash
git add src/voice2fritz/gui/main_window.py tests/test_main_window.py
git commit -m "feat: regroup controls into nav row and call-control row"
```

---

## Manual verification (after all tasks, in this session — GUI is visible)

- [ ] Launch the app, confirm: status LED row, then a 3-button nav row
  (Settings/Contacts/Log) spanning the width, then dialpad, then CALL,
  then a Hangup/Mute row below CALL (both grayed out, no active call).
- [ ] Make a call (or fake one via test), confirm Hangup/Mute become
  enabled; end the call, confirm they gray out and mute unchecks.
- [ ] Confirm Call Details dock no longer has a button at its top — just
  name/state/duration text.
- [ ] Confirm all six relocated buttons share the same visual weight/style
  (navButton class applied).
