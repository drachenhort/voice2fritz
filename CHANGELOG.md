# Changelog

All notable changes to this project are documented in this file.

## [Unreleased]

## [0.4.0]

### Changed
- Dialpad buttons made more rectangular with tighter, more phone-like
  spacing: near-zero gaps between digits, a small 2px horizontal gap for
  separation, T9 letters sitting flush under their button instead of
  floating with a gap below it.

### Fixed
- Dialpad grid cells were absorbing leftover vertical space in the window
  and stretching, which pushed the vertically-centered T9 letters away
  from their button even with zero layout spacing. Cells are now pinned
  to a fixed size so they can't be stretched.

## [0.3.0]

### Added
- Contacts tab in the dock, alongside Call Log — click a contact to dial
  without opening the Contacts dialog. The Contacts nav button still opens
  the modal dialog too.

### Changed
- Non-dialpad controls regrouped for a more deliberate layout: Settings/
  Contacts as a nav row at the top, Hangup/Mute as a row under the CALL
  button (in place of a mixed vertical button column and a stray Mute
  button on the Call Details dock).
- Call Details and Call Log docks are now pinned in place — no drag,
  float, or close.
- Removed the Log button; the Call Log/Contacts dock is always visible.
- Tighter spacing in the dialpad grid.

### Fixed
- SIP status LED now shows green on a successful registration. It was
  stuck red because the registration status text pjsip reports back is a
  bare "OK", not "200 OK" as the LED's check expected.

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
