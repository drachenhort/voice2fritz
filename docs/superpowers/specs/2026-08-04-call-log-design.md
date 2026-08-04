# voice2fritz Call Log — Design Spec

Date: 2026-08-04

## Purpose

Track outgoing, incoming, and missed calls in a local log, viewable in a
"Log" dialog with a phone-app-style list (icon + name/number + time),
matching the visual style of the "Fritz!Phone Linux" mockup the user
shared earlier. Double-clicking an entry fills the dial field for redial,
same interaction as the Contacts dialog.

Deferred from v1's stated out-of-scope list ("call history"); this is
that feature.

## Data Model

New module `src/voice2fritz/call_log.py`, following the same shape as
`contacts.py`:

```python
@dataclass
class CallLogEntry:
    number: str
    name: str
    direction: str  # "outgoing" | "incoming" | "missed"
    timestamp: str  # ISO 8601, e.g. datetime.now().isoformat()
    duration_seconds: int
```

Stored as a JSON list at `~/.config/voice2fritz/call_log.json`, same
`_read_raw`/`_write_raw`-less simple load/save pattern as `contacts.py`
(this file has no merge-safety concern since nothing else shares it).

- `load_call_log(path=DEFAULT_CALL_LOG_PATH) -> list[CallLogEntry]`
- `append_call_log_entry(entry: CallLogEntry, path=...) -> None`
- `clear_call_log(path=...) -> None`

`missed` covers both "incoming call rang out unanswered" and "user
explicitly rejected it" — both are "you didn't talk to them," which is
what a call log's missed/red-icon convention communicates. No separate
"declined" category for v1.

## Duration Semantics (deliberate simplification)

Duration is measured from when the call is initiated (dial button
clicked, or incoming call received) to when it ends — this includes
ring/setup time, not just "talk time" from the moment it's answered.
Getting exact "answered" timing would require pattern-matching pjsip's
internal call-state strings (`"CALLING"`, `"EARLY"`, `"CONFIRMED"`,
etc.) which `callStateChanged` currently passes through as opaque text —
fragile coupling to PJSIP internals for a precision this app doesn't
need. Missed calls always log `duration_seconds=0`.

## Components

- `src/voice2fritz/call_log.py` (new): data model + load/append/clear,
  as above.
- `src/voice2fritz/sip_engine.py` (modified): new
  `get_remote_number(call: SipCall) -> str` — extracts the caller's
  number from pjsua2's `CallInfo.remoteUri` (format like
  `"Display Name" <sip:01761234567@fritz.box>`, or without a display
  name). Parses the substring between `sip:` and `@`. This is needed
  because nothing currently exposes the caller's number for an incoming
  call — `_on_incoming_call` only receives the `SipCall` object itself.
- `src/voice2fritz/gui/main_window.py` (modified): tracks in-progress
  call bookkeeping across existing handlers:
  - `_on_call_clicked` (outgoing): records
    `self._call_direction = "outgoing"`,
    `self._call_number = self.number_edit.text()`,
    `self._call_start_time = datetime.now()`.
  - `_on_incoming_call`: records `self._call_direction = "incoming"`,
    `self._call_number = self.sip_engine.get_remote_number(call)`,
    `self._call_start_time = datetime.now()` — set regardless of
    accept/reject, so a rejected call still gets a timestamp. On the
    reject branch (`QMessageBox.StandardButton.No`), overwrites
    `self._call_direction = "missed"` before calling `_on_call_ended()`.
  - `_on_call_ended`: if `self._call_direction is not None`, computes
    `duration_seconds` (0 if `direction == "missed"`, else
    `(datetime.now() - self._call_start_time).total_seconds()`), looks
    up a matching contact name via `contacts.load_contacts()` (first
    contact whose `number == self._call_number`, blank if none), calls
    `call_log.append_call_log_entry(...)`, then resets
    `self._call_direction`/`_call_number`/`_call_start_time` to `None`.
  - New `log_button` ("Log") next to `contacts_button`, opens
    `CallLogDialog`, connects its `callSelected` signal to
    `self.number_edit.setText`.
- `src/voice2fritz/gui/call_log_dialog.py` (new): `QDialog` with a
  `QListWidget` where each row is a custom widget (`QWidget` with a
  `QHBoxLayout`: direction icon label on the left, a vertical stack of
  name + subtext (`number · m:ss`, or just `number` for missed) in the
  middle, timestamp label on the right) set via
  `QListWidget.setItemWidget`. Icons: `↗` (green) for outgoing, `↙`
  (white/default text color) for incoming, `↙` (red) for missed —
  plain Unicode characters, same convention as the rest of the app, no
  new asset files. Entries sorted newest-first. Double-click emits
  `callSelected(number: str)` and closes the dialog (mirrors
  `ContactsDialog`'s `_on_item_activated`/`_select_row` pattern, adapted
  for a list of custom-widget rows instead of table cells — needs its
  own row→`CallLogEntry` index tracking since `QListWidget` items don't
  carry structured data by default; store the entry in the item via
  `QListWidgetItem.setData(Qt.ItemDataRole.UserRole, entry)`). A "Clear"
  button calls `call_log.clear_call_log()` and reloads (empty list).

## Data Flow

1. User dials or receives a call → `MainWindow` records direction/number/
   start-time as described above.
2. Call ends (hangup, remote BYE, or reject) → `_on_call_ended` computes
   duration, looks up the contact name, appends a `CallLogEntry`.
3. User opens Log → `CallLogDialog` loads all entries via
   `call_log.load_call_log()`, sorted newest-first, renders each as a
   custom row widget.
4. Double-click a row → `callSelected` emits the entry's number →
   `MainWindow` fills `number_edit` → dialog closes → user clicks Call
   as normal (existing, unchanged flow).
5. Clear button → `call_log.clear_call_log()` → list reloads empty.

## Error Handling

No network/external-service calls are involved (purely local file I/O
and pjsua2 call-info parsing already exercised elsewhere), so error
handling mirrors `contacts.py`'s: malformed/missing `call_log.json`
returns an empty list rather than crashing (same `json.JSONDecodeError`
→ `[]` pattern as `contacts.load_contacts`). `get_remote_number` should
handle a `remoteUri` that doesn't match the expected `sip:...@...`
shape gracefully (return an empty string rather than raising) — this
keeps `_on_incoming_call` from crashing the call-accept flow if pjsua2
ever hands back an unexpected URI format.

## Testing

- `call_log.py`: unit-tested identically to `contacts.py`'s pattern —
  round-trip save/load, missing-file, malformed-JSON, append, clear —
  using `tmp_path`.
- `sip_engine.get_remote_number`: pure string-parsing logic, but it
  takes a `SipCall`/`CallInfo`-shaped object as input — testable by
  passing a minimal fake object exposing `.getInfo().remoteUri` as a
  plain string, no real pjsua2 needed (same testable-seam approach as
  `audio.py`'s `list_audio_devices`). Covers: display-name-prefixed URI,
  bare URI, and a malformed/unexpected string (returns `""`).
- `MainWindow`'s call-log bookkeeping: unit-tested with the existing
  `FakeSipEngine` pattern — verify that completing an outgoing call
  appends an entry with `direction="outgoing"` and the dialed number;
  that accepting an incoming call appends `direction="incoming"` with
  the number from `get_remote_number`; that rejecting one appends
  `direction="missed"` with `duration_seconds=0`. Monkeypatch
  `call_log.append_call_log_entry` to capture calls rather than hitting
  the real file.
- `CallLogDialog`: unit-tested with `pytest-qt`, monkeypatching
  `call_log.load_call_log` to return canned entries — verifies row
  count/content, double-click emits the right number, and Clear calls
  `call_log.clear_call_log()` and reloads to an empty list.
