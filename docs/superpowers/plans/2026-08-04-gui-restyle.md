# GUI Restyle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restyle `MainWindow` into a two-column dark-themed layout (dialpad grid on the left, icon call-control buttons on the right), matching a mockup the user provided — pure layout/styling change, no new call functionality.

**Architecture:** All changes are additive to existing files: `main_window.py`'s `__init__` gets a new layout arrangement plus a dialpad grid and icon button labels; a new `theme.py` module holds a QSS stylesheet string; `main.py` applies it to the `QApplication`. No changes to `sip_engine.py`, `config.py`, `audio.py`, or `settings_dialog.py`.

**Tech Stack:** Python, PySide6 (existing stack, no new dependencies).

## Global Constraints

- No new call-control functionality — only the dialpad (appends digits to `number_edit`) is new interactive behavior, everything else is a re-layout/re-style of existing widgets.
- Every existing widget attribute name (`number_edit`, `call_button`, `hangup_button`, `mute_button`, `settings_button`, `capture_combo`, `playback_combo`, `status_label`) is preserved exactly — later code and existing tests reference these by name.
- Icons are plain Unicode characters set as button text (📞, ✕, 🔇, ⚙) — no icon asset files, no new dependencies.
- Dark theme is forced via a QSS stylesheet applied at the `QApplication` level in `main.py`, not per-widget — same look regardless of desktop theme.
- No automated test asserts on QSS appearance (visual-only, not unit-testable) — but the dialpad's digit-append behavior IS unit-tested, following the existing `pytest-qt` pattern.

---

## File Structure

```
voice2fritz/
  src/voice2fritz/
    gui/
      main_window.py   (modified: layout, dialpad, icon buttons)
      theme.py          (new: DARK_STYLESHEET constant)
    main.py             (modified: apply stylesheet)
  tests/
    test_main_window.py (modified: dialpad test added, button-text assertions removed where present)
```

---

### Task 1: Restyle `MainWindow` — two-column layout, dialpad grid, icon buttons

**Files:**
- Modify: `src/voice2fritz/gui/main_window.py`
- Modify: `tests/test_main_window.py`

**Interfaces:**
- Consumes: nothing new — same `sip_engine` constructor argument and signal names as before (Task 4/6 of the v1 plan).
- Produces: `MainWindow.digit_buttons: dict[str, QPushButton]` keyed by digit character (`"0"`-`"9"`, `"*"`, `"#"`), for the dialpad test to find each button. All previously-existing public attributes (`number_edit`, `call_button`, `hangup_button`, `mute_button`, `settings_button`, `capture_combo`, `playback_combo`, `status_label`) unchanged in name/type — only their layout position and (for the four control buttons) their `.text()` change to icon characters.

- [ ] **Step 1: Write the failing test for dialpad digit clicks**

Add to `tests/test_main_window.py` (uses the existing `FakeSipEngine` and `no_device_persistence` fixture already in that file):

```python
def test_dialpad_button_appends_digit_to_number_field(qtbot):
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    window.digit_buttons["1"].click()
    window.digit_buttons["2"].click()
    window.digit_buttons["*"].click()

    assert window.number_edit.text() == "12*"


def test_dialpad_button_appends_to_existing_text(qtbot):
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    window.number_edit.setText("030")
    window.digit_buttons["5"].click()

    assert window.number_edit.text() == "0305"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/pytest tests/test_main_window.py -v -k dialpad`
Expected: FAIL with `AttributeError: 'MainWindow' object has no attribute 'digit_buttons'`

- [ ] **Step 3: Rewrite `MainWindow.__init__` and add the dialpad/layout helpers**

Replace the widget-creation-and-layout section of `src/voice2fritz/gui/main_window.py` (everything from `self.number_edit = QLineEdit()` through the `self.setCentralWidget(container)` line, i.e. lines 25-57 of the current file) with:

```python
        self.number_edit = QLineEdit()
        self.number_edit.setAlignment(Qt.AlignmentFlag.AlignRight)

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
                dialpad_grid.addWidget(button, row, col)
                self.digit_buttons[digit] = button

        dialpad_column = QVBoxLayout()
        dialpad_column.addWidget(self.number_edit)
        dialpad_column.addLayout(dialpad_grid)

        self.call_button = QPushButton("📞")
        self.call_button.setObjectName("callButton")
        self.call_button.setToolTip("Call")
        self.hangup_button = QPushButton("✕")
        self.hangup_button.setToolTip("Hang up")
        self.hangup_button.setEnabled(False)
        self.mute_button = QPushButton("🔇")
        self.mute_button.setToolTip("Mute")
        self.mute_button.setCheckable(True)
        self.mute_button.setEnabled(False)
        self.settings_button = QPushButton("⚙")
        self.settings_button.setToolTip("Settings")

        controls_column = QVBoxLayout()
        controls_column.addWidget(self.call_button)
        controls_column.addWidget(self.hangup_button)
        controls_column.addWidget(self.mute_button)
        controls_column.addWidget(self.settings_button)

        top_row = QHBoxLayout()
        top_row.addLayout(dialpad_column)
        top_row.addLayout(controls_column)

        self.capture_combo = QComboBox()
        self.playback_combo = QComboBox()
        self.status_label = QLabel("Not registered")

        device_row = QHBoxLayout()
        device_row.addWidget(QLabel("Mic:"))
        device_row.addWidget(self.capture_combo)
        device_row.addWidget(QLabel("Speaker:"))
        device_row.addWidget(self.playback_combo)

        layout = QVBoxLayout()
        layout.addWidget(self.status_label)
        layout.addLayout(top_row)
        layout.addLayout(device_row)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
```

Add `_on_digit_clicked` alongside the other `_on_*` handlers:

```python
    def _on_digit_clicked(self, digit: str) -> None:
        self.number_edit.setText(self.number_edit.text() + digit)
```

Update the imports at the top of the file to add `QGridLayout` and `Qt`:

```python
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
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
```

Leave every other method (`_populate_devices`, `_restore_device_selection`,
`_connect_signals`, `_on_call_clicked`, `_on_hangup_clicked`,
`_on_mute_clicked`, `_on_call_ended`, `_on_incoming_call`,
`_on_settings_clicked`, `_on_account_saved`, `_on_capture_changed`,
`_on_playback_changed`, `_save_device_selection`) exactly as they are —
none of them reference button text, so none need changes.

- [ ] **Step 4: Run tests to verify they pass**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/pytest tests/test_main_window.py -v`
Expected: PASS, all tests in the file (including the two new dialpad tests) — 15 passed.

- [ ] **Step 5: Run the full suite to confirm no regressions**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/pytest -v`
Expected: PASS, 30 passed (28 existing + 2 new).

- [ ] **Step 6: Commit**

```bash
git add src/voice2fritz/gui/main_window.py tests/test_main_window.py
git commit -m "feat: restyle main window with dialpad grid and icon buttons"
```

---

### Task 2: Dark theme stylesheet

**Files:**
- Create: `src/voice2fritz/gui/theme.py`
- Modify: `src/voice2fritz/main.py`

**Interfaces:**
- Produces: `theme.DARK_STYLESHEET: str` — a QSS string.
- Consumes (in `main.py`): applied via `app.setStyleSheet(theme.DARK_STYLESHEET)`.

No automated test for this task — QSS visual appearance isn't unit-testable, consistent with the plan's Global Constraints. Verified by manual inspection (Step 3).

- [ ] **Step 1: Write `src/voice2fritz/gui/theme.py`**

```python
DARK_STYLESHEET = """
QWidget {
    background-color: #1c1e26;
    color: #dddddd;
    font-size: 13px;
}

QLineEdit, QComboBox {
    background-color: #12141a;
    border: 1px solid #333333;
    border-radius: 4px;
    padding: 6px;
    color: #ffffff;
}

QPushButton {
    background-color: #2a2d38;
    border: 1px solid #383c48;
    border-radius: 6px;
    padding: 8px;
    color: #eeeeee;
}

QPushButton:hover {
    background-color: #383c48;
}

QPushButton:disabled {
    color: #666666;
}

QPushButton#callButton {
    background-color: #2fa84f;
    color: #ffffff;
    font-weight: bold;
}

QPushButton#callButton:hover {
    background-color: #36bd59;
}

QPushButton:checked {
    background-color: #a83b2f;
}

QLabel {
    color: #dddddd;
}
"""
```

- [ ] **Step 2: Apply it in `src/voice2fritz/main.py`**

Add the import:

```python
from voice2fritz.gui import theme
```

Add one line right after `app = QApplication(sys.argv)`:

```python
    app.setStyleSheet(theme.DARK_STYLESHEET)
```

- [ ] **Step 3: Manual verification**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/python -m voice2fritz.main`

Confirm: dark background throughout, the Call button (`objectName="callButton"`) is green, Mute turns red when checked/active, hover states work on buttons, text is legible (light text on dark background). Take a new screenshot and compare it against `docs/images/screenshot.png` framing — replace that screenshot file with an updated one showing the new layout (same capture method as before: `spectacle -a -b -n -o docs/images/screenshot.png` while the app is running), since the current screenshot shows the old single-row layout.

- [ ] **Step 4: Run the full test suite once more to confirm the stylesheet didn't break anything**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/pytest -v`
Expected: PASS, 30 passed.

- [ ] **Step 5: Commit**

```bash
git add src/voice2fritz/gui/theme.py src/voice2fritz/main.py docs/images/screenshot.png
git commit -m "feat: apply dark theme stylesheet, update screenshot"
```

---

## Self-Review Notes

- **Spec coverage:** two-column layout (Task 1) ✓; dialpad grid appending digits (Task 1) ✓; icon buttons with tooltips (Task 1) ✓; device dropdowns/status label unchanged in behavior (Task 1, untouched methods) ✓; dark QSS theme applied app-wide (Task 2) ✓; Unicode icons, no assets (Task 1) ✓; updated screenshot (Task 2, Step 3) ✓.
- **Placeholder scan:** none — every step has full code or concrete manual-verification instructions.
- **Type consistency:** `digit_buttons` dict keys (`"0"`-`"9"`, `"*"`, `"#"`) match between the `__init__` construction in Task 1 Step 3 and the test's lookups (`window.digit_buttons["1"]` etc.) in Task 1 Step 1. All pre-existing attribute names (`number_edit`, `call_button`, etc.) are unchanged, verified against the current `main_window.py` and `test_main_window.py` contents.
