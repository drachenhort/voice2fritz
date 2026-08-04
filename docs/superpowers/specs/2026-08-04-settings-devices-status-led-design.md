# voice2fritz Settings Device Move + Status LED + Dialpad Styling — Design Spec

Date: 2026-08-04

## Purpose

Streamline the main window: move mic/speaker device selection into the
Settings dialog (out of the always-visible dialpad window and Call
Details dock), replace the two-line "SIP Status: ..." / "Account: ..."
header with a single LED-style registration-status indicator, and make
the dialpad read more like a phone keypad (bigger/bolder digits, larger
T9 letters).

## Device Selection Move

`capture_combo` (Mic) and `speaker_combo` (Speaker) move entirely into
`SettingsDialog`. `MainWindow`'s central widget drops `device_row`
(the "Mic:" label + combo) entirely. `CallDetailsPanel` drops
`speaker_combo` and its "Speaker:" row entirely — becomes name/state/
duration/mute only.

`SettingsDialog` gains a `sip_engine` parameter
(`SettingsDialog(sip_engine, parent=None)`) — it needs it to call
`list_devices()`, `select_capture_device()`, `select_playback_device()`.
`MainWindow._on_settings_clicked` passes `self.sip_engine`.

Selecting a device in either combo applies **immediately** (same as
today): `currentIndexChanged` triggers `sip_engine.select_capture_device`/
`select_playback_device` plus `config.save_device_selection`,
independent of the account "Save" button.

**Shared helper (`src/voice2fritz/audio.py`):** device population and
saved-selection restoration is currently duplicated logic inside
`MainWindow._populate_devices`/`_restore_device_selection`. Since
`MainWindow` still needs devices selected automatically at app startup
(before the user ever opens Settings), this logic moves into a shared
function:

```python
def populate_and_restore_devices(
    sip_engine,
    capture_combo: QComboBox,
    playback_combo: QComboBox,
) -> None:
```

— populates both combos from `sip_engine.list_devices()`, restores the
saved selection via `config.load_device_selection()`, and calls
`sip_engine.select_capture_device`/`select_playback_device` for the
restored choice (mirrors current `_restore_device_selection` body
exactly, just parameterized over which combos to use). Both
`MainWindow.__init__` (startup) and `SettingsDialog.__init__` (populating
its own combos, so they show the current selection when the dialog
opens) call this same function. `MainWindow` no longer owns
`capture_combo`/`speaker_combo` as widgets at all — it has no combos of
its own after this change, only `SettingsDialog` does.

`_on_capture_changed`/`_on_playback_changed`/`_save_device_selection`
move from `MainWindow` to `SettingsDialog`, operating on
`self.capture_combo`/`self.speaker_combo` there instead.

## SIP Status LED

Replaces `sip_status_label` + `account_label` with a single small LED
indicator: `sip_status_led: QLabel`, a colored circle drawn via
`setStyleSheet` (fixed size, `border-radius` = half its width/height,
green `#2fa84f` background when the registration status text is
*exactly* `"200 OK"`, red `#a83b2f` for anything else — including the
initial "Not registered" state before any registration attempt).
`setToolTip(text)` is updated alongside the color on every
`registrationStateChanged` emission, so the raw status text (e.g.
`"200 OK"`, `"401 Unauthorized"`, `"Timeout"`) stays available on hover
for troubleshooting.

`account_label` and `MainWindow.set_account_host()` are removed
entirely, including their call sites in `main.py` (the
`window.set_account_host(account.host)` line after constructing
`MainWindow`) and `MainWindow._on_account_saved`.

`_on_call_state_changed` stops touching the top status line at all — it
already forwards to `self.call_details.set_state_text(text)`, which is
unchanged. This decouples the LED (pure registration health, driven only
by `registrationStateChanged`) from call state (shown exclusively in
Call Details, as it already mostly was).

## Dialpad Styling

New QSS class in `theme.py`:

```css
QPushButton#dialpadButton {
    font-weight: bold;
    font-size: 22px;
}
```

Applied via `button.setObjectName("dialpadButton")` on each of the 12
dialpad digit buttons (`0`-`9`, `*`, `#`) in the loop that builds them —
`digit_buttons[digit].text()` stays just the bare digit, unaffected;
this only changes the button's visual style, not its DTMF/dial behavior.

T9 letter labels' inline stylesheet changes from `font-size: 9px` to
`font-size: 11px` (color `#8a8f98` unchanged).

## Data Flow

Unchanged: `registrationStateChanged`/`callStateChanged`/`callEnded`/
`incomingCall` signal wiring is the same as before this pass — only
*where* `registrationStateChanged`'s text is displayed changes (LED
color + tooltip instead of a text label), and device-selection wiring
moves to a new owner (`SettingsDialog`) using the same underlying
`SipEngine` methods and `config` functions as before.

## Error Handling

No new failure modes — pure UI restructuring. The LED's green/red
determination is a simple string equality check (`text == "200 OK"`),
consistent with the codebase's existing string-based status handling
(e.g. call-log direction strings, call state text).

## Testing

- LED color/tooltip: `registrationStateChanged.emit("200 OK")` →
  `sip_status_led`'s stylesheet reflects the green color, `toolTip()`
  is `"200 OK"`. `emit("401 Unauthorized")` → red color, tooltip
  updated to `"401 Unauthorized"`. Initial state before any emission →
  red (not-registered default).
- `SettingsDialog`: new tests for device population (combos populated
  from a fake `sip_engine.list_devices()`), pre-selection from saved
  config (mirrors the existing `MainWindow` device-selection tests,
  relocated), and that changing either combo calls
  `sip_engine.select_capture_device`/`select_playback_device` plus
  `config.save_device_selection` immediately.
- `audio.populate_and_restore_devices`: unit-tested directly with a fake
  `sip_engine` and two bare `QComboBox` instances, asserting both
  population and saved-selection restoration/engine-selection calls
  happen correctly — this is the shared logic both `MainWindow` and
  `SettingsDialog` depend on, so it gets its own focused test rather
  than being tested only indirectly through both callers.
- `MainWindow`: existing device-selection tests
  (`test_device_combos_populated_from_engine`,
  `test_initial_device_selection_applied_at_startup`,
  `test_restores_saved_device_selection_on_startup`) move to
  `SettingsDialog`'s test file, adapted to construct
  `SettingsDialog(engine)` directly instead of `MainWindow(engine)`.
  Existing `sip_status_label`/`account_label` tests
  (`test_registration_state_updates_status_label`,
  `test_set_account_host_updates_account_label`) are replaced by the
  LED tests above. `window.call_details.speaker_combo` references in
  any remaining `MainWindow` tests are removed (no longer exists).
- Dialpad styling: no new automated test — visual-only QSS/stylesheet
  change, not meaningfully assertable via `objectName()` beyond what
  already exists implicitly (styling correctness verified manually).

## Out of Scope

- Any change to how registration/call-state signals are emitted by
  `SipEngine` — this pass only changes how `MainWindow` displays them.
- Any Mic-equivalent "quick access" control remaining in Call Details or
  the main window — per this pass, device selection lives solely in
  Settings now.
