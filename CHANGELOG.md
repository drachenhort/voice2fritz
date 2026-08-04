# Changelog

All notable changes to this project are documented in this file.

## [Unreleased]

## [0.2.0]

### Added
- DTMF tone dialing from the dialpad or keyboard during an active call.
- Local phonebook (Contacts dialog): add/edit/delete/click-to-dial,
  sortable by name or number, with other phone number types
  (mobile/home/work) shown in a separate column.
- One-way Google Contacts sync into the local phonebook via the Google
  People API (OAuth), with a "Google wins" priority setting for name
  conflicts.
- Call log docked in the main window: tracks outgoing/incoming/missed
  calls with click-to-redial, live-updates as calls complete.
- GNOME-Calls-style incoming-call popup (avatar, caller name/number,
  Answer/Decline) replacing the old blocking dialog — always-on-top,
  non-modal, with a ringtone (system theme sound, synthesized fallback)
  and auto-dismiss if the caller hangs up first.
- SIP registration status LED (green/red) with the raw status text as a
  tooltip.
- App icon.

### Changed
- Main window restyled with a dark theme, a T9-lettered dialpad grid, a
  full-width Call button, and a "Call Details" dock (name, state, live
  call duration, mute) alongside the Call Log dock.
- Mic/Speaker device selection moved from the main window into the
  Settings dialog; changes still apply immediately.
- Dialpad digit buttons are bolder and larger for a more phone-like
  keypad look.

### Fixed
- Declining an incoming call now properly signals the caller's line to
  stop ringing (previously not always effective, depending on FritzBox
  call routing).

## [0.1.0]

### Added
- Initial release: SIP softphone for FRITZ!Box (Linux desktop, PySide6 +
  pjsua2).
- Register a FRITZ!Box SIP account; make and receive calls over a headset.
- Selectable audio input/output device, in-call mute.
- Account settings stored in `~/.config/voice2fritz/config.json`; SIP
  password stored via the system keyring, never in plaintext.
- Settings dialog reachable from the main window for editing the account
  and retrying registration.
