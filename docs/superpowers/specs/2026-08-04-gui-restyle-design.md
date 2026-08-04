# voice2fritz GUI Restyle — Design Spec

Date: 2026-08-04

## Purpose

Restyle `MainWindow` to look closer to a "Fritz!Phone Linux" mockup the
user shared, without adding new call-control functionality. This is a
scoped slice of a larger mockup (which also depicted a contacts/call-history
sidebar, hold/transfer/video controls, and a FRITZ!Box status panel) — those
are separate, out-of-scope pieces to be brainstormed individually later if
wanted.

Explicitly out of scope: contacts list, call history, hold, transfer,
video calling, FRITZ!Box status panel (external IP, DECT, answering
machine). No `SipEngine` interface changes. No new dependencies.

## Layout

The window widens into a two-column layout:

- **Left column:** the existing number entry field, followed by a 3×4
  numeric dialpad grid (`1 2 3 / 4 5 6 / 7 8 9 / * 0 #`). Clicking a
  digit button appends that character to the number field — an
  alternate input method, not new call functionality. The field remains
  directly editable by typing/pasting as today.
- **Right column:** a narrow vertical stack of four icon buttons, in this
  order: 📞 Call (green), ✕ Hang up, 🔇 Mute (checkable, matches current
  toggle behavior), ⚙ Settings. Each button gets a `QToolTip` with its
  text label ("Call", "Hang up", "Mute", "Settings") for clarity, since
  icons alone can be ambiguous.
- **Below both columns:** the mic/speaker device dropdowns, unchanged in
  behavior and position relative to each other (row layout as today).
- **Top:** the status label, unchanged in behavior (still shows
  registration/call state via the same signal connections).

No widget is removed. `number_edit`, `call_button`, `hangup_button`,
`mute_button`, `settings_button`, `capture_combo`, `playback_combo`, and
`status_label` all keep their existing names, types, and signal
connections — only their layout position and the button labels (now
icon characters instead of text) change. This preserves every existing
`main_window` test unmodified except tests that assert on button text.

## Styling

A dark theme is applied application-wide via a QSS stylesheet string set
on the `QApplication` instance in `main.py`, so it displays consistently
regardless of the user's desktop theme (Plasma/GNOME/etc). The stylesheet
covers: window/widget background, text color, input field background,
button background/hover states, and the green Call / neutral other-button
distinction shown in the mockup.

Icons are plain Unicode characters (📞, ✕, 🔇, ⚙) set as button text,
rendered via the system's emoji/symbol font. No icon asset files, no new
Python dependencies.

## Data Flow

Unchanged. Dialpad button clicks call a new small handler that appends
the clicked digit to `number_edit`'s current text — no interaction with
`SipEngine`. All other signal wiring (`registrationStateChanged`,
`callStateChanged`, `callEnded`, `incomingCall`, device-selection
persistence, settings save/re-register) stays exactly as implemented
today.

## Testing

- New unit test: clicking each dialpad button appends the correct
  character to `number_edit` (using `qtbot`, no `SipEngine` interaction
  needed — verifies the widget behavior directly, following the existing
  `pytest-qt` pattern).
- Existing tests updated only where they currently assert on button
  *text* (e.g. any assertion checking `call_button.text() == "Call"`) to
  instead assert on the icon character, or better, keep using
  `objectName`/direct widget reference rather than text where the test
  doesn't actually need to check the label. No test needs to assert on
  QSS styling — visual appearance is not unit-tested, consistent with
  this being a display-only concern.
- No changes needed to `sip_engine.py`, `config.py`, `audio.py`,
  `settings_dialog.py`, or their tests.
