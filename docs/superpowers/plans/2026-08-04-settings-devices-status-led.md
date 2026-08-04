# Settings Device Move + Status LED + Dialpad Styling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move mic/speaker device selection into `SettingsDialog`, replace
the two-line SIP status/account header with a single LED-style
registration indicator, and make the dialpad digit buttons read like a
phone keypad (bigger/bolder, larger T9 letters).

**Architecture:** Two new small helper functions in `audio.py`
(one UI-free for `MainWindow`'s startup auto-selection, one
combo-populating for `SettingsDialog`'s dropdowns) — a deliberate split
from the spec's single-function wording, needed because `MainWindow` no
longer owns any combo boxes after this pass and can't call a
combo-populating function with nothing to populate. `CallDetailsPanel`
drops its `speaker_combo`. `SettingsDialog` gains a `sip_engine`
parameter and the two device combos. `MainWindow` drops its device row,
`account_label`, and `set_account_host`, and gains a small LED `QLabel`
driven purely by `registrationStateChanged`. A new `dialpadButton` QSS
class in `theme.py` styles the digit buttons.

**Tech Stack:** Python, PySide6 (existing stack, no new dependencies).

## Global Constraints

- Device selection applies **immediately** on combo change (not gated
  behind the account "Save" button) — same behavior as today, just
  relocated to `SettingsDialog`.
- The LED is green (`#2fa84f`) only when the registration status text is
  *exactly* `"200 OK"`; red (`#a83b2f`) for everything else, including
  the initial pre-registration state. The raw status text is always set
  as the LED's tooltip.
- Call state (`callStateChanged`) no longer touches the top status
  line/LED at all — it already forwards to
  `self.call_details.set_state_text(text)`, which is unchanged. The LED
  reflects registration health only.
- `digit_buttons[digit].text()` stays just the bare digit — adding
  `objectName("dialpadButton")` only changes styling, not text or
  click/DTMF wiring.
- No changes to `SipEngine`'s signal contracts or to
  `contacts.py`/`call_log.py`/`ringtone.py`/`incoming_call_popup.py`.

---

## File Structure

```
voice2fritz/
  src/voice2fritz/
    audio.py                          (modified: two new helper functions)
    main.py                             (modified: SettingsDialog(sip_engine, ...) call site)
    gui/
      call_details_panel.py             (modified: drop speaker_combo)
      settings_dialog.py                (modified: sip_engine param, device combos)
      main_window.py                    (modified: LED, drop device row/account_label, dialpad styling)
      theme.py                          (modified: new dialpadButton QSS class)
  tests/
    test_audio.py                       (new)
    test_call_details_panel.py          (unchanged — no speaker_combo references exist)
    test_settings_dialog.py             (modified: sip_engine param + migrated device tests)
    test_main_window.py                   (modified: LED tests, device/account test removal)
```

---

### Task 1: `audio.py` device-selection helpers

**Files:**
- Modify: `src/voice2fritz/audio.py`
- Test: `tests/test_audio.py` (new)

**Interfaces:**
- Produces: `restore_saved_devices(sip_engine) -> None` (no UI —
  selects the saved capture/playback devices on the engine directly, by
  name-matching against `sip_engine.list_devices()`; no-op for a device
  whose saved name isn't found or wasn't saved).
- Produces: `populate_and_restore_devices(sip_engine, capture_combo, playback_combo) -> None`
  (populates both `QComboBox` instances from `sip_engine.list_devices()`,
  restores the saved selection into each combo if found, and always
  calls `sip_engine.select_capture_device`/`select_playback_device` for
  whatever ends up selected — the saved device if found, otherwise the
  first/default item).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_audio.py
from PySide6.QtWidgets import QComboBox

from voice2fritz import config
from voice2fritz.audio import (
    AudioDevice,
    populate_and_restore_devices,
    restore_saved_devices,
)


class _FakeSipEngine:
    def __init__(self, devices):
        self._devices = devices
        self.selected_capture = None
        self.selected_playback = None

    def list_devices(self):
        return self._devices

    def select_capture_device(self, device_id):
        self.selected_capture = device_id

    def select_playback_device(self, device_id):
        self.selected_playback = device_id


def _sample_devices():
    return [
        AudioDevice(id=0, name="Built-in Mic", has_input=True, has_output=False),
        AudioDevice(id=1, name="Headset", has_input=True, has_output=True),
    ]


def test_restore_saved_devices_selects_matching_saved_names(monkeypatch):
    monkeypatch.setattr(config, "load_device_selection", lambda path=config.DEFAULT_CONFIG_PATH: ("Headset", "Headset"))
    engine = _FakeSipEngine(_sample_devices())

    restore_saved_devices(engine)

    assert engine.selected_capture == 1
    assert engine.selected_playback == 1


def test_restore_saved_devices_is_noop_when_nothing_saved(monkeypatch):
    monkeypatch.setattr(config, "load_device_selection", lambda path=config.DEFAULT_CONFIG_PATH: (None, None))
    engine = _FakeSipEngine(_sample_devices())

    restore_saved_devices(engine)

    assert engine.selected_capture is None
    assert engine.selected_playback is None


def test_populate_and_restore_devices_populates_combos(qtbot, monkeypatch):
    monkeypatch.setattr(config, "load_device_selection", lambda path=config.DEFAULT_CONFIG_PATH: (None, None))
    engine = _FakeSipEngine(_sample_devices())
    capture_combo = QComboBox()
    playback_combo = QComboBox()
    qtbot.addWidget(capture_combo)
    qtbot.addWidget(playback_combo)

    populate_and_restore_devices(engine, capture_combo, playback_combo)

    assert [capture_combo.itemText(i) for i in range(capture_combo.count())] == ["Built-in Mic", "Headset"]
    assert [playback_combo.itemText(i) for i in range(playback_combo.count())] == ["Headset"]
    assert engine.selected_capture == 0
    assert engine.selected_playback == 1


def test_populate_and_restore_devices_restores_saved_selection(qtbot, monkeypatch):
    monkeypatch.setattr(config, "load_device_selection", lambda path=config.DEFAULT_CONFIG_PATH: ("Headset", "Headset"))
    engine = _FakeSipEngine(_sample_devices())
    capture_combo = QComboBox()
    playback_combo = QComboBox()
    qtbot.addWidget(capture_combo)
    qtbot.addWidget(playback_combo)

    populate_and_restore_devices(engine, capture_combo, playback_combo)

    assert capture_combo.currentText() == "Headset"
    assert playback_combo.currentText() == "Headset"
    assert engine.selected_capture == 1
    assert engine.selected_playback == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/pytest tests/test_audio.py -v`
Expected: FAIL with `ImportError: cannot import name 'restore_saved_devices'`

- [ ] **Step 3: Add the two functions to `src/voice2fritz/audio.py`**

Add these imports at the top (alongside the existing `dataclasses`
import):

```python
from PySide6.QtWidgets import QComboBox

from voice2fritz import config
```

Append at the end of the file:

```python
def restore_saved_devices(sip_engine) -> None:
    devices = sip_engine.list_devices()
    capture_name, playback_name = config.load_device_selection()

    if capture_name is not None:
        for device in input_devices(devices):
            if device.name == capture_name:
                sip_engine.select_capture_device(device.id)
                break

    if playback_name is not None:
        for device in output_devices(devices):
            if device.name == playback_name:
                sip_engine.select_playback_device(device.id)
                break


def populate_and_restore_devices(
    sip_engine,
    capture_combo: QComboBox,
    playback_combo: QComboBox,
) -> None:
    devices = sip_engine.list_devices()
    for device in input_devices(devices):
        capture_combo.addItem(device.name, device.id)
    for device in output_devices(devices):
        playback_combo.addItem(device.name, device.id)

    capture_name, playback_name = config.load_device_selection()

    if capture_name is not None:
        index = capture_combo.findText(capture_name)
        if index >= 0:
            capture_combo.setCurrentIndex(index)
    if capture_combo.count() > 0:
        sip_engine.select_capture_device(capture_combo.itemData(capture_combo.currentIndex()))

    if playback_name is not None:
        index = playback_combo.findText(playback_name)
        if index >= 0:
            playback_combo.setCurrentIndex(index)
    if playback_combo.count() > 0:
        sip_engine.select_playback_device(playback_combo.itemData(playback_combo.currentIndex()))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/pytest tests/test_audio.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add src/voice2fritz/audio.py tests/test_audio.py
git commit -m "feat: add device-selection helpers to audio.py"
```

---

### Task 2: `CallDetailsPanel` — drop `speaker_combo`

**Files:**
- Modify: `src/voice2fritz/gui/call_details_panel.py`

**Interfaces:**
- Removes: `CallDetailsPanel.speaker_combo`. All other interfaces
  (`name_label`, `state_label`, `duration_label`, `mute_button`,
  `set_active_call`, `set_idle`, `set_state_text`) are unchanged.

No test changes: `tests/test_call_details_panel.py` never references
`speaker_combo` — confirmed by grep before writing this plan.

- [ ] **Step 1: Replace `src/voice2fritz/gui/call_details_panel.py`'s imports and `__init__`**

```python
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
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

        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.addWidget(self.name_label)
        layout.addWidget(self.state_label)
        layout.addWidget(self.duration_label)
        layout.addWidget(self.mute_button)
        layout.addStretch()

        self._seconds = 0
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)

        self.set_idle()
```

(`set_active_call`, `set_idle`, `set_state_text`, `_tick` are unchanged
— leave them exactly as they are below this point in the file.)

- [ ] **Step 2: Run tests to verify nothing broke**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/pytest tests/test_call_details_panel.py -v`
Expected: PASS (7 passed, unchanged from before this task).

- [ ] **Step 3: Commit**

```bash
git add src/voice2fritz/gui/call_details_panel.py
git commit -m "refactor: remove speaker_combo from CallDetailsPanel (moved to Settings)"
```

---

### Task 3: `SettingsDialog` — device selection

**Files:**
- Modify: `src/voice2fritz/gui/settings_dialog.py`
- Modify: `tests/test_settings_dialog.py`

**Interfaces:**
- Consumes: `populate_and_restore_devices` (Task 1).
- Produces: `SettingsDialog(sip_engine, parent=None)` (signature change
  — `sip_engine` is now a required first positional argument).
  `SettingsDialog.capture_combo: QComboBox`,
  `SettingsDialog.speaker_combo: QComboBox`.

- [ ] **Step 1: Update the existing tests for the new constructor signature**

In `tests/test_settings_dialog.py`, add a fake SIP engine and an
autouse fixture at the top of the file (device functions must not touch
the real `~/.config/voice2fritz/config.json` during tests):

```python
import pytest

from voice2fritz import config
from voice2fritz.audio import AudioDevice
from voice2fritz.gui.settings_dialog import SettingsDialog


class _FakeSipEngine:
    def __init__(self, devices=None):
        self._devices = devices or []
        self.selected_capture = None
        self.selected_playback = None

    def list_devices(self):
        return self._devices

    def select_capture_device(self, device_id):
        self.selected_capture = device_id

    def select_playback_device(self, device_id):
        self.selected_playback = device_id


@pytest.fixture(autouse=True)
def no_device_persistence(monkeypatch):
    monkeypatch.setattr(config, "load_device_selection", lambda path=config.DEFAULT_CONFIG_PATH: (None, None))
    monkeypatch.setattr(config, "save_device_selection", lambda capture, playback, path=config.DEFAULT_CONFIG_PATH: None)
```

Update all three existing tests to construct `SettingsDialog(_FakeSipEngine())`
instead of `SettingsDialog()`:

```python
def test_save_button_persists_config_and_password(qtbot, tmp_path, monkeypatch):
    saved_configs = []
    saved_passwords = []

    monkeypatch.setattr(config, "save_config", lambda cfg, path=config.DEFAULT_CONFIG_PATH: saved_configs.append(cfg))
    monkeypatch.setattr(config, "set_password", lambda username, password: saved_passwords.append((username, password)))

    dialog = SettingsDialog(_FakeSipEngine())
    qtbot.addWidget(dialog)

    dialog.host_edit.setText("fritz.box")
    dialog.username_edit.setText("user123")
    dialog.password_edit.setText("hunter2")

    with qtbot.waitSignal(dialog.accountSaved, timeout=1000):
        dialog.save_button.click()

    assert saved_configs == [config.AccountConfig(host="fritz.box", username="user123")]
    assert saved_passwords == [("user123", "hunter2")]


def test_save_button_persists_google_priority_setting(qtbot, tmp_path, monkeypatch):
    saved_values = []

    monkeypatch.setattr(config, "save_config", lambda cfg, path=config.DEFAULT_CONFIG_PATH: None)
    monkeypatch.setattr(config, "set_password", lambda username, password: None)
    monkeypatch.setattr(config, "save_google_sync_overwrites_local", lambda value, path=config.DEFAULT_CONFIG_PATH: saved_values.append(value))

    dialog = SettingsDialog(_FakeSipEngine())
    qtbot.addWidget(dialog)

    dialog.host_edit.setText("fritz.box")
    dialog.username_edit.setText("user123")
    dialog.password_edit.setText("hunter2")
    dialog.google_priority_checkbox.setChecked(False)

    with qtbot.waitSignal(dialog.accountSaved, timeout=1000):
        dialog.save_button.click()

    assert saved_values == [False]


def test_constructor_loads_saved_google_priority_setting(qtbot, monkeypatch):
    monkeypatch.setattr(config, "load_google_sync_overwrites_local", lambda path=config.DEFAULT_CONFIG_PATH: False)

    dialog = SettingsDialog(_FakeSipEngine())
    qtbot.addWidget(dialog)

    assert dialog.google_priority_checkbox.isChecked() is False
```

- [ ] **Step 2: Add the migrated + new device tests**

```python
def _sample_devices():
    return [
        AudioDevice(id=0, name="Built-in Mic", has_input=True, has_output=False),
        AudioDevice(id=1, name="Headset", has_input=True, has_output=True),
    ]


def test_device_combos_populated_from_engine(qtbot):
    engine = _FakeSipEngine(_sample_devices())

    dialog = SettingsDialog(engine)
    qtbot.addWidget(dialog)

    assert [dialog.capture_combo.itemText(i) for i in range(dialog.capture_combo.count())] == [
        "Built-in Mic",
        "Headset",
    ]
    assert [dialog.speaker_combo.itemText(i) for i in range(dialog.speaker_combo.count())] == ["Headset"]


def test_initial_device_selection_applied_at_construction(qtbot):
    engine = _FakeSipEngine(_sample_devices())

    dialog = SettingsDialog(engine)
    qtbot.addWidget(dialog)

    assert engine.selected_capture == dialog.capture_combo.itemData(0)
    assert engine.selected_playback == dialog.speaker_combo.itemData(0)


def test_restores_saved_device_selection_on_construction(qtbot, monkeypatch):
    monkeypatch.setattr(config, "load_device_selection", lambda path=config.DEFAULT_CONFIG_PATH: ("Headset", "Headset"))
    engine = _FakeSipEngine(_sample_devices())

    dialog = SettingsDialog(engine)
    qtbot.addWidget(dialog)

    assert dialog.capture_combo.currentText() == "Headset"
    assert dialog.speaker_combo.currentText() == "Headset"
    assert engine.selected_capture == 1
    assert engine.selected_playback == 1


def test_device_combo_selection_calls_engine(qtbot):
    engine = _FakeSipEngine(_sample_devices())
    dialog = SettingsDialog(engine)
    qtbot.addWidget(dialog)

    dialog.capture_combo.setCurrentIndex(1)

    assert engine.selected_capture == 1


def test_device_selection_change_persists_choice(qtbot, monkeypatch):
    saved = []
    monkeypatch.setattr(
        config,
        "save_device_selection",
        lambda capture, playback, path=config.DEFAULT_CONFIG_PATH: saved.append((capture, playback)),
    )
    engine = _FakeSipEngine(_sample_devices())
    dialog = SettingsDialog(engine)
    qtbot.addWidget(dialog)
    saved.clear()

    dialog.capture_combo.setCurrentIndex(1)

    assert saved == [("Headset", "Headset")]
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/pytest tests/test_settings_dialog.py -v`
Expected: FAIL — `TypeError: SettingsDialog.__init__() missing 1 required positional argument: 'sip_engine'`, and `AttributeError` on `dialog.capture_combo`/`dialog.speaker_combo` for the new tests.

- [ ] **Step 4: Replace `src/voice2fritz/gui/settings_dialog.py`**

```python
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QCheckBox, QComboBox, QDialog, QFormLayout, QLineEdit, QPushButton, QVBoxLayout

from voice2fritz import config
from voice2fritz.audio import populate_and_restore_devices


class SettingsDialog(QDialog):
    accountSaved = Signal(config.AccountConfig)

    def __init__(self, sip_engine, parent=None):
        super().__init__(parent)
        self.setWindowTitle("FRITZ!Box Account")
        self.sip_engine = sip_engine

        self.host_edit = QLineEdit()
        self.username_edit = QLineEdit()
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.save_button = QPushButton("Save")
        self.google_priority_checkbox = QCheckBox("Google sync overwrites local contacts with the same name")
        self.google_priority_checkbox.setChecked(config.load_google_sync_overwrites_local())

        self.capture_combo = QComboBox()
        self.speaker_combo = QComboBox()

        form = QFormLayout()
        form.addRow("Host", self.host_edit)
        form.addRow("Username", self.username_edit)
        form.addRow("Password", self.password_edit)
        form.addRow("Mic", self.capture_combo)
        form.addRow("Speaker", self.speaker_combo)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.google_priority_checkbox)
        layout.addWidget(self.save_button)

        self.save_button.clicked.connect(self._on_save)
        self.capture_combo.currentIndexChanged.connect(self._on_capture_changed)
        self.speaker_combo.currentIndexChanged.connect(self._on_playback_changed)

        populate_and_restore_devices(self.sip_engine, self.capture_combo, self.speaker_combo)

    def _on_save(self) -> None:
        cfg = config.AccountConfig(
            host=self.host_edit.text(),
            username=self.username_edit.text(),
        )
        config.save_config(cfg)
        config.set_password(cfg.username, self.password_edit.text())
        config.save_google_sync_overwrites_local(self.google_priority_checkbox.isChecked())
        self.accountSaved.emit(cfg)
        self.accept()

    def _on_capture_changed(self, index: int) -> None:
        if index >= 0:
            self.sip_engine.select_capture_device(self.capture_combo.itemData(index))
            self._save_device_selection()

    def _on_playback_changed(self, index: int) -> None:
        if index >= 0:
            self.sip_engine.select_playback_device(self.speaker_combo.itemData(index))
            self._save_device_selection()

    def _save_device_selection(self) -> None:
        capture_name = self.capture_combo.currentText() or None
        playback_name = self.speaker_combo.currentText() or None
        config.save_device_selection(capture_name, playback_name)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/pytest tests/test_settings_dialog.py -v`
Expected: PASS, all tests in the file.

- [ ] **Step 6: Commit**

```bash
git add src/voice2fritz/gui/settings_dialog.py tests/test_settings_dialog.py
git commit -m "feat: move mic/speaker device selection into SettingsDialog"
```

---

### Task 4: `MainWindow` — status LED, drop device row/account label, dialpad styling

**Files:**
- Modify: `src/voice2fritz/gui/main_window.py`
- Modify: `src/voice2fritz/main.py`
- Modify: `src/voice2fritz/gui/theme.py`
- Modify: `tests/test_main_window.py`

**Interfaces:**
- Consumes: `restore_saved_devices` (Task 1), `SettingsDialog(sip_engine, parent)` (Task 3).
- Produces: `MainWindow.sip_status_led: QLabel`. Removes:
  `MainWindow.capture_combo`, `MainWindow.account_label`,
  `MainWindow.set_account_host`, `MainWindow._populate_devices`,
  `MainWindow._restore_device_selection`, `MainWindow._on_capture_changed`,
  `MainWindow._on_playback_changed`, `MainWindow._save_device_selection`.

- [ ] **Step 1: Remove tests that no longer apply, replace the status test**

In `tests/test_main_window.py`, **delete** these five tests entirely
(migrated to `test_settings_dialog.py` in Task 3):
`test_device_combos_populated_from_engine`,
`test_device_combo_selection_calls_engine`,
`test_initial_device_selection_applied_at_startup`,
`test_restores_saved_device_selection_on_startup`,
`test_device_selection_change_persists_choice`.

**Delete** `test_set_account_host_updates_account_label` entirely.

In `test_account_saved_triggers_reregistration`, remove the line
`assert window.account_label.text() == "Account: fritz.box"` (keep
the `assert engine.registrations == [...]` line above it).

**Replace** `test_registration_state_updates_status_label` with:

```python
def test_registration_success_shows_green_led(qtbot):
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    engine.registrationStateChanged.emit("200 OK")

    assert "#2fa84f" in window.sip_status_led.styleSheet()
    assert window.sip_status_led.toolTip() == "200 OK"


def test_registration_failure_shows_red_led(qtbot):
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    engine.registrationStateChanged.emit("401 Unauthorized")

    assert "#a83b2f" in window.sip_status_led.styleSheet()
    assert window.sip_status_led.toolTip() == "401 Unauthorized"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/pytest tests/test_main_window.py -v`
Expected: FAIL — `AttributeError` on `window.sip_status_led` for the two
new tests; other tests referencing removed widgets
(`window.capture_combo`, `window.account_label`) will also fail once you
reach Step 3 below (they're not failing yet since the source hasn't
changed — that's expected at this point, just confirm the two new LED
tests fail with `AttributeError`).

- [ ] **Step 3: Update imports and `__init__`**

Update the imports at the top of `src/voice2fritz/gui/main_window.py`:

```python
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDockWidget,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from voice2fritz import call_log, config, contacts, ringtone
from voice2fritz.audio import restore_saved_devices
from voice2fritz.gui.call_details_panel import CallDetailsPanel
from voice2fritz.gui.call_log_panel import CallLogPanel
from voice2fritz.gui.contacts_dialog import ContactsDialog
from voice2fritz.gui.incoming_call_popup import IncomingCallPopup
from voice2fritz.gui.settings_dialog import SettingsDialog
```

(`QComboBox` is dropped — `MainWindow` no longer owns any combo boxes.
`input_devices`/`output_devices` are dropped — no longer used directly
by `MainWindow`.)

In the dialpad-building loop, add the object name to each digit button
(the loop body currently starts with `button = QPushButton(digit)`):

```python
                button = QPushButton(digit)
                button.setObjectName("dialpadButton")
                button.clicked.connect(lambda checked=False, d=digit: self._on_digit_clicked(d))

                letters_label = QLabel(_T9_LETTERS[digit])
                letters_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                letters_label.setStyleSheet("color: #8a8f98; font-size: 11px;")
```

(Only the new `setObjectName` line and the `font-size` value change from
`9px` to `11px` — everything else in this loop body is unchanged.)

Replace the block from `self.capture_combo = QComboBox()` through
`self.setCentralWidget(container)` with:

```python
        self.sip_status_led = QLabel()
        self.sip_status_led.setFixedSize(14, 14)
        self._set_sip_status_led(is_ok=False, text="Not registered")

        status_row = QHBoxLayout()
        status_row.addWidget(self.sip_status_led)
        status_row.addStretch()

        layout = QVBoxLayout()
        layout.addLayout(status_row)
        layout.addLayout(top_row)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
```

Replace the dock-setup-through-end-of-`__init__` block (currently
`self.call_details = CallDetailsPanel()` through
`self._restore_device_selection()`) with:

```python
        self.call_details = CallDetailsPanel()
        self.call_details_dock = QDockWidget("Call Details", self)
        self.call_details_dock.setWidget(self.call_details)
        self.call_details_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.call_details_dock)

        self.log_panel = CallLogPanel()
        self.log_dock = QDockWidget("Call Log", self)
        self.log_dock.setWidget(self.log_panel)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.log_dock)
        self.log_panel.entryActivated.connect(self.number_edit.setText)

        self._connect_signals()
        restore_saved_devices(self.sip_engine)
```

- [ ] **Step 4: Replace `_connect_signals`, add `_set_sip_status_led`, update the registration/call-state handlers**

```python
    def _connect_signals(self) -> None:
        self.call_button.clicked.connect(self._on_call_clicked)
        self.hangup_button.clicked.connect(self._on_hangup_clicked)
        self.backspace_button.clicked.connect(self._on_backspace_clicked)
        self.call_details.mute_button.clicked.connect(self._on_mute_clicked)
        self.sip_engine.registrationStateChanged.connect(self._on_registration_state_changed)
        self.sip_engine.callStateChanged.connect(self._on_call_state_changed)
        self.sip_engine.callEnded.connect(self._on_call_ended)
        self.sip_engine.incomingCall.connect(self._on_incoming_call)
        self.settings_button.clicked.connect(self._on_settings_clicked)
        self.contacts_button.clicked.connect(self._on_contacts_clicked)
        self.log_button.clicked.connect(self._on_log_clicked)
```

Replace `_on_registration_state_changed`, and the block that used to
contain `_on_call_state_changed`/`set_account_host`:

```python
    def _set_sip_status_led(self, is_ok: bool, text: str) -> None:
        color = "#2fa84f" if is_ok else "#a83b2f"
        self.sip_status_led.setStyleSheet(f"background-color: {color}; border-radius: 7px;")
        self.sip_status_led.setToolTip(text)

    def _on_registration_state_changed(self, text: str) -> None:
        self._set_sip_status_led(is_ok=(text == "200 OK"), text=text)

    def _on_call_state_changed(self, text: str) -> None:
        self.call_details.set_state_text(text)
```

(`set_account_host` is deleted entirely — no replacement method.)

- [ ] **Step 5: Remove the device-handling methods, update `_on_settings_clicked` and `_on_account_saved`**

Delete these methods entirely from `main_window.py`:
`_populate_devices`, `_restore_device_selection`,
`_on_capture_changed`, `_on_playback_changed`, `_save_device_selection`.

Replace `_on_settings_clicked`:

```python
    def _on_settings_clicked(self) -> None:
        dialog = SettingsDialog(self.sip_engine, self)
        dialog.accountSaved.connect(self._on_account_saved)
        dialog.exec()
```

Replace `_on_account_saved` (remove the `self.set_account_host(cfg.host)` line):

```python
    def _on_account_saved(self, cfg: config.AccountConfig) -> None:
        password = config.get_password(cfg.username) or ""
        self.sip_engine.register(cfg.host, cfg.username, password)
```

- [ ] **Step 6: Update `src/voice2fritz/main.py`**

Change both `SettingsDialog(...)` call sites to pass `sip_engine`, and
remove the `window.set_account_host(account.host)` line:

```python
import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from voice2fritz import config
from voice2fritz.gui import theme
from voice2fritz.gui.main_window import MainWindow
from voice2fritz.gui.settings_dialog import SettingsDialog
from voice2fritz.sip_engine import SipEngine

ICON_PATH = Path(__file__).parent / "gui" / "resources" / "icon.png"


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyleSheet(theme.DARK_STYLESHEET)
    app.setWindowIcon(QIcon(str(ICON_PATH)))

    sip_engine = SipEngine()
    sip_engine.start()

    account = config.load_config()
    if account is None:
        dialog = SettingsDialog(sip_engine)
        if dialog.exec() != SettingsDialog.DialogCode.Accepted:
            sip_engine.stop()
            sys.exit(0)
        account = config.load_config()

    window = MainWindow(sip_engine)
    window.show()

    password = config.get_password(account.username) or ""
    sip_engine.register(account.host, account.username, password)

    exit_code = app.exec()
    sip_engine.stop()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
```

- [ ] **Step 7: Add the `dialpadButton` QSS class to `src/voice2fritz/gui/theme.py`**

Add this block anywhere among the other `QPushButton#...` rules (e.g.
right after the `QPushButton[dtmfMode="true"]` block):

```css
QPushButton#dialpadButton {
    font-weight: bold;
    font-size: 22px;
}
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/pytest tests/test_main_window.py -v`
Expected: PASS, all tests in the file.

- [ ] **Step 9: Run the full suite to confirm no regressions**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/pytest -v`
Expected: PASS, all passing, zero failing.

- [ ] **Step 10: Manual verification against real hardware**

With the real FRITZ!Box 7590:
1. Run `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/python -m voice2fritz.main`.
2. Confirm the main window shows a single small colored dot at the top
   (no "SIP Status:"/"Account:" text lines), red before registration
   completes, turning green once registered. Hover over it — confirm
   the tooltip shows the raw status text (e.g. "200 OK").
3. Confirm there's no Mic dropdown visible in the main window anymore.
4. Open Settings — confirm Mic and Speaker dropdowns appear, populated
   with your real audio devices, pre-selected to whatever was
   previously chosen (or the first device on first run).
5. Change the Mic or Speaker dropdown in Settings — confirm it takes
   effect immediately (make a test call to verify audio still routes
   correctly), and that the choice persists across an app restart.
6. Confirm the dialpad digits (0-9, *, #) are visibly bold and larger
   than before, and the T9 letters underneath are slightly bigger but
   still clearly secondary/decorative.
7. Make a call — confirm DTMF and dialing still work correctly (digit
   button click behavior is unaffected by the styling change).

If any pjsua2/PJSIP behavior or Qt stylesheet rendering differs from
expectations here, adjust accordingly — expected hardware/environment-
specific verification work, not a plan defect, consistent with this
project's other hardware-touching tasks.

- [ ] **Step 11: Commit**

```bash
git add src/voice2fritz/gui/main_window.py src/voice2fritz/main.py src/voice2fritz/gui/theme.py tests/test_main_window.py
git commit -m "feat: SIP status LED, drop device row/account label, bolder dialpad styling"
```

---

## Self-Review Notes

- **Spec coverage:** device selection moved to Settings with immediate apply (Task 3) ✓; shared population logic split into a UI-free startup helper and a combo-populating dialog helper — a deliberate, documented deviation from the spec's literal "same function" wording, made necessary by `MainWindow` owning zero combo boxes after this pass (Task 1, explained in Architecture) ✓; `CallDetailsPanel` drops `speaker_combo` (Task 2) ✓; LED green only for exact `"200 OK"`, red otherwise, tooltip shows raw text (Task 4 Step 4) ✓; `account_label`/`set_account_host` fully removed including `main.py` call site (Task 4 Steps 5-6) ✓; call state decoupled from the top line, still flows to Call Details only (Task 4 Step 4) ✓; dialpad digits bold+22px via new `dialpadButton` QSS class, digit `.text()` unaffected (Task 4 Steps 3, 7) ✓; T9 labels 9px→11px (Task 4 Step 3) ✓; manual verification covers every piece above against real hardware (Task 4 Step 10) ✓.
- **Placeholder scan:** none — every step has full code or concrete manual-verification instructions.
- **Type consistency:** `restore_saved_devices(sip_engine)` and `populate_and_restore_devices(sip_engine, capture_combo, playback_combo)` (Task 1) match their call sites exactly in Task 3 (`SettingsDialog.__init__`) and Task 4 (`MainWindow.__init__`). `SettingsDialog(sip_engine, parent=None)` matches both call sites in Task 4 (`_on_settings_clicked`, `main.py`). `sip_status_led`/`_set_sip_status_led` names match between their Task 4 Step 3/4 definitions and the Step 1 tests.
