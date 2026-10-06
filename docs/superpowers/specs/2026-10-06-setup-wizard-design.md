# voice2fritz Setup Wizard — Design Spec

Date: 2026-10-06

## Purpose

Users who have never set up VoIP on a FRITZ!Box need more than the bare
Host/Username/Password form in Settings. The
[FRITZ!Box setup guide](../../fritzbox-setup.md) explains the steps, but
lives outside the app. The setup wizard brings that guide into
voice2fritz as a step-by-step dialog that both explains what to do on the
FRITZ!Box and performs the voice2fritz side: it saves the account, checks
the registration live, and sets up audio.

Success: a first-time user opens the wizard from Settings, follows it
page by page, and ends up registered with working audio, without reading
the guide or seeing a registration error popup.

## Decisions

- The wizard explains **and** configures (not explain-only).
- It is reachable from the Settings page only. The first-run
  `SettingsDialog` in `main.py` stays unchanged.
- No screenshots. Pages use short numbered steps, menu paths in bold, and
  an "Open FRITZ!Box" button. Images can be added later without changing
  this design.
- Built on `QWizard`. Shared logic is extracted from `SettingsPanel` and
  `MainWindow` so Settings and the wizard use one code path.

## Entry Point

`SettingsPanel` gets a **"Setup wizard…"** button at the top of the page
and a `setupWizardRequested` signal that the button emits. The button is
disabled during a call (with the tooltip "Not available during a call"),
in `SettingsPanel.set_call_active`, like the echo test button.

`MainWindow` connects the signal to `open_setup_wizard()`, which creates
a `SetupWizard` and opens it as a modal window.

## Wizard Pages

1. **Welcome.** What the wizard does, then a checklist: computer on the
   home network (not the guest WLAN), VPN off, FRITZ!Box password at hand,
   headset plugged in.
2. **Phone number on the FRITZ!Box.** Steps from guide Step 1:
   open the FRITZ!Box, go to **Telephony → Own Numbers**, look for at
   least one number with a green dot; what to do if the list is empty.
   "Open FRITZ!Box" button.
3. **Create an IP phone.** Steps from guide Step 2 (Telephony Devices →
   Configure New Device → Telephone → LAN/WLAN (IP telephone) → name →
   username and password → outgoing number → incoming calls → confirm).
   States that the username and password are new credentials only for
   voice2fritz, not the FRITZ!Box login, and should be written down.
   "Open FRITZ!Box" button.
4. **Connect.** Host, Username and Password fields and a **Connect**
   button. Host is pre-filled with the saved host, or `fritz.box` if none.
   Username is pre-filled with the saved username. Password is always
   empty. Connect is disabled while host, username or password is empty.

   Pressing Connect saves the account with `config.save_account`, calls
   `sip_engine.register(host, username, password)`, starts the timeout
   timer and shows the status inline, never in a popup. If `register`
   raises, the page shows the "Could not connect" text with the
   exception as `{detail}` and stops the timer:

   | State | Shown |
   |---|---|
   | Waiting | "Connecting…" (Connect disabled until a result arrives) |
   | `classify_registration` → `"ok"` | Green: "Connected as {account}." |
   | `"rejected"` | Red: "The FRITZ!Box rejected the login. Use the username and password of the IP phone, not the FRITZ!Box login." |
   | `None` (other failure code) | Red: "Could not connect: {detail}. Check the host, and that this computer is not on the guest WLAN." |
   | Timeout | Red: "No answer from {host}. Try 192.168.178.1, and check that this computer is not on the guest WLAN." |

   After `"ok"`, if `describe_address(sip_engine.media_address).kind` is
   `"VPN"`, an orange line is added: "Call audio goes through the VPN;
   the FRITZ!Box may not reach it. Turn off the VPN and restart
   voice2fritz."

   The page reports `isComplete()` only after an `"ok"` result. Editing
   any field afterwards resets the page to not complete, so the shown
   result always matches the fields. Back always works.

   Only the first result after a Connect press is shown. Later
   registration updates (PJSIP keeps refreshing or retrying) are ignored
   until the next Connect press.
5. **Audio.** An `AudioSetupWidget`: mic and speaker dropdowns, mic level
   bar and echo test, behaving as in Settings (device choice applies and
   is saved immediately).
6. **Done.** Test-call suggestions: dial the internal number of a DECT
   handset (for example `**610`), call your mobile, call your own landline
   from your mobile. Points to the troubleshooting section of the setup
   guide. **Finish** closes the wizard.

**Cancel** closes the wizard at any point. Anything already saved by
Connect or a device choice stays saved. Nothing is rolled back.

"Open FRITZ!Box" calls `QDesktopServices.openUrl(QUrl(f"http://{host}"))`,
where `host` is the Connect page's host field, or `fritz.box` if empty.

## Components

### `voice2fritz/registration.py` (new)

Pure module, no Qt or pjsua2 imports, so the wizard and main window share
it without circular imports:

- `REGISTRATION_TIMEOUT_MS = 20_000` (moved from
  `main_window._REGISTRATION_VERIFY_TIMEOUT_MS`).
- `classify_registration(text: str) -> str | None`: `"ok"` when `text`
  starts with `"2"`, `"rejected"` when its status code is 401, 403 or 407,
  otherwise `None`. This is the logic now at `main_window.py:309-315`;
  `MainWindow._on_registration_state_changed` calls it instead.

### `config.save_account(cfg: AccountConfig, password: str) -> None` (new)

Calls `save_config(cfg)`, and `set_password(cfg.username, password)` when
`password` is not empty. `SettingsPanel._on_save` uses it in place of its
own two calls.

### `gui/audio_setup_widget.py` → `AudioSetupWidget(sip_engine)` (new, moved code)

Moved unchanged from `SettingsPanel`: `capture_combo`, `speaker_combo`,
`mic_level_bar`, `echo_test_button`, `echo_test_status`, the level-meter
timer started in `showEvent` and stopped in `hideEvent`, the echo-test
state machine and its constants, the device-change handlers, and
`set_call_active(active)` for the echo-test part. It lays out its rows in
its own `QFormLayout` (Mic, Mic level, Speaker, Audio test).

`SettingsPanel` contains one `AudioSetupWidget` as `self.audio` and keeps
the old attribute names as aliases (`self.capture_combo =
self.audio.capture_combo`, and so on, as `SettingsDialog` already does),
so existing tests and callers keep working. `SettingsPanel.set_call_active`
forwards to `self.audio.set_call_active` and still handles the language
combo and the new wizard button. The audio rows get their own label column,
so their labels may not line up exactly with the account rows.

### `gui/setup_wizard.py` → `SetupWizard(QWizard)` (new)

`SetupWizard(sip_engine, parent=None)`. One `QWizardPage` subclass per
page. The Connect page registers through `sip_engine.register` directly
rather than `MainWindow.register_account`, because that method catches
exceptions and reports them in a popup.
The Connect page connects to `sip_engine.registrationStateChanged` and
owns a single-shot `QTimer` with `REGISTRATION_TIMEOUT_MS`.

`SetupWizard.set_call_active(active)` forwards to the audio page's
`AudioSetupWidget`.

### `MainWindow` changes

- `open_setup_wizard()` creates `SetupWizard(self.sip_engine, self)`,
  keeps it in `self._setup_wizard`, connects `finished` to
  `_on_setup_wizard_finished`, and calls `open()`.
- While `self._setup_wizard` is not `None`, `_show_registration_error`
  returns without showing a popup (this covers `_on_registration_failed`
  and any verification still running). Wizard registrations never start
  main-window verification, so no "Settings verified" box appears.
  The status light and `settings_panel.set_registration_result` still
  update.
- `_set_call_button_active` (which already calls
  `settings_panel.set_call_active`) also calls
  `self._setup_wizard.set_call_active` when the wizard is open.
- `_on_setup_wizard_finished` sets `self._setup_wizard = None` and calls
  `settings_panel.reload()`.

### `SettingsPanel.reload()` (new)

Reloads host and username from `config.load_config()`, updates the
password hint, and restores the saved device choices into the combos.

## Translations

All new text goes through `tr()` and gets a German entry in `_GERMAN`.
The German pages use the German FRITZ!OS menu names as in
`docs/fritzbox-setup.de.md` (**Telefonie → Eigene Rufnummern**,
**Telefonie → Telefoniegeräte → Neues Gerät einrichten**, …). The
existing `test_every_tr_text_has_a_german_translation` and
`test_placeholders_match_between_languages` catch gaps.

## Testing

Tests run offscreen with a fake `sip_engine` and the stubbed keyring from
`conftest.py`.

- **Extraction safety:** the existing Settings panel and Settings dialog
  tests pass unchanged.
- `classify_registration`: table test (`"200 OK"` → `"ok"`; 401, 403,
  407 → `"rejected"`; 408, 503 → `None`).
- `config.save_account`: writes config, sets the password only when
  not empty.
- **Connect page:** Connect calls `sip_engine.register` with the entered
  values and saves the account; a raising `register` shows the
  could-not-connect text; `"200 OK"` shows green and completes the page;
  `"401 Unauthorized"` shows the wrong-login text and the page stays
  incomplete; `"503 …"` shows the could-not-connect text; timer timeout
  shows the no-answer text; a stubbed `describe_address` returning
  `"VPN"` adds the VPN warning; editing a field after success makes the
  page incomplete again; a later registration update after the first
  result does not change the shown result.
- **Other pages:** "Open FRITZ!Box" opens `http://<host>` and falls back
  to `http://fritz.box` (stubbed `QDesktopServices.openUrl`); the audio
  page contains an `AudioSetupWidget`.
- **MainWindow:** the Settings button opens the wizard; a registration
  failure while the wizard is open shows no popup but updates the status
  light; a call starting while the wizard is open aborts its echo test;
  closing the wizard calls `settings_panel.reload()`; the wizard button is
  disabled during a call.
- **Manual:** against a FRITZ!Box 7590: full run with correct
  credentials, one with a wrong password, one with a wrong host; English
  and German.

## Out of Scope

- Replacing the first-run `SettingsDialog` with the wizard.
- Screenshots or diagrams of the FRITZ!Box interface.
- Detecting the FRITZ!Box automatically or creating the IP phone through
  TR-064.
- Opening the wizard automatically after a registration error.
