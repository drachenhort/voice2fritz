# Incoming-Call Popup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the blocking `QMessageBox.question` incoming-call dialog
with a GNOME-Calls-style popup (avatar, name, number, Answer/Decline),
always-on-top and non-modal, with a ringtone and auto-dismiss on remote
hangup.

**Architecture:** Two new standalone, independently testable units
(`IncomingCallPopup(QWidget)`, `ringtone.py`), then `MainWindow` wiring
that replaces `_on_incoming_call`'s `QMessageBox` call and extends
`_on_call_ended` to close a still-open popup.

**Tech Stack:** Python, PySide6 (`QtWidgets`, `QtMultimedia` — already
available in the installed PySide6 package, no new dependency), stdlib
`wave`/`math`/`struct` for ringtone synthesis.

## Global Constraints

- Popup is non-modal (`.show()`, never `.exec()`) and always-on-top
  (`Qt.WindowType.WindowStaysOnTopHint`).
- Avatar: initials circle for a named caller, generic 📞 glyph fallback
  for an unnamed one — no photo storage, no new `contacts.py` fields.
- Answer/Decline buttons reuse the existing `callButton`/`deleteButton`
  QSS object names from `theme.py` (green/red) — no new stylesheet rules
  needed.
- Ringtone: system freedesktop theme file first
  (`/usr/share/sounds/freedesktop/stereo/phone-incoming-call.oga`),
  synthesized WAV fallback cached at `~/.cache/voice2fritz/ringtone.wav`
  (stdlib `wave`, no bundled binary asset in the repo). All ringtone
  playback failures are silent no-ops — never raise, never block the
  call.
- Auto-dismiss: if the caller hangs up before Answer/Decline is clicked,
  the popup closes itself and the call logs as `"missed"`.
- `SipEngine`'s existing signal contracts (`incomingCall`, `callEnded`,
  `callStateChanged`, `registrationStateChanged`) are unchanged — only
  `MainWindow`'s response to them changes.

---

## File Structure

```
voice2fritz/
  src/voice2fritz/
    ringtone.py                        (new)
    gui/
      incoming_call_popup.py           (new)
      main_window.py                     (modified: incoming-call flow)
  tests/
    test_ringtone.py                   (new)
    test_incoming_call_popup.py        (new)
    test_main_window.py                  (modified)
```

---

### Task 1: `IncomingCallPopup`

**Files:**
- Create: `src/voice2fritz/gui/incoming_call_popup.py`
- Test: `tests/test_incoming_call_popup.py`

**Interfaces:**
- Produces: `class IncomingCallPopup(QWidget)` with:
  - `answered: Signal`, `declined: Signal` (no-arg)
  - `avatar_label: QLabel`, `name_label: QLabel`, `number_label: QLabel`
  - `answer_button: QPushButton`, `decline_button: QPushButton`
  - Constructor: `IncomingCallPopup(name: str, number: str, parent=None)`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_incoming_call_popup.py
from voice2fritz.gui.incoming_call_popup import IncomingCallPopup


def test_shows_name_and_number(qtbot):
    popup = IncomingCallPopup("Anna Schmidt", "+4917612345678")
    qtbot.addWidget(popup)

    assert popup.name_label.text() == "Anna Schmidt"
    assert popup.number_label.text() == "+4917612345678"


def test_shows_number_as_name_when_no_name(qtbot):
    popup = IncomingCallPopup("", "+4917612345678")
    qtbot.addWidget(popup)

    assert popup.name_label.text() == "+4917612345678"
    assert popup.number_label.text() == "+4917612345678"


def test_avatar_shows_initials_for_named_caller(qtbot):
    popup = IncomingCallPopup("Anna Schmidt", "+4917612345678")
    qtbot.addWidget(popup)

    assert popup.avatar_label.text() == "AS"


def test_avatar_shows_fallback_glyph_for_unnamed_caller(qtbot):
    popup = IncomingCallPopup("", "+4917612345678")
    qtbot.addWidget(popup)

    assert popup.avatar_label.text() == "📞"


def test_answer_button_emits_answered_signal(qtbot):
    popup = IncomingCallPopup("Anna Schmidt", "+4917612345678")
    qtbot.addWidget(popup)

    with qtbot.waitSignal(popup.answered, timeout=1000):
        popup.answer_button.click()


def test_decline_button_emits_declined_signal(qtbot):
    popup = IncomingCallPopup("Anna Schmidt", "+4917612345678")
    qtbot.addWidget(popup)

    with qtbot.waitSignal(popup.declined, timeout=1000):
        popup.decline_button.click()


def test_window_stays_on_top_flag_is_set(qtbot):
    from PySide6.QtCore import Qt

    popup = IncomingCallPopup("Anna Schmidt", "+4917612345678")
    qtbot.addWidget(popup)

    assert popup.windowFlags() & Qt.WindowType.WindowStaysOnTopHint
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/pytest tests/test_incoming_call_popup.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'voice2fritz.gui.incoming_call_popup'`

- [ ] **Step 3: Write `src/voice2fritz/gui/incoming_call_popup.py`**

```python
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

_AVATAR_COLORS = [
    "#e07a5f", "#3d5a80", "#81b29a", "#f2cc8f",
    "#9b5de5", "#00bbf9", "#f15bb5", "#00f5d4",
]
_FALLBACK_AVATAR_COLOR = "#5c6370"


def _initials(name: str) -> str:
    words = name.split()
    return "".join(word[0] for word in words[:2]).upper()


def _avatar_color(name: str) -> str:
    return _AVATAR_COLORS[sum(ord(c) for c in name) % len(_AVATAR_COLORS)]


class IncomingCallPopup(QWidget):
    answered = Signal()
    declined = Signal()

    def __init__(self, name: str, number: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Incoming call")
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)

        avatar_text = _initials(name) if name else "📞"
        avatar_color = _avatar_color(name) if name else _FALLBACK_AVATAR_COLOR
        self.avatar_label = QLabel(avatar_text)
        self.avatar_label.setFixedSize(64, 64)
        self.avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar_label.setStyleSheet(
            f"background-color: {avatar_color}; color: #ffffff; "
            f"border-radius: 32px; font-size: 22px; font-weight: bold;"
        )

        self.name_label = QLabel(name if name else number)
        self.name_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.number_label = QLabel(number)
        self.number_label.setStyleSheet("color: #8a8f98;")
        self.number_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.answer_button = QPushButton("📞 Answer")
        self.answer_button.setObjectName("callButton")
        self.decline_button = QPushButton("✕ Decline")
        self.decline_button.setObjectName("deleteButton")

        button_row = QHBoxLayout()
        button_row.addWidget(self.decline_button)
        button_row.addWidget(self.answer_button)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.addWidget(self.avatar_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.name_label)
        layout.addWidget(self.number_label)
        layout.addLayout(button_row)

        self.answer_button.clicked.connect(self.answered.emit)
        self.decline_button.clicked.connect(self.declined.emit)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/pytest tests/test_incoming_call_popup.py -v`
Expected: PASS (7 passed).

- [ ] **Step 5: Commit**

```bash
git add src/voice2fritz/gui/incoming_call_popup.py tests/test_incoming_call_popup.py
git commit -m "feat: add IncomingCallPopup (avatar, name/number, Answer/Decline)"
```

---

### Task 2: `ringtone.py`

**Files:**
- Create: `src/voice2fritz/ringtone.py`
- Test: `tests/test_ringtone.py`

**Interfaces:**
- Produces: `play_ringtone() -> None`, `stop_ringtone() -> None`,
  `DEFAULT_RINGTONE_CACHE_PATH: Path` (module-level, mutable by
  monkeypatch — read inside functions at call time, not baked into a
  default argument), `_synthesize_ringtone(path: Path | None = None) -> Path`,
  `_system_ringtone_path() -> Path | None`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_ringtone.py
import wave

from voice2fritz import ringtone


def test_synthesize_ringtone_writes_valid_wav_file(tmp_path):
    target = tmp_path / "ring.wav"

    result = ringtone._synthesize_ringtone(target)

    assert result == target
    assert target.exists()
    with wave.open(str(target), "rb") as wav_file:
        assert wav_file.getnchannels() == 1
        assert wav_file.getsampwidth() == 2
        assert wav_file.getnframes() > 0


def test_synthesize_ringtone_is_idempotent(tmp_path):
    target = tmp_path / "ring.wav"

    ringtone._synthesize_ringtone(target)
    first_mtime = target.stat().st_mtime_ns
    ringtone._synthesize_ringtone(target)

    assert target.stat().st_mtime_ns == first_mtime


def test_system_ringtone_path_returns_existing_file(monkeypatch, tmp_path):
    theme_file = tmp_path / "phone-incoming-call.oga"
    theme_file.write_bytes(b"fake-audio")
    monkeypatch.setattr(ringtone, "_THEME_PATHS", [theme_file])

    assert ringtone._system_ringtone_path() == theme_file


def test_system_ringtone_path_returns_none_when_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(ringtone, "_THEME_PATHS", [tmp_path / "missing.oga"])

    assert ringtone._system_ringtone_path() is None


def test_play_and_stop_ringtone_do_not_raise(qtbot, monkeypatch, tmp_path):
    monkeypatch.setattr(ringtone, "DEFAULT_RINGTONE_CACHE_PATH", tmp_path / "ring.wav")
    monkeypatch.setattr(ringtone, "_THEME_PATHS", [tmp_path / "missing.oga"])

    ringtone.play_ringtone()
    ringtone.stop_ringtone()


def test_play_ringtone_never_raises_even_if_synthesis_fails(monkeypatch):
    def _boom(path=None):
        raise OSError("disk full")

    monkeypatch.setattr(ringtone, "_synthesize_ringtone", _boom)
    monkeypatch.setattr(ringtone, "_THEME_PATHS", [])

    ringtone.play_ringtone()
    ringtone.stop_ringtone()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/pytest tests/test_ringtone.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'voice2fritz.ringtone'`

- [ ] **Step 3: Write `src/voice2fritz/ringtone.py`**

```python
import math
import struct
import wave
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QSoundEffect

DEFAULT_RINGTONE_CACHE_PATH = Path.home() / ".cache" / "voice2fritz" / "ringtone.wav"

_THEME_PATHS = [
    Path("/usr/share/sounds/freedesktop/stereo/phone-incoming-call.oga"),
]

_effect: QSoundEffect | None = None


def _system_ringtone_path() -> Path | None:
    for path in _THEME_PATHS:
        if path.exists():
            return path
    return None


def _synthesize_ringtone(path: Path | None = None) -> Path:
    if path is None:
        path = DEFAULT_RINGTONE_CACHE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return path

    sample_rate = 44100
    frequencies = (950, 1400)
    tone_seconds = 0.4
    silence_seconds = 0.2

    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)

        for frequency in frequencies:
            for i in range(int(sample_rate * tone_seconds)):
                value = int(32767 * 0.5 * math.sin(2 * math.pi * frequency * i / sample_rate))
                wav_file.writeframesraw(struct.pack("<h", value))
        for i in range(int(sample_rate * silence_seconds)):
            wav_file.writeframesraw(struct.pack("<h", 0))

    return path


def play_ringtone() -> None:
    global _effect
    try:
        source_path = _system_ringtone_path() or _synthesize_ringtone()
        effect = QSoundEffect()
        effect.setSource(QUrl.fromLocalFile(str(source_path)))
        effect.setLoopCount(QSoundEffect.Infinite)
        effect.play()
        _effect = effect
    except Exception:
        _effect = None


def stop_ringtone() -> None:
    global _effect
    try:
        if _effect is not None:
            _effect.stop()
    except Exception:
        pass
    finally:
        _effect = None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/pytest tests/test_ringtone.py -v`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add src/voice2fritz/ringtone.py tests/test_ringtone.py
git commit -m "feat: add ringtone playback (system theme + synthesized fallback)"
```

---

### Task 3: Wire the popup and ringtone into `MainWindow`

**Files:**
- Modify: `src/voice2fritz/gui/main_window.py`
- Modify: `tests/test_main_window.py`

**Interfaces:**
- Consumes: `IncomingCallPopup` (Task 1), `ringtone.play_ringtone`/`ringtone.stop_ringtone` (Task 2).
- Produces: `MainWindow.incoming_popup: IncomingCallPopup | None`. Removes
  the `QMessageBox.question` call from `_on_incoming_call` and the
  now-unused `QMessageBox` import.

- [ ] **Step 1: Update existing incoming-call tests**

In `tests/test_main_window.py`, replace the `QMessageBox` import (no
longer needed) and add a `ringtone` import:

```python
from voice2fritz import ringtone
```

Remove `QMessageBox` from the `from PySide6.QtWidgets import ...` line
(keep `QDockWidget`).

Add an autouse fixture near the top (alongside `no_device_persistence`)
so no test in this file plays a real sound:

```python
@pytest.fixture(autouse=True)
def no_ringtone_playback(monkeypatch):
    monkeypatch.setattr(ringtone, "play_ringtone", lambda: None)
    monkeypatch.setattr(ringtone, "stop_ringtone", lambda: None)
```

Replace `test_incoming_call_accept_answers_and_enables_controls`:

```python
def test_incoming_call_accept_answers_and_enables_controls(qtbot):
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    incoming_call = object()
    engine.incomingCall.emit(incoming_call)
    assert window.incoming_popup is not None

    window.incoming_popup.answered.emit()

    assert engine.answers == [incoming_call]
    assert window._active_call is incoming_call
    assert window.hangup_button.isEnabled()
    assert window.call_details.mute_button.isEnabled()
    assert window.call_details.name_label.text() == engine.remote_number
    assert window.incoming_popup is None
```

Replace `test_incoming_call_reject_hangs_up_and_resets_state`:

```python
def test_incoming_call_reject_hangs_up_and_resets_state(qtbot):
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    incoming_call = object()
    engine.incomingCall.emit(incoming_call)
    window.incoming_popup.declined.emit()

    assert engine.hangups == [incoming_call]
    assert window._active_call is None
    assert not window.hangup_button.isEnabled()
    assert not window.call_details.mute_button.isEnabled()
    assert window.incoming_popup is None
```

Replace `test_accepted_incoming_call_appends_log_entry`:

```python
def test_accepted_incoming_call_appends_log_entry(qtbot, monkeypatch):
    logged = []
    monkeypatch.setattr(call_log_module, "append_call_log_entry", lambda entry, path=call_log_module.DEFAULT_CALL_LOG_PATH: logged.append(entry))

    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    incoming_call = object()
    engine.incomingCall.emit(incoming_call)
    window.incoming_popup.answered.emit()
    window.hangup_button.click()

    assert len(logged) == 1
    assert logged[0].number == engine.remote_number
    assert logged[0].direction == "incoming"
```

Replace `test_rejected_incoming_call_appends_missed_log_entry`:

```python
def test_rejected_incoming_call_appends_missed_log_entry(qtbot, monkeypatch):
    logged = []
    monkeypatch.setattr(call_log_module, "append_call_log_entry", lambda entry, path=call_log_module.DEFAULT_CALL_LOG_PATH: logged.append(entry))

    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    incoming_call = object()
    engine.incomingCall.emit(incoming_call)
    window.incoming_popup.declined.emit()

    assert len(logged) == 1
    assert logged[0].number == engine.remote_number
    assert logged[0].direction == "missed"
    assert logged[0].duration_seconds == 0
```

- [ ] **Step 2: Add the new auto-dismiss test**

```python
def test_incoming_call_auto_dismisses_popup_on_remote_hangup(qtbot, monkeypatch):
    stopped = []
    monkeypatch.setattr(ringtone, "stop_ringtone", lambda: stopped.append(True))
    logged = []
    monkeypatch.setattr(call_log_module, "append_call_log_entry", lambda entry, path=call_log_module.DEFAULT_CALL_LOG_PATH: logged.append(entry))

    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    incoming_call = object()
    engine.incomingCall.emit(incoming_call)
    assert window.incoming_popup is not None

    engine.callEnded.emit()

    assert window.incoming_popup is None
    assert stopped == [True]
    assert logged[0].direction == "missed"
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/pytest tests/test_main_window.py -v`
Expected: FAIL — `AttributeError` on `window.incoming_popup` (doesn't
exist yet), and the accept/reject tests fail since `_on_incoming_call`
still calls the removed `QMessageBox.question`.

- [ ] **Step 4: Update `main_window.py` imports and `__init__`**

Update the imports at the top of `src/voice2fritz/gui/main_window.py`:

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
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from voice2fritz import call_log, config, contacts, ringtone
from voice2fritz.audio import input_devices, output_devices
from voice2fritz.gui.call_details_panel import CallDetailsPanel
from voice2fritz.gui.call_log_panel import CallLogPanel
from voice2fritz.gui.contacts_dialog import ContactsDialog
from voice2fritz.gui.incoming_call_popup import IncomingCallPopup
from voice2fritz.gui.settings_dialog import SettingsDialog
```

(`QMessageBox` is dropped from the import list — no longer used
anywhere in this file.)

In `__init__`, add `self.incoming_popup: IncomingCallPopup | None = None`
alongside the other instance attributes at the top:

```python
        self.sip_engine = sip_engine
        self._active_call = None
        self._call_direction: str | None = None
        self._call_number: str | None = None
        self._call_start_time: datetime | None = None
        self.incoming_popup: IncomingCallPopup | None = None
```

- [ ] **Step 5: Replace `_on_call_ended` and `_on_incoming_call`, add the new handlers**

Replace `_on_call_ended`:

```python
    def _on_call_ended(self) -> None:
        if self.incoming_popup is not None:
            self._close_incoming_popup()
            if self._call_direction == "incoming":
                self._call_direction = "missed"
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

        name = self._contact_name_for(self._call_number)
        self.incoming_popup = IncomingCallPopup(name, self._call_number or "")
        self.incoming_popup.answered.connect(self._on_incoming_call_answered)
        self.incoming_popup.declined.connect(self._on_incoming_call_declined)
        ringtone.play_ringtone()
        self.incoming_popup.show()
```

Add three new methods directly after it:

```python
    def _on_incoming_call_answered(self) -> None:
        self._close_incoming_popup()
        self.sip_engine.answer(self._active_call)
        self.hangup_button.setEnabled(True)
        self._set_dtmf_mode(True)
        name = self._contact_name_for(self._call_number)
        self.call_details.set_active_call(name, self._call_number or "")

    def _on_incoming_call_declined(self) -> None:
        self._close_incoming_popup()
        self._call_direction = "missed"
        self.sip_engine.hangup(self._active_call)
        self._on_call_ended()

    def _close_incoming_popup(self) -> None:
        ringtone.stop_ringtone()
        if self.incoming_popup is not None:
            self.incoming_popup.close()
            self.incoming_popup = None
```

**Why `_on_call_ended` handles the auto-dismiss case, not a second
`callEnded` connection:** `sip_engine.callEnded` is already connected once
to `_on_call_ended` in `_connect_signals` (unchanged) and fires on every
call end, including a remote hangup while the popup is still open and
unanswered. Adding a second, per-call `callEnded` connection inside
`_on_incoming_call` would double-fire cleanup (both the permanent
`_on_call_ended` connection and the new one) and log the call twice.
Routing auto-dismiss through the existing single `_on_call_ended` path
avoids that — it already runs on every call end, so checking
`self.incoming_popup is not None` there is sufficient and exclusive.

- [ ] **Step 6: Run tests to verify they pass**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/pytest tests/test_main_window.py -v`
Expected: PASS, all tests in the file.

- [ ] **Step 7: Run the full suite to confirm no regressions**

Run: `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/pytest -v`
Expected: PASS, all passing, zero failing.

- [ ] **Step 8: Manual verification against real hardware**

With the real FRITZ!Box 7590:
1. Run `LD_LIBRARY_PATH=~/.local/lib/pjsip .venv/bin/python -m voice2fritz.main`.
2. Call the registered number from another phone. Confirm the popup
   appears, stays on top of other windows, and a ringtone plays
   (system theme sound if available, otherwise the synthesized beep).
3. Confirm the avatar shows initials if the caller's number matches a
   saved contact with a name, otherwise the 📞 fallback glyph.
4. Click Answer — confirm the call connects, the popup closes, the
   ringtone stops, and Call Details shows the caller as usual.
5. Repeat and click Decline instead — confirm the call is rejected, the
   popup closes, the ringtone stops, and the call log shows it as missed.
6. Repeat and hang up from the *other* phone before answering/declining
   — confirm the popup auto-closes, the ringtone stops, and the call log
   shows it as missed.

If any pjsua2/PJSIP or window-manager behavior differs from expectations
here (e.g. `WindowStaysOnTopHint` not actually raising above other apps
under the user's specific window manager), adjust accordingly — expected
hardware/environment-specific verification work, not a plan defect,
consistent with this project's other hardware-touching tasks.

- [ ] **Step 9: Commit**

```bash
git add src/voice2fritz/gui/main_window.py tests/test_main_window.py
git commit -m "feat: replace blocking incoming-call dialog with IncomingCallPopup + ringtone"
```

---

## Self-Review Notes

- **Spec coverage:** non-modal always-on-top popup (Task 1, Task 3 Step 4-5) ✓; initials/fallback-glyph avatar (Task 1) ✓; Answer/Decline reusing existing `callButton`/`deleteButton` QSS (Task 1) ✓; system-theme + synthesized-fallback ringtone, silent-failure error handling (Task 2) ✓; auto-dismiss on remote hangup via the existing `callEnded`→`_on_call_ended` path, not a fragile per-call second connection (Task 3 Step 5, explained inline) ✓; all four pre-existing QMessageBox-based incoming-call tests migrated to drive the popup's signals directly, plus one new auto-dismiss test (Task 3 Steps 1-2) ✓; manual hardware verification covers popup visibility/stacking, ringtone, avatar, and all three exit paths (Task 3 Step 8) ✓.
- **Placeholder scan:** none — every step has full code or concrete manual-verification instructions.
- **Type consistency:** `IncomingCallPopup(name: str, number: str, parent=None)` and its `answered`/`declined` signals match identically between Task 1's definition and Task 3's `_on_incoming_call`/test call sites. `ringtone.play_ringtone()`/`ringtone.stop_ringtone()` (no args, no return) match between Task 2's definition and Task 3's call sites. `MainWindow.incoming_popup: IncomingCallPopup | None` name matches between its Step 4 declaration and every later reference (Steps 5, and all of Task 3's tests).
