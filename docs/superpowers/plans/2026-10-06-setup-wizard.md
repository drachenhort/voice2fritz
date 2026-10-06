# Setup Wizard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A step-by-step setup wizard, opened from Settings, that explains the FRITZ!Box IP phone setup and configures voice2fritz (account with live registration check, then audio).

**Architecture:** A `QWizard` subclass in `gui/setup_wizard.py` with six pages. Shared logic is first pulled out of `SettingsPanel` and `MainWindow` (registration classification, account saving, the audio widget) so Settings and the wizard use one code path. `MainWindow` opens the wizard as a non-modal window and suppresses registration popups while it is open.

**Tech Stack:** Python 3, PySide6 (`QWizard`, `QWizardPage`), pytest + pytest-qt (offscreen), pjsua2 (only through the existing `SipEngine`; tests use fakes).

**Spec:** `docs/superpowers/specs/2026-10-06-setup-wizard-design.md`

## Global Constraints

- Run tests with: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/python -m pytest -q` from the repo root (without `LD_LIBRARY_PATH` nine test modules fail to import `pjsua2`). Baseline before Task 1: `285 passed`.
- All user-visible text goes through `tr()` from `voice2fritz.i18n`, and every new `tr()` literal gets a German entry in `_GERMAN` in `src/voice2fritz/i18n.py`, in the same task that adds it. `tests/test_i18n.py::test_every_tr_text_has_a_german_translation` and `test_placeholders_match_between_languages` enforce this.
- Status colours, reused from Settings: green `#2fa84f`, red `#d0453a`, orange `#d08a2c`.
- Registration timeout: 20 000 ms (`REGISTRATION_TIMEOUT_MS`).
- Default FRITZ!Box host: `fritz.box`.
- Rejected-login status codes: 401, 403, 407.
- Use ASCII `...` for ellipses in UI text, as the existing strings do.
- Commit messages: Conventional Commits (`feat:`, `refactor:`, `test:`, `docs:`), ending with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Commit straight to `master` (the repo has no merge commits).

## Review Focus

1. **A call arrives while the wizard is open.** The user must still be able to hang up in the main window (so the wizard is non-modal), and a running echo test in the wizard must stop. Pinned in Task 7.
2. **"Setup wizard..." pressed twice.** Only one wizard should exist; the second press brings the open one to the front. Pinned in Task 7.
3. **Late or repeated registration updates.** PJSIP keeps refreshing and retrying. Only the first result after a Connect press may change the page, and a result arriving after the user edited a field must not mark the page complete. Pinned in Task 5.
4. **The mic level meter is shared.** Closing the wizard (whose audio page stops the monitor on hide) must not leave the Settings level bar dead while Settings is on screen. Pinned in Task 4.
5. **Whitespace around host or username** (copied from the FRITZ!Box page). It must be stripped before saving and registering. Pinned in Task 5.

---

## File Structure

- Create `src/voice2fritz/registration.py`: pure helpers for reading registration status text. No Qt, no pjsua2.
- Modify `src/voice2fritz/config.py`: add `save_account`.
- Create `src/voice2fritz/gui/audio_setup_widget.py`: mic/speaker choice, level meter, echo test (moved from `SettingsPanel`).
- Modify `src/voice2fritz/gui/settings_panel.py`: embed `AudioSetupWidget`; add wizard button, signal and `reload()`.
- Create `src/voice2fritz/gui/setup_wizard.py`: `ConnectPage`, info pages, `AudioPage`, `SetupWizard`.
- Modify `src/voice2fritz/gui/main_window.py`: use `classify_registration`; open/track the wizard; suppress popups; forward call state.
- Modify `src/voice2fritz/i18n.py`: German strings.
- Tests: create `tests/test_registration.py`, `tests/test_setup_wizard.py`; modify `tests/test_config.py`, `tests/test_settings_panel_audio_test.py`, `tests/test_main_window.py`.
- Modify `CHANGELOG.md`.

---

### Task 1: Registration status helpers

**Files:**
- Create: `src/voice2fritz/registration.py`
- Modify: `src/voice2fritz/gui/main_window.py:40,43,233,307-315`
- Test: `tests/test_registration.py`

**Interfaces:**
- Produces: `REGISTRATION_TIMEOUT_MS: int = 20_000`; `classify_registration(text: str) -> str | None` returning `"ok"`, `"rejected"` or `None`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_registration.py`:

```python
import pytest

from voice2fritz.registration import REGISTRATION_TIMEOUT_MS, classify_registration


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("200 OK", "ok"),
        ("202 Accepted", "ok"),
        ("401 Unauthorized", "rejected"),
        ("403 Forbidden", "rejected"),
        ("407 Proxy Authentication Required", "rejected"),
        ("408 Request Timeout", None),
        ("503 Service Unavailable", None),
        ("", None),
    ],
)
def test_classify_registration(text, expected):
    assert classify_registration(text) == expected


def test_timeout_is_twenty_seconds():
    assert REGISTRATION_TIMEOUT_MS == 20_000
```

- [ ] **Step 2: Run test to verify it fails**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/python -m pytest tests/test_registration.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'voice2fritz.registration'`

- [ ] **Step 3: Write the module**

Create `src/voice2fritz/registration.py`:

```python
"""Reading registration status text such as "200 OK" or "401 Unauthorized"."""

# How long to wait for the FRITZ!Box to answer a registration.
REGISTRATION_TIMEOUT_MS = 20_000

_AUTH_REJECTED_CODES = {"401", "403", "407"}


def classify_registration(text: str) -> str | None:
    """"ok", "rejected" (the FRITZ!Box refused the login), or None for anything else.

    None covers unreachable hosts and timeouts, which say nothing about the password.
    """
    if text.startswith("2"):
        return "ok"
    if text.split(" ", 1)[0] in _AUTH_REJECTED_CODES:
        return "rejected"
    return None
```

- [ ] **Step 4: Use it in `MainWindow`**

In `src/voice2fritz/gui/main_window.py`:

1. Delete the line `_REGISTRATION_VERIFY_TIMEOUT_MS = 20_000` and the line `_AUTH_REJECTED_CODES = {"401", "403", "407"}`.
2. Add the import after `from voice2fritz.i18n import current_language, set_language, tr`:

```python
from voice2fritz.registration import REGISTRATION_TIMEOUT_MS, classify_registration
```

3. In `_connect_signals`, change `self._verification_timer.setInterval(_REGISTRATION_VERIFY_TIMEOUT_MS)` to:

```python
        self._verification_timer.setInterval(REGISTRATION_TIMEOUT_MS)
```

4. Replace the body of `_on_registration_state_changed` with:

```python
    def _on_registration_state_changed(self, text: str) -> None:
        self._set_sip_status_led(is_ok=(text == "200 OK"), text=text)
        self.settings_panel.set_registration_result(classify_registration(text))
```

- [ ] **Step 5: Run the full suite**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/python -m pytest -q`
Expected: all pass (9 new tests). `test_registration_result_reaches_settings_password_hint` in `tests/test_main_window.py` confirms `MainWindow` behaves as before.

- [ ] **Step 6: Commit**

```bash
git add src/voice2fritz/registration.py src/voice2fritz/gui/main_window.py tests/test_registration.py
git commit -m "refactor: move registration status classification into its own module

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: `config.save_account`

**Files:**
- Modify: `src/voice2fritz/config.py` (after `save_config`)
- Modify: `src/voice2fritz/gui/settings_panel.py` (`_on_save`)
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `config.save_account(cfg: AccountConfig, password: str, path: Path = DEFAULT_CONFIG_PATH) -> None`. Saves `cfg`; stores `password` in the keyring only when it is not empty.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_config.py` (it imports names from `voice2fritz.config`; add a module import at the top: `from voice2fritz import config`):

```python
def test_save_account_writes_config_and_password(tmp_path, monkeypatch):
    stored = {}
    monkeypatch.setattr(config, "set_password", lambda username, password: stored.update({username: password}))
    path = tmp_path / "config.json"

    config.save_account(config.AccountConfig(host="fritz.box", username="620"), "secret12", path=path)

    assert config.load_config(path) == config.AccountConfig(host="fritz.box", username="620")
    assert stored == {"620": "secret12"}


def test_save_account_with_empty_password_keeps_saved_password(tmp_path, monkeypatch):
    stored = {}
    monkeypatch.setattr(config, "set_password", lambda username, password: stored.update({username: password}))

    config.save_account(config.AccountConfig(host="fritz.box", username="620"), "", path=tmp_path / "config.json")

    assert stored == {}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/python -m pytest tests/test_config.py -q -k save_account`
Expected: FAIL with `AttributeError: module 'voice2fritz.config' has no attribute 'save_account'`

- [ ] **Step 3: Implement**

In `src/voice2fritz/config.py`, directly after `save_config`:

```python
def save_account(cfg: AccountConfig, password: str, path: Path = DEFAULT_CONFIG_PATH) -> None:
    """Save the account; an empty password keeps the one already in the keyring."""
    save_config(cfg, path)
    if password:
        set_password(cfg.username, password)
```

`set_password` is defined further down the module; that is fine because it is looked up at call time (and tests can monkeypatch it).

- [ ] **Step 4: Use it in `SettingsPanel._on_save`**

In `src/voice2fritz/gui/settings_panel.py`, replace these lines of `_on_save`:

```python
        config.save_config(cfg)
        if self.password_edit.text():
            config.set_password(cfg.username, self.password_edit.text())
            # Never leave the password on screen; the hint reports its status instead.
            self.password_edit.clear()
```

with:

```python
        config.save_account(cfg, self.password_edit.text())
        # Never leave the password on screen; the hint reports its status instead.
        self.password_edit.clear()
```

- [ ] **Step 5: Run the full suite**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/python -m pytest -q`
Expected: all pass. `test_saving_a_password_clears_the_field_and_resets_status` confirms Settings still stores the password and clears the field.

- [ ] **Step 6: Commit**

```bash
git add src/voice2fritz/config.py src/voice2fritz/gui/settings_panel.py tests/test_config.py
git commit -m "refactor: add config.save_account for saving account and password together

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Extract `AudioSetupWidget`

**Files:**
- Create: `src/voice2fritz/gui/audio_setup_widget.py`
- Modify (rewrite): `src/voice2fritz/gui/settings_panel.py`
- Modify: `tests/test_settings_panel_audio_test.py` (retarget only)

**Interfaces:**
- Produces: `AudioSetupWidget(sip_engine, parent=None)` with public attributes `capture_combo`, `speaker_combo`, `mic_level_bar`, `echo_test_button`, `echo_test_status` and methods `set_call_active(active: bool)`, `show_saved_devices()`, `resume_level_monitor()`. `SettingsPanel.audio: AudioSetupWidget`, plus the old attribute names as aliases.

This task is a pure move. The existing tests are the safety net; the only test edits allowed are the retargeting in Step 1.

- [ ] **Step 1: Retarget the tests to the new module**

In `tests/test_settings_panel_audio_test.py`:

1. Add the import next to the existing `settings_panel_module` import:

```python
from voice2fritz.gui import audio_setup_widget as audio_setup_widget_module
```

2. In the fixtures `finalized_wav` and `recorded_peak`, change `settings_panel_module` to `audio_setup_widget_module` (two lines: `wav_is_finalized`, `wav_peak`).
3. In `test_echo_test_gives_up_when_file_never_finishes`, change `settings_panel_module._ECHO_FINALIZE_MAX_POLLS` to `audio_setup_widget_module._ECHO_FINALIZE_MAX_POLLS`.
4. Replace every `panel._advance_echo_test()` with `panel.audio._advance_echo_test()` and `panel._update_mic_level()` with `panel.audio._update_mic_level()`:

```bash
sed -i 's/panel\._advance_echo_test()/panel.audio._advance_echo_test()/; s/panel\._update_mic_level()/panel.audio._update_mic_level()/' tests/test_settings_panel_audio_test.py
```

(Each line holds at most one call, so no `g` flag is needed; check with `grep -n "panel\._" tests/test_settings_panel_audio_test.py`, which must print nothing.)

Leave the `settings_panel_module.describe_address` and `settings_panel_module.QLocale` patches unchanged: those stay in `settings_panel.py`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/python -m pytest tests/test_settings_panel_audio_test.py -q`
Expected: FAIL at collection with `ImportError: cannot import name 'audio_setup_widget'`.

- [ ] **Step 3: Create the widget (code moved from `SettingsPanel`)**

Create `src/voice2fritz/gui/audio_setup_widget.py`:

```python
import os
import tempfile

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QWidget,
)

from voice2fritz import config
from voice2fritz.audio import populate_and_restore_devices, wav_is_finalized, wav_peak
from voice2fritz.i18n import tr

_LEVEL_POLL_MS = 100
ECHO_RECORD_MS = 3000
ECHO_PLAYBACK_MS = 3300
_ECHO_FINALIZE_POLL_MS = 100
_ECHO_FINALIZE_MAX_POLLS = 20
# A muted mic records a peak of about 0-15; normal speech peaks in the thousands.
_SILENCE_PEAK_THRESHOLD = 200
_ECHO_TEST_PATH = os.path.join(tempfile.gettempdir(), "voice2fritz-echo-test.wav")


class AudioSetupWidget(QWidget):
    """Mic and speaker choice, the live mic level and the record-and-play-back echo test."""

    def __init__(self, sip_engine, parent=None):
        super().__init__(parent)
        self.sip_engine = sip_engine

        self.capture_combo = QComboBox()
        self.speaker_combo = QComboBox()

        self.mic_level_bar = QProgressBar()
        self.mic_level_bar.setRange(0, 100)
        self.mic_level_bar.setTextVisible(False)
        self.mic_level_bar.setFixedHeight(8)
        self.mic_level_bar.setToolTip(tr("Live microphone level"))

        self.echo_test_button = QPushButton(tr("Test mic && speaker"))
        self.echo_test_status = QLabel(tr("Records 3 seconds, then plays them back."))
        self.echo_test_status.setStyleSheet("color: #8a8f98;")
        echo_test_row = QHBoxLayout()
        echo_test_row.addWidget(self.echo_test_button)
        echo_test_row.addWidget(self.echo_test_status, 1)

        form = QFormLayout(self)
        form.setContentsMargins(0, 0, 0, 0)
        form.addRow(tr("Mic"), self.capture_combo)
        form.addRow(tr("Mic level"), self.mic_level_bar)
        form.addRow(tr("Speaker"), self.speaker_combo)
        form.addRow(tr("Audio test"), echo_test_row)

        populate_and_restore_devices(self.sip_engine, self.capture_combo, self.speaker_combo)

        self.capture_combo.currentIndexChanged.connect(self._on_capture_changed)
        self.speaker_combo.currentIndexChanged.connect(self._on_playback_changed)

        self._level_timer = QTimer(self)
        self._level_timer.setInterval(_LEVEL_POLL_MS)
        self._level_timer.timeout.connect(self._update_mic_level)

        self._call_active = False
        self._echo_stage: str | None = None
        self._echo_timer = QTimer(self)
        self._echo_timer.setSingleShot(True)
        self._echo_timer.timeout.connect(self._advance_echo_test)
        self.echo_test_button.clicked.connect(self._start_echo_test)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        # Only hold the mic open while the widget is on screen.
        self.sip_engine.start_level_monitor()
        self._level_timer.start()

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self._level_timer.stop()
        self.sip_engine.stop_level_monitor()
        self.mic_level_bar.setValue(0)
        self._abort_echo_test()

    def resume_level_monitor(self) -> None:
        """Restart the level meter if on screen; another widget may have stopped the shared monitor."""
        if self.isVisible():
            self.sip_engine.start_level_monitor()
            self._level_timer.start()

    def show_saved_devices(self) -> None:
        """Select the saved devices in the combos, e.g. after another window changed them."""
        capture_name, playback_name = config.load_device_selection()
        for combo, name in ((self.capture_combo, capture_name), (self.speaker_combo, playback_name)):
            index = combo.findText(name) if name is not None else -1
            if index >= 0:
                # The device is already selected in the engine and saved; don't do it again.
                combo.blockSignals(True)
                combo.setCurrentIndex(index)
                combo.blockSignals(False)

    def _update_mic_level(self) -> None:
        self.mic_level_bar.setValue(round(self.sip_engine.capture_level() * 100))

    def set_call_active(self, active: bool) -> None:
        # A test during a call would mix its audio into the call.
        self._call_active = active
        if active:
            self._abort_echo_test()
        self.echo_test_button.setEnabled(not active)
        self.echo_test_button.setToolTip(tr("Not available during a call") if active else "")

    def _start_echo_test(self) -> None:
        try:
            self.sip_engine.start_echo_recording(_ECHO_TEST_PATH)
        except Exception as exc:
            self._fail_echo_test(exc)
            return
        self._echo_stage = "recording"
        self.echo_test_button.setEnabled(False)
        self.echo_test_status.setText(tr("Recording - speak now..."))
        self._echo_timer.start(ECHO_RECORD_MS)

    def _advance_echo_test(self) -> None:
        if self._echo_stage == "recording":
            # pjsua2 closes the recorder asynchronously; wait for the finished WAV file.
            self.sip_engine.stop_echo_recording()
            self._echo_stage = "finalizing"
            self._echo_finalize_polls = 0
            self.echo_test_status.setText(tr("Preparing playback..."))
            self._echo_timer.start(_ECHO_FINALIZE_POLL_MS)
        elif self._echo_stage == "finalizing":
            if not wav_is_finalized(_ECHO_TEST_PATH):
                self._echo_finalize_polls += 1
                if self._echo_finalize_polls >= _ECHO_FINALIZE_MAX_POLLS:
                    self._end_echo_test(tr("Test failed: the recording was not saved."))
                else:
                    self._echo_timer.start(_ECHO_FINALIZE_POLL_MS)
                return
            if wav_peak(_ECHO_TEST_PATH) < _SILENCE_PEAK_THRESHOLD:
                self._end_echo_test(tr("Recorded only silence - is the mic muted?"))
                return
            try:
                self.sip_engine.start_echo_playback(_ECHO_TEST_PATH)
            except Exception as exc:
                self._fail_echo_test(exc)
                return
            self._echo_stage = "playing"
            self.echo_test_status.setText(tr("Playing back..."))
            self._echo_timer.start(ECHO_PLAYBACK_MS)
        elif self._echo_stage == "playing":
            self._end_echo_test(tr("Done - did you hear yourself?"))

    def _fail_echo_test(self, exc: Exception) -> None:
        reason = getattr(exc, "reason", "") or str(exc)
        self._end_echo_test(tr("Test failed: {reason}", reason=reason))

    def _abort_echo_test(self) -> None:
        if self._echo_stage is not None:
            self._end_echo_test(tr("Test cancelled."))

    def _end_echo_test(self, status: str) -> None:
        self._echo_timer.stop()
        self._echo_stage = None
        self.sip_engine.stop_echo_recording()
        self.sip_engine.stop_echo_playback()
        try:
            os.remove(_ECHO_TEST_PATH)
        except OSError:
            pass
        self.echo_test_status.setText(status)
        self.echo_test_button.setEnabled(not self._call_active)

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

Before moving on, diff each moved method against the old `settings_panel.py` (`git show HEAD:src/voice2fritz/gui/settings_panel.py`). Only `showEvent` (no `update_call_audio_ip`), `set_call_active` (no language combo), and the two new methods `resume_level_monitor` and `show_saved_devices` may differ.

- [ ] **Step 4: Rewrite `SettingsPanel` to embed the widget**

Replace `src/voice2fritz/gui/settings_panel.py` with:

```python
from PySide6.QtCore import QLocale, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from voice2fritz import config
from voice2fritz.gui.audio_setup_widget import AudioSetupWidget
from voice2fritz.network import describe_address
from voice2fritz.i18n import LANGUAGES, language_from_locale, tr


class SettingsPanel(QWidget):
    accountSaved = Signal(config.AccountConfig)
    languageChanged = Signal(str)

    def __init__(self, sip_engine, parent=None):
        super().__init__(parent)
        self.sip_engine = sip_engine

        self.host_edit = QLineEdit()
        self.username_edit = QLineEdit()
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        # None until the FRITZ!Box has answered a registration with the saved password.
        self._password_status: str | None = None
        self.save_button = QPushButton(tr("Save"))
        self.save_button.setObjectName("addButton")
        self.google_priority_checkbox = QCheckBox(tr("Google sync overwrites local contacts with the same name"))
        self.google_priority_checkbox.setChecked(config.load_google_sync_overwrites_local())

        existing_account = config.load_config()
        if existing_account is not None:
            self.host_edit.setText(existing_account.host)
            self.username_edit.setText(existing_account.username)

        self.audio = AudioSetupWidget(sip_engine)
        # The audio controls used to live here; keep their names for callers.
        self.capture_combo = self.audio.capture_combo
        self.speaker_combo = self.audio.speaker_combo
        self.mic_level_bar = self.audio.mic_level_bar
        self.echo_test_button = self.audio.echo_test_button
        self.echo_test_status = self.audio.echo_test_status

        account_form = QFormLayout()
        account_form.addRow(tr("Host"), self.host_edit)
        account_form.addRow(tr("Username"), self.username_edit)
        account_form.addRow(tr("Password"), self.password_edit)

        self.call_audio_ip_label = QLabel()
        self.language_combo = QComboBox()
        for code, label in LANGUAGES.items():
            self.language_combo.addItem(label, code)
        self.language_combo.setCurrentIndex(max(0, self.language_combo.findData(config.load_language())))

        other_form = QFormLayout()
        other_form.addRow(tr("Call audio IP"), self.call_audio_ip_label)
        other_form.addRow(tr("Language"), self.language_combo)

        layout = QVBoxLayout(self)
        layout.addLayout(account_form)
        layout.addWidget(self.audio)
        layout.addLayout(other_form)
        layout.addWidget(self.google_priority_checkbox)
        layout.addWidget(self.save_button)
        layout.addStretch()

        self.save_button.clicked.connect(self._on_save)

        self.username_edit.textChanged.connect(self._update_password_hint)
        self._update_password_hint()

        self.language_combo.currentIndexChanged.connect(self._on_language_changed)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.update_call_audio_ip()

    def update_call_audio_ip(self) -> None:
        address = self.sip_engine.media_address
        if address is None:
            self.call_audio_ip_label.setText(tr("Not registered yet"))
            self.call_audio_ip_label.setStyleSheet("color: #8a8f98;")
            self.call_audio_ip_label.setToolTip("")
            return
        info = describe_address(address)
        if info.interface is None:
            # Network type is only known where interfaces can be inspected (Linux).
            self.call_audio_ip_label.setText(info.address)
        else:
            self.call_audio_ip_label.setText(f"{info.address} - {tr(info.kind)} ({info.interface})")
        if info.kind == "VPN":
            # The FRITZ!Box is on the LAN; audio routed through a VPN usually doesn't arrive.
            self.call_audio_ip_label.setStyleSheet("color: #d08a2c;")
            self.call_audio_ip_label.setToolTip(tr("Call audio goes through the VPN; the FRITZ!Box may not reach it."))
        else:
            self.call_audio_ip_label.setStyleSheet("")
            self.call_audio_ip_label.setToolTip(tr("Local address the FRITZ!Box sends call audio to."))

    def set_call_active(self, active: bool) -> None:
        self.audio.set_call_active(active)
        # Switching language restarts the app, which would drop the call.
        self.language_combo.setEnabled(not active)
        self.language_combo.setToolTip(tr("Not available during a call") if active else "")

    def _on_save(self) -> None:
        cfg = config.AccountConfig(
            host=self.host_edit.text(),
            username=self.username_edit.text(),
        )
        config.save_account(cfg, self.password_edit.text())
        # Never leave the password on screen; the hint reports its status instead.
        self.password_edit.clear()
        self._password_status = None
        self._update_password_hint()
        config.save_google_sync_overwrites_local(self.google_priority_checkbox.isChecked())
        self.accountSaved.emit(cfg)
        # Saving re-registers, which may pick a different local address.
        self.update_call_audio_ip()

    def set_registration_result(self, status: str | None) -> None:
        """Report how the FRITZ!Box answered the saved password: "ok", "rejected" or None (unknown)."""
        self._password_status = status
        self._update_password_hint()

    def _update_password_hint(self) -> None:
        username = self.username_edit.text()
        saved = bool(username) and bool(config.get_password(username))
        if not saved:
            hint, color = tr("No password saved"), None
        elif self._password_status == "ok":
            hint, color = tr("Password tested and working"), "#2fa84f"
        elif self._password_status == "rejected":
            hint, color = tr("Saved password was rejected - enter it again"), "#d0453a"
        else:
            hint, color = tr("Password saved (not tested yet)"), None
        self.password_edit.setPlaceholderText(hint)
        # A palette colour would lose against the app stylesheet; set it in QSS instead.
        self.password_edit.setStyleSheet(f"QLineEdit {{ placeholder-text-color: {color}; }}" if color else "")

    def _on_language_changed(self, index: int) -> None:
        language = self.language_combo.itemData(index)
        config.save_language(language)
        system_language = language_from_locale(QLocale.system().name())
        if language != system_language:
            # A deliberate choice against the system language: don't offer it at startup.
            config.save_declined_system_language(system_language)
        self.languageChanged.emit(language)
```

Compare with `git show HEAD:src/voice2fritz/gui/settings_panel.py`: every method that stays here must be unchanged except `showEvent`, `set_call_active` and `_on_save` (the latter already changed in Task 2).

- [ ] **Step 5: Run the full suite**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/python -m pytest -q`
Expected: all pass, the same count as after Task 2. In particular `test_level_monitor_runs_only_while_panel_is_shown` (the child widget gets show and hide events with the panel), `test_hiding_panel_during_call_keeps_button_disabled`, and all `tests/test_settings_dialog.py` and `tests/test_main_window.py` tests.

- [ ] **Step 6: Commit**

```bash
git add src/voice2fritz/gui/audio_setup_widget.py src/voice2fritz/gui/settings_panel.py tests/test_settings_panel_audio_test.py
git commit -m "refactor: move audio device choice and echo test into AudioSetupWidget

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Wizard button and `reload()` in Settings

**Files:**
- Modify: `src/voice2fritz/gui/settings_panel.py`
- Modify: `src/voice2fritz/i18n.py`
- Test: `tests/test_settings_panel_audio_test.py`

**Interfaces:**
- Consumes: `AudioSetupWidget.show_saved_devices()`, `AudioSetupWidget.resume_level_monitor()` (Task 3).
- Produces: `SettingsPanel.setupWizardRequested: Signal()`, `SettingsPanel.setup_wizard_button: QPushButton`, `SettingsPanel.reload() -> None`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_settings_panel_audio_test.py`:

```python
def test_setup_wizard_button_requests_the_wizard(panel, qtbot):
    with qtbot.waitSignal(panel.setupWizardRequested, timeout=1000):
        panel.setup_wizard_button.click()


def test_setup_wizard_button_is_disabled_during_call(panel):
    panel.set_call_active(True)
    assert not panel.setup_wizard_button.isEnabled()
    assert panel.setup_wizard_button.toolTip() == "Not available during a call"

    panel.set_call_active(False)
    assert panel.setup_wizard_button.isEnabled()
    assert panel.setup_wizard_button.toolTip() == ""


def test_reload_shows_account_saved_elsewhere(panel, monkeypatch):
    monkeypatch.setattr(
        config, "load_config", lambda path=config.DEFAULT_CONFIG_PATH: config.AccountConfig("192.168.178.1", "620")
    )
    monkeypatch.setattr(config, "get_password", lambda username: "secret12")

    panel.reload()

    assert panel.host_edit.text() == "192.168.178.1"
    assert panel.username_edit.text() == "620"
    assert panel.password_edit.placeholderText() == "Password saved (not tested yet)"


def test_reload_restarts_level_monitor_stopped_by_another_window(panel):
    panel.show()
    panel.sip_engine.stop_level_monitor()  # what the wizard's audio page does when it hides

    panel.reload()

    assert panel.sip_engine.events[-1] == "monitor on"


def test_reload_shows_devices_chosen_elsewhere(qtbot, monkeypatch, finalized_wav, recorded_peak):
    from voice2fritz.audio import AudioDevice

    engine = _RecordingEngine()
    engine.list_devices = lambda: [
        AudioDevice(id=0, name="Built-in Mic", has_input=True, has_output=False),
        AudioDevice(id=1, name="Headset", has_input=True, has_output=True),
    ]
    panel = SettingsPanel(engine)
    qtbot.addWidget(panel)
    monkeypatch.setattr(config, "load_device_selection", lambda path=config.DEFAULT_CONFIG_PATH: ("Headset", "Headset"))

    panel.reload()

    assert panel.capture_combo.currentText() == "Headset"
    assert panel.speaker_combo.currentText() == "Headset"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/python -m pytest tests/test_settings_panel_audio_test.py -q -k "wizard or reload"`
Expected: FAIL with `AttributeError: 'SettingsPanel' object has no attribute 'setupWizardRequested'` (and `setup_wizard_button`, `reload`).

- [ ] **Step 3: Implement**

In `src/voice2fritz/gui/settings_panel.py`:

1. Add the signal under `languageChanged = Signal(str)`:

```python
    setupWizardRequested = Signal()
```

2. In `__init__`, before `self.host_edit = QLineEdit()`:

```python
        self.setup_wizard_button = QPushButton(tr("Setup wizard..."))
```

3. In the layout block, make the button the first widget:

```python
        layout = QVBoxLayout(self)
        layout.addWidget(self.setup_wizard_button)
        layout.addLayout(account_form)
```

4. After `self.save_button.clicked.connect(self._on_save)`:

```python
        self.setup_wizard_button.clicked.connect(self.setupWizardRequested)
```

5. At the end of `set_call_active`:

```python
        self.setup_wizard_button.setEnabled(not active)
        self.setup_wizard_button.setToolTip(tr("Not available during a call") if active else "")
```

6. Add after `set_registration_result`:

```python
    def reload(self) -> None:
        """Show what another window (the setup wizard) saved."""
        account = config.load_config()
        if account is not None:
            self.host_edit.setText(account.host)
            self.username_edit.setText(account.username)
        self._password_status = None
        self._update_password_hint()
        self.audio.show_saved_devices()
        self.audio.resume_level_monitor()
        self.update_call_audio_ip()
```

In `src/voice2fritz/i18n.py`, add to `_GERMAN` in the Settings section (next to `"Save": "Speichern",`):

```python
    "Setup wizard...": "Einrichtungsassistent...",
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/python -m pytest -q`
Expected: all pass, including `tests/test_i18n.py`.

- [ ] **Step 5: Commit**

```bash
git add src/voice2fritz/gui/settings_panel.py src/voice2fritz/i18n.py tests/test_settings_panel_audio_test.py
git commit -m "feat: add setup wizard button and reload to Settings

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Connect page

**Files:**
- Create: `src/voice2fritz/gui/setup_wizard.py` (Connect page only in this task)
- Modify: `src/voice2fritz/i18n.py`
- Test: `tests/test_setup_wizard.py`

**Interfaces:**
- Consumes: `classify_registration`, `REGISTRATION_TIMEOUT_MS` (Task 1); `config.save_account` (Task 2); `voice2fritz.network.describe_address(address) -> AddressInfo` (existing; `.kind == "VPN"` for VPNs); `sip_engine.registrationStateChanged: Signal(str)`, `sip_engine.register(host, username, password)`, `sip_engine.media_address: str | None` (existing).
- Produces: `DEFAULT_HOST = "fritz.box"`; `ConnectPage(sip_engine, parent=None)` with `host_edit`, `username_edit`, `password_edit`, `connect_button`, `status_label`, `vpn_label`, `host() -> str`, `isComplete() -> bool`, and a `_timer` (single-shot `QTimer`).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_setup_wizard.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/python -m pytest tests/test_setup_wizard.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'voice2fritz.gui.setup_wizard'`

- [ ] **Step 3: Implement the Connect page**

Create `src/voice2fritz/gui/setup_wizard.py`:

```python
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWizardPage,
)

from voice2fritz import config
from voice2fritz.i18n import tr
from voice2fritz.network import describe_address
from voice2fritz.registration import REGISTRATION_TIMEOUT_MS, classify_registration

DEFAULT_HOST = "fritz.box"

_GREEN = "#2fa84f"
_RED = "#d0453a"
_ORANGE = "#d08a2c"


class ConnectPage(QWizardPage):
    """Saves the IP phone account, registers, and reports the FRITZ!Box's answer inline."""

    def __init__(self, sip_engine, parent=None):
        super().__init__(parent)
        self.sip_engine = sip_engine
        self.setTitle(tr("Connect"))
        self.setSubTitle(tr("Enter the username and password of the IP phone you just created."))

        self.host_edit = QLineEdit()
        self.username_edit = QLineEdit()
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        existing_account = config.load_config()
        self.host_edit.setText(existing_account.host if existing_account is not None else DEFAULT_HOST)
        if existing_account is not None:
            self.username_edit.setText(existing_account.username)

        self.connect_button = QPushButton(tr("Connect"))
        self.connect_button.setObjectName("addButton")
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        self.vpn_label = QLabel()
        self.vpn_label.setWordWrap(True)
        self.vpn_label.setStyleSheet(f"color: {_ORANGE};")
        self.vpn_label.hide()

        form = QFormLayout()
        form.addRow(tr("Host"), self.host_edit)
        form.addRow(tr("Username"), self.username_edit)
        form.addRow(tr("Password"), self.password_edit)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.connect_button)
        layout.addWidget(self.status_label)
        layout.addWidget(self.vpn_label)
        layout.addStretch()

        self._connected = False
        # The account of the Connect press still waiting for an answer, else None.
        self._pending: config.AccountConfig | None = None
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(REGISTRATION_TIMEOUT_MS)
        self._timer.timeout.connect(self._on_timeout)

        for edit in (self.host_edit, self.username_edit, self.password_edit):
            edit.textChanged.connect(self._on_fields_changed)
        self.connect_button.clicked.connect(self._on_connect)
        sip_engine.registrationStateChanged.connect(self._on_registration_state_changed)
        self._update_connect_button()

    def host(self) -> str:
        return self.host_edit.text().strip() or DEFAULT_HOST

    def isComplete(self) -> bool:
        return self._connected

    def _fields_filled(self) -> bool:
        return all(edit.text().strip() for edit in (self.host_edit, self.username_edit, self.password_edit))

    def _update_connect_button(self) -> None:
        self.connect_button.setEnabled(self._fields_filled() and self._pending is None)

    def _set_status(self, text: str, color: str | None) -> None:
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color};" if color else "")

    def _set_connected(self, connected: bool) -> None:
        if connected != self._connected:
            self._connected = connected
            self.completeChanged.emit()

    def _on_fields_changed(self) -> None:
        # A shown result (or a pending one) no longer matches the fields.
        self._pending = None
        self._timer.stop()
        self._set_status("", None)
        self.vpn_label.hide()
        self._set_connected(False)
        self._update_connect_button()

    def _on_connect(self) -> None:
        cfg = config.AccountConfig(host=self.host_edit.text().strip(), username=self.username_edit.text().strip())
        password = self.password_edit.text()
        config.save_account(cfg, password)
        self.vpn_label.hide()
        self._set_connected(False)
        self._pending = cfg
        self._set_status(tr("Connecting..."), None)
        self._update_connect_button()
        self._timer.start()
        try:
            self.sip_engine.register(cfg.host, cfg.username, password)
        except Exception as exc:
            detail = getattr(exc, "reason", "") or str(exc)
            self._finish(self._could_not_connect(detail), _RED)

    def _on_registration_state_changed(self, text: str) -> None:
        if self._pending is None:
            return
        account = f"{self._pending.username}@{self._pending.host}"
        result = classify_registration(text)
        if result == "ok":
            self._finish(tr("Connected as {account}.", account=account), _GREEN)
            self._show_vpn_warning_if_needed()
            self._set_connected(True)
        elif result == "rejected":
            self._finish(
                tr("The FRITZ!Box rejected the login. Use the username and password of the IP phone, not the FRITZ!Box login."),
                _RED,
            )
        else:
            self._finish(self._could_not_connect(text), _RED)

    def _on_timeout(self) -> None:
        if self._pending is None:
            return
        host = self._pending.host
        self._finish(
            tr("No answer from {host}. Try 192.168.178.1, and check that this computer is not on the guest WLAN.", host=host),
            _RED,
        )

    def _could_not_connect(self, detail: str) -> str:
        return tr(
            "Could not connect: {detail}. Check the host, and that this computer is not on the guest WLAN.",
            detail=detail,
        )

    def _finish(self, text: str, color: str) -> None:
        self._pending = None
        self._timer.stop()
        self._set_status(text, color)
        self._update_connect_button()

    def _show_vpn_warning_if_needed(self) -> None:
        address = self.sip_engine.media_address
        if address is not None and describe_address(address).kind == "VPN":
            self.vpn_label.setText(
                tr("Call audio goes through the VPN; the FRITZ!Box may not reach it. Turn off the VPN and restart voice2fritz.")
            )
            self.vpn_label.show()
```

Note: `vpn_label.show()` on a page that is not itself shown leaves `isVisible()` false; that is why the tests check `isHidden()`.

- [ ] **Step 4: Add the German strings**

In `src/voice2fritz/i18n.py`, add a new section at the end of `_GERMAN` (before the closing `}`, after the network kinds), and check first with `grep -n '"Connect"' src/voice2fritz/i18n.py` that `"Connect"` does not exist yet:

```python
    # Setup wizard (voice2fritz.gui.setup_wizard)
    "Connect": "Verbinden",
    "Enter the username and password of the IP phone you just created.":
        "Gib Benutzername und Kennwort des eben angelegten IP-Telefons ein.",
    "Connecting...": "Verbinde...",
    "Connected as {account}.": "Verbunden als {account}.",
    "The FRITZ!Box rejected the login. Use the username and password of the IP phone, not the FRITZ!Box login.":
        "Die FRITZ!Box hat die Anmeldung abgelehnt. Verwende Benutzername und Kennwort des IP-Telefons, "
        "nicht die Anmeldung an der FRITZ!Box.",
    "Could not connect: {detail}. Check the host, and that this computer is not on the guest WLAN.":
        "Verbindung fehlgeschlagen: {detail}. Prüfe den Host und dass dieser Computer nicht im Gast-WLAN ist.",
    "No answer from {host}. Try 192.168.178.1, and check that this computer is not on the guest WLAN.":
        "Keine Antwort von {host}. Versuche 192.168.178.1 und prüfe, dass dieser Computer nicht im Gast-WLAN ist.",
    "Call audio goes through the VPN; the FRITZ!Box may not reach it. Turn off the VPN and restart voice2fritz.":
        "Der Anrufton läuft über das VPN; die FRITZ!Box erreicht ihn eventuell nicht. "
        "Schalte das VPN aus und starte voice2fritz neu.",
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/python -m pytest -q`
Expected: all pass, including `tests/test_i18n.py`.

- [ ] **Step 6: Commit**

```bash
git add src/voice2fritz/gui/setup_wizard.py src/voice2fritz/i18n.py tests/test_setup_wizard.py
git commit -m "feat: add setup wizard connect page with inline registration check

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: The wizard and its other pages

**Files:**
- Modify: `src/voice2fritz/gui/setup_wizard.py`
- Modify: `src/voice2fritz/i18n.py`
- Test: `tests/test_setup_wizard.py`

**Interfaces:**
- Consumes: `ConnectPage`, `DEFAULT_HOST` (Task 5); `AudioSetupWidget` (Task 3); `voice2fritz.i18n.current_language() -> str` (existing).
- Produces: `SetupWizard(sip_engine, parent=None)` (a `QWizard`) with attributes `connect_page: ConnectPage`, `audio_page: AudioPage`; methods `open_fritzbox() -> None`, `set_call_active(active: bool) -> None`. `AudioPage.audio: AudioSetupWidget`. `guide_url() -> str`.

- [ ] **Step 1: Write the failing tests**

In `tests/test_setup_wizard.py`, add these imports at the top with the others (change the existing `from voice2fritz.gui.setup_wizard import ConnectPage` line):

```python
from PySide6.QtWidgets import QWizard

from voice2fritz.gui.audio_setup_widget import AudioSetupWidget
from voice2fritz.gui.setup_wizard import ConnectPage, SetupWizard
from voice2fritz.i18n import set_language
```

Then append:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/python -m pytest tests/test_setup_wizard.py -q`
Expected: FAIL at collection with `ImportError: cannot import name 'SetupWizard'`.

- [ ] **Step 3: Implement the pages and the wizard**

In `src/voice2fritz/gui/setup_wizard.py`:

1. Replace the imports at the top with:

```python
from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWizard,
    QWizardPage,
)

from voice2fritz import config
from voice2fritz.gui.audio_setup_widget import AudioSetupWidget
from voice2fritz.i18n import current_language, tr
from voice2fritz.network import describe_address
from voice2fritz.registration import REGISTRATION_TIMEOUT_MS, classify_registration
```

2. Below `_ORANGE = "#d08a2c"` add:

```python
_GUIDE_BASE_URL = "https://github.com/drachenhort/voice2fritz/blob/master/docs/"


def guide_url() -> str:
    """Troubleshooting section of the FRITZ!Box setup guide, in the UI language."""
    if current_language() == "de":
        return _GUIDE_BASE_URL + "fritzbox-setup.de.md#fehlersuche"
    return _GUIDE_BASE_URL + "fritzbox-setup.md#troubleshooting"


def _text_label(html: str) -> QLabel:
    label = QLabel(html)
    label.setWordWrap(True)
    label.setOpenExternalLinks(True)
    return label


def _list_html(items: list[str], ordered: bool) -> str:
    tag = "ol" if ordered else "ul"
    return f"<{tag}>" + "".join(f"<li>{item}</li>" for item in items) + f"</{tag}>"


class _InfoPage(QWizardPage):
    """A page of explanations: an intro, a list, an optional note and "Open FRITZ!Box"."""

    def __init__(self, title, subtitle, items, ordered, note=None, open_fritzbox=None, parent=None):
        super().__init__(parent)
        self.setTitle(title)
        self.setSubTitle(subtitle)
        layout = QVBoxLayout(self)
        layout.addWidget(_text_label(_list_html(items, ordered)))
        if note is not None:
            layout.addWidget(_text_label(note))
        self.open_button = None
        if open_fritzbox is not None:
            self.open_button = QPushButton(tr("Open FRITZ!Box"))
            self.open_button.clicked.connect(open_fritzbox)
            layout.addWidget(self.open_button)
        layout.addStretch()


class AudioPage(QWizardPage):
    def __init__(self, sip_engine, parent=None):
        super().__init__(parent)
        self.setTitle(tr("Audio"))
        self.setSubTitle(tr("Choose your headset, then test it."))
        self.audio = AudioSetupWidget(sip_engine)
        layout = QVBoxLayout(self)
        layout.addWidget(self.audio)
        layout.addStretch()
```

3. At the end of the file, add:

```python
class SetupWizard(QWizard):
    """Walks a first-time user through the FRITZ!Box IP phone setup and configures voice2fritz."""

    def __init__(self, sip_engine, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("voice2fritz setup"))
        # Classic style follows the app palette; the modern style paints a white header.
        self.setWizardStyle(QWizard.WizardStyle.ClassicStyle)
        self.setOption(QWizard.WizardOption.NoBackButtonOnStartPage, True)
        self.setButtonText(QWizard.WizardButton.BackButton, tr("Back"))
        self.setButtonText(QWizard.WizardButton.NextButton, tr("Next"))
        self.setButtonText(QWizard.WizardButton.FinishButton, tr("Finish"))
        self.setButtonText(QWizard.WizardButton.CancelButton, tr("Cancel"))

        self.connect_page = ConnectPage(sip_engine)
        self.audio_page = AudioPage(sip_engine)

        self.addPage(
            _InfoPage(
                tr("Welcome"),
                tr("This wizard connects voice2fritz to your FRITZ!Box as an IP phone, step by step. Before you start, check that:"),
                [
                    tr("This computer is on your home network, by cable or WLAN. The guest WLAN will not work."),
                    tr("Any VPN is turned off for now."),
                    tr("You know the password for the FRITZ!Box web interface. It is often printed on a sticker on the bottom of the box."),
                    tr("Your headset is plugged in."),
                ],
                ordered=False,
            )
        )
        self.addPage(
            _InfoPage(
                tr("Check your phone number"),
                tr("Your FRITZ!Box needs at least one phone number from your internet provider."),
                [
                    tr("Click <b>Open FRITZ!Box</b> below and log in."),
                    tr("Go to <b>Telephony → Own Numbers</b>."),
                    tr("Check that at least one number has a green dot."),
                ],
                ordered=True,
                note=tr(
                    "If the list is empty, your provider has not set up telephony yet. Most providers do this "
                    "automatically. If yours does not, use the FRITZ!Box wizard for adding a phone number, with the "
                    "details your provider sent you."
                ),
                open_fritzbox=self.open_fritzbox,
            )
        )
        self.addPage(
            _InfoPage(
                tr("Create an IP phone"),
                tr("voice2fritz connects to the FRITZ!Box as an IP phone. Create one for it."),
                [
                    tr("In the FRITZ!Box, go to <b>Telephony → Telephony Devices</b>."),
                    tr("Click <b>Configure New Device</b>."),
                    tr("Choose <b>Telephone (with and without answering machine)</b> and click <b>Next</b>."),
                    tr("Choose <b>LAN/WLAN (IP telephone)</b> and click <b>Next</b>."),
                    tr("Enter a name, for example <b>voice2fritz</b>."),
                    tr("Choose a <b>username</b> and a <b>password</b>, and write both down."),
                    tr("Choose the <b>outgoing number</b> that people see when you call them."),
                    tr("Choose which <b>incoming calls</b> should ring in voice2fritz."),
                    tr("Finish the wizard. You may need to confirm with a button press on the box or on a DECT handset."),
                ],
                ordered=True,
                note=tr(
                    "The username and password are new credentials only for voice2fritz. "
                    "They are not your FRITZ!Box login."
                ),
                open_fritzbox=self.open_fritzbox,
            )
        )
        self.addPage(self.connect_page)
        self.addPage(self.audio_page)
        self.addPage(
            _InfoPage(
                tr("Done"),
                tr("voice2fritz is connected. Make a few test calls:"),
                [
                    tr("<b>Internal:</b> dial the internal number of a DECT handset, for example <b>**610</b>. This costs nothing."),
                    tr("<b>External:</b> call your mobile phone and check that both sides hear each other."),
                    tr("<b>Incoming:</b> call your landline from your mobile phone."),
                ],
                ordered=False,
                note=tr(
                    'If something does not work, see the <a href="{url}">troubleshooting section of the setup guide</a>.',
                    url=guide_url(),
                ),
            )
        )

    def open_fritzbox(self) -> None:
        QDesktopServices.openUrl(QUrl(f"http://{self.connect_page.host()}"))

    def set_call_active(self, active: bool) -> None:
        self.audio_page.audio.set_call_active(active)
```

`"→"` is a plain Unicode arrow inside UI text, not code; keep it.

- [ ] **Step 4: Add the German strings**

First check which keys exist: `grep -n -E '"(Back|Next|Finish|Audio|Done|Welcome|Cancel)"' src/voice2fritz/i18n.py`. `"Cancel"` already exists; add only the missing ones. Append to the setup wizard section of `_GERMAN`:

```python
    "voice2fritz setup": "voice2fritz einrichten",
    "Back": "Zurück",
    "Next": "Weiter",
    "Finish": "Fertigstellen",
    "Open FRITZ!Box": "FRITZ!Box öffnen",
    "Welcome": "Willkommen",
    "This wizard connects voice2fritz to your FRITZ!Box as an IP phone, step by step. Before you start, check that:":
        "Dieser Assistent verbindet voice2fritz Schritt für Schritt als IP-Telefon mit deiner FRITZ!Box. "
        "Bevor du anfängst, prüfe:",
    "This computer is on your home network, by cable or WLAN. The guest WLAN will not work.":
        "Dieser Computer ist per Kabel oder WLAN im Heimnetz. Das Gast-WLAN funktioniert nicht.",
    "Any VPN is turned off for now.": "Ein VPN ist vorerst ausgeschaltet.",
    "You know the password for the FRITZ!Box web interface. It is often printed on a sticker on the bottom of the box.":
        "Du kennst das Passwort der FRITZ!Box-Benutzeroberfläche. Es steht oft auf einem Aufkleber unten auf der Box.",
    "Your headset is plugged in.": "Dein Headset ist angeschlossen.",
    "Check your phone number": "Rufnummer prüfen",
    "Your FRITZ!Box needs at least one phone number from your internet provider.":
        "Deine FRITZ!Box braucht mindestens eine Rufnummer von deinem Internetanbieter.",
    "Click <b>Open FRITZ!Box</b> below and log in.": "Unten auf <b>FRITZ!Box öffnen</b> klicken und anmelden.",
    "Go to <b>Telephony → Own Numbers</b>.": "<b>Telefonie → Eigene Rufnummern</b> öffnen.",
    "Check that at least one number has a green dot.": "Prüfen, dass mindestens eine Rufnummer einen grünen Punkt hat.",
    "If the list is empty, your provider has not set up telephony yet. Most providers do this "
    "automatically. If yours does not, use the FRITZ!Box wizard for adding a phone number, with the "
    "details your provider sent you.":
        "Ist die Liste leer, hat dein Anbieter die Telefonie noch nicht eingerichtet. Die meisten Anbieter "
        "erledigen das automatisch. Falls nicht, nutze den Assistenten der FRITZ!Box zum Einrichten einer "
        "Rufnummer, mit den Daten aus den Unterlagen deines Anbieters.",
    "Create an IP phone": "IP-Telefon anlegen",
    "voice2fritz connects to the FRITZ!Box as an IP phone. Create one for it.":
        "voice2fritz meldet sich als IP-Telefon an der FRITZ!Box an. Lege dafür eines an.",
    "In the FRITZ!Box, go to <b>Telephony → Telephony Devices</b>.":
        "In der FRITZ!Box <b>Telefonie → Telefoniegeräte</b> öffnen.",
    "Click <b>Configure New Device</b>.": "<b>Neues Gerät einrichten</b> klicken.",
    "Choose <b>Telephone (with and without answering machine)</b> and click <b>Next</b>.":
        "<b>Telefon (mit und ohne Anrufbeantworter)</b> wählen und <b>Weiter</b> klicken.",
    "Choose <b>LAN/WLAN (IP telephone)</b> and click <b>Next</b>.":
        "<b>LAN/WLAN (IP-Telefon)</b> wählen und <b>Weiter</b> klicken.",
    "Enter a name, for example <b>voice2fritz</b>.": "Einen Namen eingeben, zum Beispiel <b>voice2fritz</b>.",
    "Choose a <b>username</b> and a <b>password</b>, and write both down.":
        "<b>Benutzername</b> und <b>Kennwort</b> festlegen und beides aufschreiben.",
    "Choose the <b>outgoing number</b> that people see when you call them.":
        "Die <b>ausgehende Rufnummer</b> wählen, die Angerufene sehen.",
    "Choose which <b>incoming calls</b> should ring in voice2fritz.":
        "Wählen, bei welchen <b>ankommenden Anrufen</b> voice2fritz klingeln soll.",
    "Finish the wizard. You may need to confirm with a button press on the box or on a DECT handset.":
        "Den Assistenten abschließen. Eventuell musst du per Tastendruck an der Box oder an einem "
        "DECT-Mobilteil bestätigen.",
    "The username and password are new credentials only for voice2fritz. "
    "They are not your FRITZ!Box login.":
        "Benutzername und Kennwort sind neue Zugangsdaten nur für voice2fritz. "
        "Sie sind nicht die Anmeldung an der FRITZ!Box.",
    "Audio": "Ton",
    "Choose your headset, then test it.": "Wähle dein Headset und teste es.",
    "Done": "Fertig",
    "voice2fritz is connected. Make a few test calls:": "voice2fritz ist verbunden. Mach ein paar Testanrufe:",
    "<b>Internal:</b> dial the internal number of a DECT handset, for example <b>**610</b>. This costs nothing.":
        "<b>Intern:</b> die interne Rufnummer eines DECT-Mobilteils wählen, zum Beispiel <b>**610</b>. "
        "Das kostet nichts.",
    "<b>External:</b> call your mobile phone and check that both sides hear each other.":
        "<b>Extern:</b> dein Handy anrufen und prüfen, ob beide Seiten sich hören.",
    "<b>Incoming:</b> call your landline from your mobile phone.":
        "<b>Eingehend:</b> vom Handy aus deine Festnetznummer anrufen.",
    'If something does not work, see the <a href="{url}">troubleshooting section of the setup guide</a>.':
        'Falls etwas nicht funktioniert, hilft die <a href="{url}">Fehlersuche in der Einrichtungsanleitung</a>.',
```

The dictionary keys built from adjacent string literals must join to exactly the same text as the `tr()` call; `test_every_tr_text_has_a_german_translation` fails if one space is off.

- [ ] **Step 5: Run tests to verify they pass**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/python -m pytest -q`
Expected: all pass, including `tests/test_i18n.py`.

- [ ] **Step 6: Commit**

```bash
git add src/voice2fritz/gui/setup_wizard.py src/voice2fritz/i18n.py tests/test_setup_wizard.py
git commit -m "feat: add setup wizard with FRITZ!Box steps, audio and test-call pages

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Open the wizard from the main window

**Files:**
- Modify: `src/voice2fritz/gui/main_window.py`
- Test: `tests/test_main_window.py`

**Interfaces:**
- Consumes: `SetupWizard(sip_engine, parent)`, `SetupWizard.set_call_active` (Task 6); `SettingsPanel.setupWizardRequested`, `SettingsPanel.reload()` (Task 4).
- Produces: `MainWindow.open_setup_wizard() -> None`, `MainWindow._setup_wizard: SetupWizard | None`.

- [ ] **Step 1: Write the failing tests**

In `tests/test_main_window.py`, add to the imports:

```python
from voice2fritz.gui.setup_wizard import SetupWizard
```

Add an autouse fixture next to the others, so the wizard never reads the real config:

```python
@pytest.fixture(autouse=True)
def no_saved_account(monkeypatch):
    monkeypatch.setattr(config_module, "load_config", lambda path=config_module.DEFAULT_CONFIG_PATH: None)
```

Append the tests:

```python
def test_settings_button_opens_setup_wizard(qtbot):
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    window.settings_panel.setup_wizard_button.click()

    assert isinstance(window._setup_wizard, SetupWizard)
    assert window._setup_wizard.isVisible()
    assert not window._setup_wizard.isModal()


def test_second_request_reuses_the_open_wizard(qtbot):
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    window.open_setup_wizard()
    first = window._setup_wizard
    window.open_setup_wizard()

    assert window._setup_wizard is first


def test_registration_failure_during_wizard_shows_no_popup(qtbot):
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)
    window.open_setup_wizard()

    engine.registrationStateChanged.emit("401 Unauthorized")
    engine.registrationFailed.emit("Authorization failed for 620@fritz.box: 401 Unauthorized")

    assert not hasattr(window, "_registration_error_box")
    assert window.sip_status_led.toolTip() == "401 Unauthorized"


def test_call_during_wizard_stops_its_echo_test(qtbot):
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)
    window.open_setup_wizard()
    audio = window._setup_wizard.audio_page.audio
    audio.echo_test_button.click()

    window.number_edit.setText("01234567")
    window.call_button.click()

    assert audio.echo_test_status.text() == "Test cancelled."
    assert not audio.echo_test_button.isEnabled()
    assert window.hangup_button.isEnabled()


def test_closing_the_wizard_reloads_settings(qtbot, monkeypatch):
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)
    reloads = []
    monkeypatch.setattr(window.settings_panel, "reload", lambda: reloads.append(True))
    window.open_setup_wizard()

    window._setup_wizard.reject()

    assert reloads == [True]
    assert window._setup_wizard is None


def test_registration_popups_return_after_the_wizard_closes(qtbot):
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)
    window.open_setup_wizard()
    window._setup_wizard.reject()

    engine.registrationFailed.emit("Authorization failed")

    assert window._registration_error_box.isVisible()
```

`test_call_during_wizard_stops_its_echo_test` relies on `MainWindow._on_call_clicked` (`src/voice2fritz/gui/main_window.py:435-450`), which calls `_set_call_button_active(True)` and enables `hangup_button` without needing a registered account.

- [ ] **Step 2: Run tests to verify they fail**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/python -m pytest tests/test_main_window.py -q -k "wizard"`
Expected: FAIL with `AttributeError: 'MainWindow' object has no attribute '_setup_wizard'` or `'open_setup_wizard'`.

- [ ] **Step 3: Implement**

In `src/voice2fritz/gui/main_window.py`:

1. Add the import after `from voice2fritz.gui.settings_panel import SettingsPanel`:

```python
from voice2fritz.gui.setup_wizard import SetupWizard
```

2. After `self.settings_panel.languageChanged.connect(self._on_language_changed)`:

```python
        self.settings_panel.setupWizardRequested.connect(self.open_setup_wizard)
```

3. As the first line of `_connect_signals` (it runs before `_on_call_ended`, which reads it):

```python
        self._setup_wizard: SetupWizard | None = None
```

4. At the top of `_show_registration_error`, before the existing comment:

```python
        if self._setup_wizard is not None:
            # The wizard shows registration results on its own page.
            return
```

5. At the end of `_set_call_button_active`:

```python
        if self._setup_wizard is not None:
            self._setup_wizard.set_call_active(active)
```

6. Add after `_show_settings_page`:

```python
    def open_setup_wizard(self) -> None:
        if self._setup_wizard is not None:
            self._setup_wizard.raise_()
            self._setup_wizard.activateWindow()
            return
        # Not modal: during a call that arrives meanwhile, Hang up must stay reachable.
        self._setup_wizard = SetupWizard(self.sip_engine, self)
        self._setup_wizard.finished.connect(self._on_setup_wizard_finished)
        self._setup_wizard.show()

    def _on_setup_wizard_finished(self) -> None:
        self._setup_wizard.deleteLater()
        self._setup_wizard = None
        self.settings_panel.reload()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/python -m pytest -q`
Expected: all pass, including every existing registration-popup test (the wizard is closed in those).

- [ ] **Step 5: Commit**

```bash
git add src/voice2fritz/gui/main_window.py tests/test_main_window.py
git commit -m "feat: open the setup wizard from Settings

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Changelog and manual check

**Files:**
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Add the changelog entry**

Under `## [Unreleased]` in `CHANGELOG.md`:

```markdown
### Added
- Setup wizard (Settings → "Setup wizard..."): explains step by step how
  to check the phone number and create an IP phone on the FRITZ!Box, then
  saves the account and shows right on the page whether the FRITZ!Box
  accepts it, sets up the headset and suggests test calls. English and
  German.
```

- [ ] **Step 2: Run the full suite once more**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/python -m pytest -q`
Expected: all pass.

- [ ] **Step 3: Manual check against the FRITZ!Box**

Start the app with `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/python -m voice2fritz.main` and check, in English and then German (switch in Settings, restart):

1. Settings → "Setup wizard..." opens the wizard as its own window; the main window stays usable.
2. "Open FRITZ!Box" opens `http://fritz.box` in the browser.
3. Connect page: a wrong password shows the rejected-login text; a wrong host (`fritz.boxx`) shows the could-not-connect or no-answer text within 20 s; correct credentials turn green and enable Next. No popups in any case.
4. Audio page: level bar moves; the echo test plays back.
5. Done page: the guide link opens the troubleshooting section.
6. After Finish, Settings shows the account and devices, the password hint says "Password tested and working" once registered, and the Settings level bar moves.
7. The wizard looks readable with the app theme (classic style, no white header).

Report each result. Anything that fails goes back to the owning task.

- [ ] **Step 4: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs: add setup wizard to changelog

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
