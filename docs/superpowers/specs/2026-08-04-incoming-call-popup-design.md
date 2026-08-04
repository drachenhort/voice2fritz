# voice2fritz Incoming-Call Popup — Design Spec

Date: 2026-08-04

## Purpose

Replace the current blocking `QMessageBox.question("Incoming call. Answer?")`
with a GNOME-Calls-style popup (mockup image the user shared): avatar,
caller name/number, Answer/Decline buttons — non-modal, always-on-top,
with a ringtone.

## Architecture

**New `IncomingCallPopup(QWidget)`** (own file, own tests) — a top-level,
non-modal window (`Qt.WindowStaysOnTopHint`, shown via `.show()`, not
`.exec()`), centered on screen. Contains:

- An initials-circle avatar: a `QLabel` with a colored round background
  drawn via stylesheet, generated from the caller name (first letters of
  up to two words, deterministic background color derived from the name)
  — falls back to a generic 📞 glyph when no contact name is known (empty
  name passed in).
- `name_label` (contact name, or the number if no name), `number_label`
  (always the raw number).
- `answer_button` (green, "📞 Answer" or similar) and `decline_button`
  (red, "✕ Decline").

Emits two signals: `answered = Signal()` and `declined = Signal()`.
`MainWindow` owns the actual `sip_engine.answer()`/`hangup()` calls —
the popup itself has no SIP engine dependency, same separation of
concerns as `CallLogPanel`/`CallDetailsPanel`.

**New `src/voice2fritz/ringtone.py`** — a small module wrapping
`QSoundEffect` (`PySide6.QtMultimedia`):

- `play_ringtone() -> None`: tries the freedesktop sound theme path
  (`/usr/share/sounds/freedesktop/stereo/phone-incoming-call.oga`,
  checked directly and via `XDG_DATA_DIRS` entries) with
  `setLoopCount(QSoundEffect.Infinite)`. If not found, synthesizes a short
  two-tone beep pattern as a WAV once into
  `~/.cache/voice2fritz/ringtone.wav` (via the stdlib `wave` module — no
  bundled binary asset committed to the repo) and loops that instead.
- `stop_ringtone() -> None`: stops playback.
- Both functions wrap their body in try/except and no-op silently on any
  failure (missing backend, unwritable cache dir, no audio device) — a
  broken ringtone must never block the popup or the call itself.

**`MainWindow._on_incoming_call`** (in `main_window.py`) replaces the
`QMessageBox.question` call entirely:

1. Build `IncomingCallPopup(name, number)` (name resolved via the
   existing `_contact_name_for(self._call_number)` helper), call
   `ringtone.play_ringtone()`, `popup.show()`.
2. Connect `popup.answered` to the existing accept logic (unchanged:
   `sip_engine.answer`, `hangup_button.setEnabled(True)`,
   `_set_dtmf_mode(True)`, `call_details.set_active_call(...)`), then
   close the popup.
3. Connect `popup.declined` to the existing reject logic (unchanged:
   `_call_direction = "missed"`, `sip_engine.hangup`,
   `_on_call_ended()`), then close the popup.
4. Connect `sip_engine.callEnded` (already emitted on remote hangup) to
   also close the popup + stop the ringtone if it's still open when the
   call ends without being answered — auto-dismiss.

All three paths converge on one `_close_incoming_popup()` helper that
stops the ringtone, closes the popup, and disconnects the popup's
signals — so a stray second signal (e.g. `callEnded` arriving a tick
after Answer was clicked) can't run cleanup twice.

## Data Flow

```
sip_engine.incomingCall(call)
  -> _on_incoming_call(call)
       -> IncomingCallPopup(name, number); ringtone.play_ringtone(); popup.show()
       -> exactly one of:
            popup.answered   -> accept logic -> _close_incoming_popup()
            popup.declined   -> reject logic -> _close_incoming_popup()
            sip_engine.callEnded (before either) -> missed-call logic -> _close_incoming_popup()
```

## Error Handling

- Ringtone file missing / `QSoundEffect` backend unavailable (headless
  test environments, no audio device): silent no-op, never raises.
- WAV synthesis is a one-time cache-miss cost; if
  `~/.cache/voice2fritz/` isn't writable, fall back to no sound rather
  than crashing.
- Popup signal double-fire (e.g. both `callEnded` and a button click
  racing) is prevented by disconnecting signals in
  `_close_incoming_popup()` before running any cleanup logic.

## Testing

- `IncomingCallPopup` (`tests/test_incoming_call_popup.py`, pytest-qt,
  same pattern as `test_call_details_panel.py`): construct with
  name/number, assert `name_label`/`number_label` text; click
  `answer_button`/`decline_button`, assert the corresponding signal
  fired (`qtbot.waitSignal`); assert the avatar shows initials for a
  named caller vs. the fallback 📞 glyph for an unnamed one (empty name).
- `ringtone.py` (`tests/test_ringtone.py`): test the fallback WAV
  synthesis function directly — call it, assert a valid WAV file is
  written to a temp cache dir (monkeypatched, not the real
  `~/.cache/voice2fritz/`). Test that `play_ringtone()`/`stop_ringtone()`
  don't raise when called back-to-back in this sandboxed/headless
  environment — not actual audible output, which is untestable in CI.
- `MainWindow` (`tests/test_main_window.py`): update
  `test_incoming_call_accept_answers_and_enables_controls` and
  `test_incoming_call_reject_hangs_up_and_resets_state` to drive the
  popup's `answered`/`declined` signals instead of mocking
  `QMessageBox`. Add a new test for the auto-dismiss path: emit
  `sip_engine.callEnded` before answering, assert the popup is closed
  and the call is logged as missed.

## Out of Scope

- Actual audible verification of the ringtone sound (manual, during
  hardware verification with a real incoming call).
- Any change to `SipEngine`, `sip_engine.py`'s existing
  `incomingCall`/`callEnded` signal contracts — this pass only changes
  how `MainWindow` responds to them.
