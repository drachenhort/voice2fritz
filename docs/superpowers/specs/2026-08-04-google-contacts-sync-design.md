# voice2fritz Google Contacts Sync — Design Spec

Date: 2026-08-04

## Purpose

Let the user pull contacts from their Android phone's Google account into
voice2fritz's local phonebook, instead of typing them in by hand. One-way
sync only (Google → local); contacts added locally are never pushed back
to Google. Google-sourced contacts are updated in place when their
number(s) change on the Google side, tracked separately from
manually-added contacts via a `source` marker.

**Name-conflict priority is a Settings toggle.** When a synced Google
contact and a manually-added local contact share the same name, one of
two things happens, controlled by a new setting:
- **Google wins (default):** the local entry is replaced by the synced
  one. This can overwrite/delete a manually-added contact's number if it
  shares a name with a Google contact — a real, intentional data-loss
  tradeoff the user explicitly chose as the default.
- **Local wins (opt-out):** sync skips creating/updating anything for
  that name; the manually-added entry is left exactly as-is.

Deferred from the local-phonebook work (see
`2026-08-04-phonebook-design.md`, which itself replaced an earlier
FritzBox-TR-064-based attempt that didn't pan out).

Out of scope: two-way sync, editing/deleting Google-side contacts from
voice2fritz, syncing anything other than name + phone numbers (no photos,
emails, addresses), automatic/background sync (this is a manual,
on-demand action).

## Why New Dependencies

Every prior voice2fritz feature (TR-064, DTMF, device audio) used stdlib
only. Google's People API requires real OAuth 2.0 user consent — contacts
are private data, not accessible via a simple API key. Hand-rolling
OAuth 2.0 (authorization code flow, PKCE, token refresh, secure token
storage) correctly and safely is a substantial, security-sensitive
undertaking on its own — not a small addition like TR-064's HTTP Digest
auth was. Using Google's own well-tested libraries
(`google-auth`, `google-auth-oauthlib`, `google-api-python-client`) is the
right tradeoff here, even though it breaks the project's "no new
dependencies" streak.

## Architecture

- **Google Cloud setup (one-time, by the user, not part of the app):**
  Create a Google Cloud project, enable the People API, create an OAuth
  2.0 Client ID of type "Desktop app", download its `client_secret.json`.
  This file is placed at `~/.config/voice2fritz/google_client_secret.json`
  — never committed to the repo (voice2fritz's GitHub repo is public).
- **First sync (consent flow):** `google_auth_oauthlib.flow.InstalledAppFlow`
  reads `google_client_secret.json`, opens the user's browser for Google's
  consent screen, and runs a short-lived local HTTP server
  (`flow.run_local_server()`) to receive the OAuth redirect. On success, the
  resulting credentials (including a refresh token) are saved to
  `~/.config/voice2fritz/google_token.json`.
- **Later syncs:** the saved token is loaded and silently refreshed as
  needed (`google.auth.transport.requests.Request()` +
  `credentials.refresh()`) — no repeated browser popups unless the user
  revokes access on Google's side.
- **Fetching contacts:** `googleapiclient.discovery.build("people", "v1", credentials=creds)`,
  then `people.connections.list(resourceName="people/me", personFields="names,phoneNumbers")`,
  paginated via `pageToken` until exhausted.
- **Data model change:** `contacts.Contact` gains a `source: str = "local"`
  field (`"local"` for manually-added entries, `"google"` for
  sync-created ones). Existing `contacts.json` files have no `source`
  key — `load_contacts()` defaults missing keys to `"local"`, so every
  contact added before this feature existed is (correctly) treated as
  manually-added and never touched by sync logic.
- **Priority setting:** `config.py` gains
  `load_google_sync_overwrites_local() -> bool` (default `True`, matching
  the user's chosen default) and
  `save_google_sync_overwrites_local(value: bool)`, stored in
  `config.json` alongside the existing settings. `SettingsDialog` gets a
  checkbox, "Google sync overwrites local contacts with the same name",
  checked by default, saved on the same Save click as everything else.
- **Merging, grouped by name:** Google contacts are grouped by name; each
  group's number list becomes that name's current Google-sourced numbers
  (multiple numbers per Google contact become multiple local `Contact`
  entries, one per number, matching how the earlier TR-064 design handled
  multi-number contacts). For each name, read the priority setting, then:
  - **If a `source == "local"` entry with this name exists:**
    - Priority = local wins → skip this name entirely, nothing changes.
    - Priority = Google wins → delete every existing entry (both
      `"local"` and `"google"` sourced) with this name, then add fresh
      `source == "google"` entries for every current number.
  - **If no `source == "local"` entry with this name exists:** behave the
    same regardless of the priority setting (there's no conflict to
    resolve) — if existing `source == "google"` entries for this name
    have a different number set than the fresh fetch, replace them;
    if there are none yet, add them; if the sets already match, do
    nothing.
  - This makes sync idempotent for the common case (no duplicates from
    repeated runs once no local/google mismatch remains for a name), and
    correctly reflects number changes made on the phone.

## Components

- `src/voice2fritz/contacts.py` (modified):
  - `Contact` gains `source: str = "local"`.
  - `load_contacts()` reads `item.get("source", "local")` so pre-existing
    entries without the key default correctly.
  - New: `sync_contact_for_name(name: str, numbers: list[str], overwrite_local: bool, path=DEFAULT_CONTACTS_PATH) -> bool`
    — implements the priority logic described above in one place. Returns
    `True` if it made a change (added/replaced anything), `False` if it
    skipped (local-wins case) or the state already matched (no-op case)
    — used by `sync_google_contacts()` to count real changes. This is the
    one place that ever deletes/replaces existing contacts;
    `add_contact()` (existing, unchanged) is still used for plain manual
    additions from the dialog's Add button.
- `src/voice2fritz/config.py` (modified): add
  `load_google_sync_overwrites_local(path=DEFAULT_CONFIG_PATH) -> bool`
  (default `True` when the key is absent) and
  `save_google_sync_overwrites_local(value: bool, path=DEFAULT_CONFIG_PATH) -> None`,
  merge-safe like the existing device-selection/FritzBox-username keys.
- `src/voice2fritz/gui/settings_dialog.py` (modified): new
  `google_priority_checkbox: QCheckBox` ("Google sync overwrites local
  contacts with the same name"), defaulted to checked, saved via
  `config.save_google_sync_overwrites_local(...)` on the same Save click.
- `src/voice2fritz/google_contacts.py` (new):
  - `TOKEN_PATH = Path.home() / ".config" / "voice2fritz" / "google_token.json"`
  - `CLIENT_SECRET_PATH = Path.home() / ".config" / "voice2fritz" / "google_client_secret.json"`
  - `SCOPES = ["https://www.googleapis.com/auth/contacts.readonly"]`
  - `_get_credentials() -> Credentials` — loads/refreshes/creates the
    OAuth token as described above. Raises `FileNotFoundError` with a
    clear message if `client_secret.json` is missing (caught by the
    caller, shown via `QMessageBox`, same pattern as everywhere else).
  - `_fetch_google_contacts(creds) -> dict[str, list[str]]` — returns
    `{name: [number, ...]}`, grouping every phone number under its
    contact's name, paginating through `people.connections.list`.
  - `sync_google_contacts() -> int` — orchestrates the above: reads the
    priority setting via `config.load_google_sync_overwrites_local()`,
    fetches the grouped Google contacts, and calls
    `contacts.sync_contact_for_name(name, numbers, overwrite_local)` for
    each name, counting how many calls returned `True`. Returns that
    count — matches what the UI reports in one line, see below.
- `src/voice2fritz/gui/contacts_dialog.py` (modified): new
  `sync_button` ("Sync Google"). On click: calls
  `google_contacts.sync_google_contacts()` inside a try/except; on
  success, reloads the list and could optionally show a brief
  "N contacts added" status (kept simple: reuse the existing
  `QMessageBox.information` pattern, one line); on failure (missing
  client secret, auth error, network error), `QMessageBox.warning` with
  the error message — same as the dialog's existing fetch-failure
  handling.
- `pyproject.toml` (modified): add `google-auth`, `google-auth-oauthlib`,
  `google-api-python-client` to `dependencies`.
- `README.md` / `README.de.md` (modified): short walkthrough for creating
  the Google Cloud project, enabling the People API, creating a Desktop
  app OAuth client, and downloading `client_secret.json` to the right
  path — mirroring the existing pjsua2 build walkthrough's level of
  detail.

## Data Flow

1. User opens Contacts, clicks "Sync Google".
2. `sync_google_contacts()` runs: get/refresh credentials → read the
   priority setting → fetch all Google contacts grouped by name → call
   `contacts.sync_contact_for_name(name, numbers, overwrite_local)` per
   name, which adds, replaces, or skips per the priority rules above.
3. Dialog reloads its list from `contacts.load_contacts()` (existing
   `_reload_list()` method, unchanged) — synced contacts appear alongside
   manually-added ones, distinguished internally by `source` but not
   visually separated in the list (same display format for both).
4. First run only: browser opens for Google consent before step 2
   proceeds; this is synchronous/blocking from the dialog's perspective
   (acceptable — it's a deliberate, infrequent user action, not something
   that needs to be responsive/async for v1).

## Error Handling

- Missing `google_client_secret.json`: caught, `QMessageBox.warning` with
  a message pointing at the README's setup section.
- Auth/consent failure or denial: caught, shown via `QMessageBox`. A
  failure partway through means some names were already
  replaced/added and others weren't yet — safe to just click Sync Google
  again, since re-running only touches names whose Google-side numbers
  still differ from local state; already-synced names are left alone.
- Network failure mid-fetch (pagination): same as above — caught, shown,
  safe to retry.

## Testing

- `contacts.sync_contact_for_name`: unit-tested directly (no
  Google/network involvement at all) — covers: replacing an existing
  google-sourced entry's numbers; adding a brand-new name with no prior
  entries; a local-name conflict with `overwrite_local=False` (must leave
  the local entry completely untouched and report `False`); the same
  conflict with `overwrite_local=True` (must delete the local entry and
  replace it with the google-sourced one, reporting `True`); and the
  already-in-sync no-op case (must report `False`, no writes).
- `_fetch_google_contacts`'s pagination/grouping logic and the
  diff-and-replace orchestration in `sync_google_contacts` are the
  testable seams: both can be unit-tested by injecting a fake People API
  client object (a stub with a `.connections().list(...).execute()`
  chain returning canned dictionaries) and a temp `contacts.json` path —
  no real OAuth or network needed, following the same pure/impure split
  used throughout the project (`audio.py`, `tr064.py`).
- `_get_credentials()` (the actual OAuth flow) has no automated test —
  requires real browser interaction and a real Google account — verified
  manually by the user during Task implementation, consistent with how
  `sip_engine.py`'s pjsua2 calls and `tr064.py`'s network calls are
  verified.
- `ContactsDialog`'s new "Sync Google" button: unit-tested with
  `pytest-qt`, monkeypatching `google_contacts.sync_google_contacts` to
  a fake callable — verifies the list reloads after a successful sync
  and that a raised exception shows a warning without crashing, following
  the exact pattern already used for the dialog's other error handling
  tests.
