# Changelog

All notable changes to this project are documented in this file.

## [Unreleased]

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
