# voice2fritz Google Contacts Sync — Design Spec

Date: 2026-08-04

## Purpose

Let the user pull contacts from their Android phone's Google account into
voice2fritz's local phonebook, instead of typing them in by hand. One-way
sync only (Google → local); contacts added locally are never pushed back
to Google and are never overwritten by a sync.

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
- **Merging:** for each Google contact with at least one phone number, use
  its first name entry and first phone number (multiple numbers per
  Google contact become multiple local `Contact` entries, matching how
  the earlier TR-064 design handled multi-number contacts). Before
  adding, check the number against every existing entry in
  `contacts.json` (via `contacts.load_contacts()`) — skip if the number
  is already present. This makes sync idempotent: running it repeatedly
  never creates duplicates, and never touches/removes existing entries.

## Components

- `src/voice2fritz/google_contacts.py` (new):
  - `TOKEN_PATH = Path.home() / ".config" / "voice2fritz" / "google_token.json"`
  - `CLIENT_SECRET_PATH = Path.home() / ".config" / "voice2fritz" / "google_client_secret.json"`
  - `SCOPES = ["https://www.googleapis.com/auth/contacts.readonly"]`
  - `_get_credentials() -> Credentials` — loads/refreshes/creates the
    OAuth token as described above. Raises `FileNotFoundError` with a
    clear message if `client_secret.json` is missing (caught by the
    caller, shown via `QMessageBox`, same pattern as everywhere else).
  - `_fetch_google_contacts(creds) -> list[tuple[str, str]]` — returns
    `(name, number)` pairs, one per phone number, paginating through
    `people.connections.list`.
  - `sync_google_contacts() -> int` — orchestrates the above, merges
    against `contacts.load_contacts()`/`contacts.add_contact()`
    (existing module, unchanged), returns the count of newly added
    contacts.
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
2. `sync_google_contacts()` runs: get/refresh credentials → fetch all
   Google contacts with phone numbers → for each, skip if the number
   already exists locally, otherwise `contacts.add_contact(name, number)`.
3. Dialog reloads its list from `contacts.load_contacts()` (existing
   `_reload_list()` method, unchanged) — newly synced contacts appear
   alongside manually-added ones, indistinguishable in storage (both are
   just `Contact(name, number)` entries in the same file).
4. First run only: browser opens for Google consent before step 2
   proceeds; this is synchronous/blocking from the dialog's perspective
   (acceptable — it's a deliberate, infrequent user action, not something
   that needs to be responsive/async for v1).

## Error Handling

- Missing `google_client_secret.json`: caught, `QMessageBox.warning` with
  a message pointing at the README's setup section.
- Auth/consent failure or denial: caught, shown via `QMessageBox`, no
  partial state — either the whole sync completes or nothing is added
  (contacts are only added one at a time as they're confirmed unique, so
  a failure partway through simply means "sync got interrupted, some
  contacts may already be added, safe to just click Sync Google again"
  since dedup makes re-running safe).
- Network failure mid-fetch (pagination): same as above — caught, shown,
  safe to retry.

## Testing

- `_fetch_google_contacts`'s pagination/parsing logic and the merge/dedup
  logic in `sync_google_contacts` are the testable seams: both can be
  unit-tested by injecting a fake People API client object (a stub with a
  `.connections().list(...).execute()` chain returning canned
  dictionaries) and a temp `contacts.json` path — no real OAuth or
  network needed, following the same pure/impure split used throughout
  the project (`audio.py`, `tr064.py`).
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
