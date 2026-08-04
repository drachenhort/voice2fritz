# voice2fritz Dialpad Restyle + Call Details Dock — Design Spec

Date: 2026-08-04

## Purpose

Restyle the dialer to closely match a phone-app mockup the user shared:
T9-lettered dialpad, a full-width green Call button, a two-line SIP
status header, and a new always-visible "Call Details" dock showing the
active call's info and controls (Mute/Speaker) — while explicitly
skipping Hold/Transfer/Video, which aren't built (Video was deliberately
disabled in the pjsip build; Hold/Transfer were never implemented).

Out of scope: converting Contacts/Settings into tabs (stay as modal
dialogs — explicit user decision); any Hold/Transfer/Video
functionality.

## Layout

Both docks move to the **left** side of the window, stacked (Call
Details above Call Log), leaving the dialpad + controls as the main
central content — reversing today's layout where Call Log alone was
docked on the right.

- `self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.call_details_dock)`
- `self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.log_dock)`

Adding two docks to the same area stacks them vertically by default in
Qt (no extra API needed) — Call Details ends up above Call Log since
it's added first.

## Components

### Dialpad restyle (`main_window.py`)

- Each dialpad digit gets T9 letters shown as decorative subtext below
  it. Mapping: `1`→"", `2`→"ABC", `3`→"DEF", `4`→"GHI", `5`→"JKL",
  `6`→"MNO", `7`→"PQRS", `8`→"TUV", `9`→"WXYZ", `*`→"", `0`→"+", `#`→"".
  `digit_buttons[digit]` itself stays an unchanged `QPushButton` with
  `.text()` equal to just the digit — DTMF sends the button's digit, and
  existing click/DTMF wiring must not change. The T9 letters are a
  separate, non-interactive `QLabel` (small font) placed below each
  button in its own `QVBoxLayout` cell within the dialpad grid, purely
  visual.
- `number_edit` gets a `backspace_button` (⌫) placed to its right in the
  same row; clicking it removes the last character:
  `self.number_edit.setText(self.number_edit.text()[:-1])`.
- `call_button` text changes from `"📞"` (icon-only) to `"📞 CALL"`, kept
  full-width by moving it out of the narrow `controls_column` into its
  own row spanning the dialpad's width, directly under the dialpad grid
  (matches the mockup's full-width green button under the keypad).
  `hangup_button`, `settings_button`, `contacts_button`, `log_button`
  remain in the narrower side column as today — `mute_button` moves out
  of this column entirely, see Call Details below.
- `status_label` (single line today) becomes two `QLabel`s: `sip_status_label`
  ("SIP Status: <state>") and `account_label` ("Account: <host>"),
  stacked at the top where `status_label` used to be.
  `sip_engine.registrationStateChanged`/`callStateChanged` connect to
  `sip_status_label.setText` (replacing the old direct connection to
  `status_label.setText`). `account_label`'s text is set once, when
  registration succeeds, from the host used in `_on_account_saved`
  (stored as `self._account_host`, set there and in the startup
  `config.load_config()` path in `main.py` — `main.py` already loads
  the account and calls `sip_engine.register(...)`, so it can call a
  new `MainWindow.set_account_host(host)` method right after
  constructing the window, mirroring how `main.py` already wires
  things).

### `CallDetailsPanel` (new, `src/voice2fritz/gui/call_details_panel.py`)

- `QWidget` with: `name_label` (contact name or number), `state_label`
  (e.g. "Active", "Ringing" — reuses whatever `callStateChanged` last
  sent), `duration_label` (live `MM:SS`, updated by a `QTimer` ticking
  once per second while a call is active), `mute_button`, and a
  `speaker_combo: QComboBox` (the existing playback-device dropdown,
  relocated here from the device row — `main_window.py`'s
  `playback_combo` becomes `CallDetailsPanel.speaker_combo`, wired the
  same way via signals passed through, since device selection logic
  already lives in `MainWindow`).
- Shown state (`set_active_call(name, number)`) vs idle state
  (`set_idle()`, shows "No active call", clears duration/timer, disables
  mute) are two explicit methods `MainWindow` calls from its existing
  call-lifecycle handlers (`_on_call_clicked`/`_on_incoming_call`'s
  accept path call `set_active_call`; `_on_call_ended` calls
  `set_idle()`).
- `mute_button` inside this panel replaces `MainWindow.mute_button` —
  `MainWindow` keeps a reference (`self.call_details.mute_button`) for
  existing `_on_mute_clicked` wiring rather than duplicating the
  enable/disable logic; `_set_dtmf_mode`-adjacent enable/disable calls
  (`self.mute_button.setEnabled(...)`) redirect to
  `self.call_details.mute_button.setEnabled(...)`.

### `MicSelector` note

The mockup's "Mic" selection isn't part of Call Details in the
mockup (it's implicit/handled elsewhere) — `capture_combo` (mic
selection) stays where it is today, in the device row under the
dialpad, unchanged. Only `playback_combo` (Speaker) moves into Call
Details, since the mockup explicitly puts a Speaker control in Call
Details but not a Mic one.

## Data Flow

Unchanged call-lifecycle signal wiring
(`registrationStateChanged`/`callStateChanged`/`callEnded`/`incomingCall`)
— this pass only changes *where* their effects are displayed
(`sip_status_label` instead of `status_label`; `CallDetailsPanel`'s
labels/timer instead of nothing) and adds the duration `QTimer`,
started in `set_active_call()` and stopped in `set_idle()`.

## Error Handling

No new failure modes — pure UI restructuring plus a `QTimer` for the
duration display (standard Qt, no error cases beyond what already
exists for call state).

## Testing

- T9 label rendering: unit-tested by asserting the decorative label
  text next to each `digit_buttons[digit]` matches the mapping above —
  doesn't touch `digit_buttons[digit].text()` itself (unchanged, still
  just the digit, so existing DTMF/dial tests keep passing unmodified).
- Backspace button: `pytest-qt` test — set `number_edit` text, click
  `backspace_button`, assert last character removed.
- `sip_status_label`/`account_label`: test that `registrationStateChanged`
  updates `sip_status_label` (replacing the old `status_label` test) and
  that `set_account_host("fritz.box")` sets `account_label.text()`
  correctly.
- `CallDetailsPanel`: unit-tested standalone (like `CallLogPanel`) —
  `set_active_call`/`set_idle` toggle the right visible state/text;
  `speaker_combo` selection still calls
  `sip_engine.select_playback_device` (moved wiring, same behavior,
  verified with the existing `FakeSipEngine` pattern). Duration timer
  tested by advancing `qtbot.wait()` and asserting `duration_label`
  updates — a short, bounded wait (e.g. just over 1 second) is
  acceptable here since it's testing real timer behavior, not
  something to mock away.
- `MainWindow`: existing call-flow tests (`test_completed_outgoing_call_appends_log_entry`
  etc.) updated to also assert `window.call_details.name_label`/
  `state_label` reflect the active call, and that `_on_call_ended`
  leaves the panel in its idle state.
