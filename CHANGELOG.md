# Changelog

All notable changes to this project are documented in this file.

## [Unreleased]

## [0.13.0]

### Added
- On startup the app checks the system language. If it's supported but
  not the language set in voice2fritz, it asks (in that language)
  whether to switch; accepting applies it immediately. A "no" is
  remembered until the system language changes, and so is choosing a
  different language in Settings.

## [0.12.0]

### Added
- Experimental Windows build: a GitHub workflow compiles pjproject with
  Visual Studio, packages the app with PyInstaller and attaches
  `voice2fritz-<version>-windows-x64.zip` to each release. Untested on
  real Windows hardware.

### Changed
- voice2fritz is now licensed under the GNU General Public License
  v3.0 or later (previously MIT).
- The app starts on Windows: the Linux-only network inspection and the
  restart after a language change no longer assume Linux.

## [0.11.0]

### Added
- German translation of the whole interface: menus, buttons, dialogs,
  call states and Qt's standard texts. Choose it under Settings ->
  Language (English stays the default); the app offers to restart to
  apply it. Not available during a call.
- Selecting a call log entry opens an action bar below it: Redial or
  Call back, Edit (puts the number on the dialpad to change before
  calling) and Save to contacts (hidden for numbers already saved).
- The Settings password field shows the saved password's status instead
  of looking empty: "Password tested and working" (green) once the
  FRITZ!Box accepted it, "Saved password was rejected" (red), "Password
  saved (not tested yet)" or "No password saved". The field is cleared
  after saving, so the password never stays on screen.

### Fixed
- Call log rows no longer draw dark boxes behind their texts.

## [0.10.0]

### Added
- Settings shows which IP address call audio uses and whether it's the
  local network or a VPN (e.g. "192.168.178.26 - Local network
  (enp34s0)"); a VPN address is highlighted with a warning tooltip.

## [0.9.1]

### Fixed
- You heard nothing on calls - no ringing, no
  voicemail greeting, no caller - whenever a VPN was the default route.
  PJSIP advertised the VPN address for audio, so the FRITZ!Box sent it
  there. Audio is now bound to the local address that reaches the
  FRITZ!Box.

## [0.9.0]

### Added
- Settings shows a live mic level bar while the page is open, so you
  can see the chosen microphone picks you up.
- "Test mic & speaker" in Settings records 3 seconds and plays them
  back on the chosen speaker - an echo test without placing a call.
  It's unavailable during calls. If the recording is silent, it says
  "Recorded only silence - is the mic muted?" instead of playing it.
- Outgoing calls play a ringback tone (425 Hz, 1 s on / 4 s off) while
  the call is being set up, so it's audible that the app is dialing.
  It stops when the call is answered or ends, or when the network
  sends its own audio (ringing or an announcement).

## [0.8.0]

### Added
- A warning window appears when the FRITZ!Box rejects the SIP login
  (e.g. "maximum number of stale retries exceeded" or 401/403/407),
  showing the error and offering to open Settings.
- Saving account settings now tests them: a confirmation appears once
  the FRITZ!Box accepts the registration, or an error if it fails or
  doesn't answer within 20 seconds.

### Fixed
- Saving changed account settings never re-registered: replacing the
  old SIP account crashed (pjsua2 accounts have no delete()), so new
  credentials were silently ignored until restart.
- Google contacts sync could crash the app intermittently once the sync
  finished: its worker object was freed twice, from two threads.
- The window now identifies itself as "voice2fritz" to the desktop, so
  the taskbar no longer groups it with other Python apps.
- A saved host that can't form a valid SIP address (e.g. empty or
  containing spaces) crashed the app at startup; it now opens the
  registration error window instead.

## [0.7.0]

### Added
- Right-clicking a call log entry offers Redial (outgoing calls) or
  Call back (incoming/missed calls), which dials the number right away.
- The same menu offers "Save to contacts…" for numbers not yet in the
  phonebook; it asks for a name and saves the number.

### Changed
- Mic and Speaker dropdowns list PipeWire/PulseAudio devices by their
  readable names (e.g. "Arctis Nova 7 Chat") plus a "System default"
  entry, instead of cryptic ALSA names like `hdmi:CARD=HDMI,DEV=1`.
  Previously saved device choices don't carry over; pick the devices
  again once in Settings.

## [0.6.0]

### Added
- Sidebar navigation: Contacts, Call Log, and Settings are now pages
  behind a persistent left icon rail instead of two fixed docks plus a
  modal Settings dialog. Call Details and the Hangup/Mute controls move
  into a call bar that appears only during a call and stays reachable
  from any page.
- Double-clicking a phonebook entry dials it and switches to the
  Dialpad page.
- The number field shows "number (Name)" whenever the number matches a
  contact, live as you type or dial - not only when dialing came from
  Contacts.
- The CALL button turns into a red HANGUP button, same position, for
  the duration of a call.

### Changed
- Dialpad keys restyled as rounded-square phone keys with the T9
  letters painted inside each key, scale with the window, and flash an
  accent colour only on the key being pressed during a call (previously
  a static border sat on all twelve keys for the whole call).

### Removed
- ContactsDialog: Contacts opening in a second, modal place on top of
  the already-docked ContactsPanel no longer makes sense once Contacts
  is a page of its own.

### Fixed
- Settings no longer overwrites the stored password when the password
  field is left empty on save.
- Placing a call with an empty or whitespace-only number is now a
  no-op instead of reaching the SIP engine.
- Google contacts sync runs off the UI thread, so it no longer freezes
  the window while it's in progress.
- Hangup now sends a normal BYE (200 OK) instead of a decline response.
- Re-registering deletes the previous SIP account first, instead of
  leaking it.
- Malformed entries in the contacts/call-log JSON files are skipped
  instead of crashing the loader.
- The ringtone player is stopped before a new one starts, instead of
  potentially overlapping.

## [0.5.1]

### Fixed
- The app was quitting outright when the incoming-call popup closed
  (e.g. after declining) while the main window was minimized to the
  tray — Qt's default "quit on last window closed" fired because no
  window was visible at that moment.

## [0.5.0]

### Added
- Closing the main window now asks Quit / Minimize to Tray / Cancel,
  instead of quitting outright.
- System tray icon with a Show/Quit menu, so voice2fritz can keep
  running (and receiving calls) in the background.
- Answering an incoming call while minimized to the tray brings the
  window back automatically; declining leaves it minimized.

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
