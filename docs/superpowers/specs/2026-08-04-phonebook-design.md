# voice2fritz FritzBox Phonebook — Design Spec

Date: 2026-08-04

## Purpose

Let the user browse their FritzBox's phonebook and click a contact to
fill the dial field, instead of typing/remembering numbers by hand.
Read-only, browse-and-dial only — no editing, no caller-ID lookup on
incoming calls, no contact syncing. Deferred from v1 per the design
spec's v2 candidate list; this is that feature.

Out of scope for this pass: caller-ID name lookup on incoming calls,
editing/adding contacts, syncing/caching the phonebook to disk.

## Architecture

FritzBox exposes its phonebook via TR-064 (a SOAP-based home-network API
distinct from SIP), authenticated with the FritzBox's own web-login
username/password — separate from the SIP account credentials already
stored. voice2fritz talks to it with Python's stdlib `urllib` (no new
dependency), following the same "no new deps unless truly needed"
approach used for DTMF.

Flow to fetch contacts: SOAP `GetPhonebookList` action (discovers
phonebook IDs, normally just `[0]`) → SOAP `GetPhonebook` action for ID 0
(returns a `NewPhonebookURL`) → plain HTTP GET on that URL (also
Digest-authenticated) → parse the returned phonebook XML.

## Components

- `src/voice2fritz/tr064.py` (new):
  - `@dataclass Contact(name: str, numbers: list[str])`
  - `parse_phonebook_xml(xml_text: str) -> list[Contact]` — pure
    function, no network. This is the testable seam (analogous to
    `audio.py`'s `list_audio_devices`): parses `<phonebook><contact>`
    entries (`<person><realName>`, `<telephony><number>` — possibly
    multiple numbers per contact) via `xml.etree.ElementTree`.
  - `get_phonebook(host: str, username: str, password: str) -> list[Contact]`
    — the impure networking function: SOAP calls + HTTP GET (via
    `urllib.request` with `HTTPDigestAuthHandler`) +
    `parse_phonebook_xml()`. Raises on network/auth failure — caller
    handles the exception, this function does not swallow errors.
- `src/voice2fritz/config.py` (modified): add
  `load_fritzbox_username() -> str | None` / `save_fritzbox_username(username)`
  (the FritzBox host itself is the existing SIP `AccountConfig.host`,
  reused rather than duplicated — only the username differs; stored
  under a new `fritzbox_username` key, merge-safe like the existing
  device-selection keys) and `get_fritzbox_password(username)` /
  `set_fritzbox_password(username, password)`, storing under a distinct
  keyring key (e.g. `f"fritzbox:{username}"`) so it can never collide
  with a SIP password stored under the same username.
- `src/voice2fritz/gui/settings_dialog.py` (modified): add
  `fritzbox_username_edit` / `fritzbox_password_edit` fields, saved via
  the new config functions on the same Save click as the SIP fields.
- `src/voice2fritz/gui/contacts_dialog.py` (new): `QDialog` with a
  `QListWidget`. On open, calls `tr064.get_phonebook(...)` (via the
  saved FritzBox host/username/password) and populates the list with
  `"{name} — {number}"` per contact (one row per number, since a
  contact can have multiple numbers). Double-clicking a row (or a
  Select button) emits `contactSelected(number: str)` and calls
  `accept()`. If fetching fails, shows a `QMessageBox` with the error
  and leaves the list empty rather than crashing.
- `src/voice2fritz/gui/main_window.py` (modified): new
  `contacts_button` ("Contacts") next to `settings_button`. Opens
  `ContactsDialog`; its `contactSelected` signal sets `number_edit`'s
  text to the chosen number.

## Data Flow

1. User clicks Contacts → `ContactsDialog` opens → calls
   `tr064.get_phonebook(host, fritzbox_username, fritzbox_password)`.
2. Success: list populated, one row per contact/number.
3. Failure (network/auth error): caught in the dialog, shown via
   `QMessageBox`, list stays empty; user can close the dialog and retry
   later (no automatic retry).
4. User double-clicks a contact row → `contactSelected` emits the number
   → `main_window` sets `number_edit.text()` → dialog closes → user
   clicks Call as normal (unchanged existing flow).

## Error Handling

- Missing FritzBox credentials (never configured): Contacts button still
  opens the dialog, which immediately shows "FritzBox credentials not
  configured — set them in Settings" instead of attempting a fetch.
- Network/auth failure during fetch: caught, shown via `QMessageBox`,
  dialog remains open with an empty list (matches the "no crash, no
  automatic retry" pattern used elsewhere in the app, e.g. registration
  failure).

## Testing

- `tr064.parse_phonebook_xml`: unit-testable with a canned FritzBox-style
  XML string (no network) — verifies name/number extraction, multiple
  numbers per contact, and malformed/empty input handling.
- `tr064.get_phonebook`: no automated test (real network call to a real
  FritzBox) — verified manually against the user's FritzBox 7590,
  consistent with how `sip_engine.py`'s pjsua2 calls are verified.
- `config.py`'s new FritzBox credential functions: unit-tested the same
  way as the existing SIP credential functions (keyring mocked,
  `tmp_path` for the config file).
- `ContactsDialog`: unit-tested with `pytest-qt`, injecting a fake
  `get_phonebook`-like callable (monkeypatched) so no real network is
  needed — verifies the list populates correctly, double-click emits
  `contactSelected` with the right number, and a fetch failure shows an
  error without crashing.
