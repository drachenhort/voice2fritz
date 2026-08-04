from google.auth.exceptions import RefreshError

from voice2fritz.contacts import Contact, load_contacts, save_contacts
from voice2fritz.google_contacts import _fetch_google_contacts, _get_credentials, _sync_from_grouped


class _FakeRequest:
    def __init__(self, page):
        self._page = page

    def execute(self):
        return self._page


class _FakeService:
    def __init__(self, pages_by_token):
        self._pages_by_token = pages_by_token

    def people(self):
        return self

    def connections(self):
        return self

    def list(self, resourceName, personFields, pageSize, pageToken=None):
        return _FakeRequest(self._pages_by_token[pageToken])


def test_fetch_google_contacts_paginates_and_groups_by_name():
    page0 = {
        "connections": [
            {"names": [{"displayName": "Anna Schmidt"}], "phoneNumbers": [{"value": "+4917612345678", "type": "mobile"}]},
        ],
        "nextPageToken": "tok1",
    }
    page1 = {
        "connections": [
            {"names": [{"displayName": "Anna Schmidt"}], "phoneNumbers": [{"value": "+4917698765432", "type": "home"}]},
            {"names": [{"displayName": "Ben Weber"}], "phoneNumbers": [{"value": "+4930123456", "type": "work"}]},
        ],
    }
    service = _FakeService({None: page0, "tok1": page1})

    result = _fetch_google_contacts(service)

    assert result == {
        "Anna Schmidt": [("+4917612345678", "mobile"), ("+4917698765432", "home")],
        "Ben Weber": [("+4930123456", "work")],
    }


def test_fetch_google_contacts_skips_entries_without_name_or_number():
    page0 = {
        "connections": [
            {"names": [], "phoneNumbers": [{"value": "+4917612345678"}]},
            {"names": [{"displayName": "No Number"}], "phoneNumbers": []},
        ],
    }
    service = _FakeService({None: page0})

    assert _fetch_google_contacts(service) == {}


def test_fetch_google_contacts_dedups_duplicate_numbers():
    page0 = {
        "connections": [
            {
                "names": [{"displayName": "Anna Schmidt"}],
                "phoneNumbers": [
                    {"value": "+4917612345678", "type": "mobile"},
                    {"value": "+4917612345678", "type": "main"},
                ],
            },
        ],
    }
    service = _FakeService({None: page0})

    assert _fetch_google_contacts(service) == {"Anna Schmidt": [("+4917612345678", "mobile")]}


def test_fetch_google_contacts_dedups_across_multiple_person_entries_for_same_name():
    page0 = {
        "connections": [
            {"names": [{"displayName": "Anna Schmidt"}], "phoneNumbers": [{"value": "+4917612345678", "type": "mobile"}]},
            {"names": [{"displayName": "Anna Schmidt"}], "phoneNumbers": [{"value": "+4917612345678", "type": "mobile"}]},
        ],
    }
    service = _FakeService({None: page0})

    assert _fetch_google_contacts(service) == {"Anna Schmidt": [("+4917612345678", "mobile")]}


def test_fetch_google_contacts_prefers_canonical_form():
    page0 = {
        "connections": [
            {
                "names": [{"displayName": "Anna Schmidt"}],
                "phoneNumbers": [
                    {"value": "0176 12345678", "canonicalForm": "+4917612345678", "type": "mobile"},
                ],
            },
        ],
    }
    service = _FakeService({None: page0})

    assert _fetch_google_contacts(service) == {"Anna Schmidt": [("+4917612345678", "mobile")]}


def test_fetch_google_contacts_defaults_missing_type_to_empty_string():
    page0 = {
        "connections": [
            {"names": [{"displayName": "Anna Schmidt"}], "phoneNumbers": [{"value": "+4917612345678"}]},
        ],
    }
    service = _FakeService({None: page0})

    assert _fetch_google_contacts(service) == {"Anna Schmidt": [("+4917612345678", "")]}


def test_sync_from_grouped_adds_and_counts_changes(tmp_path):
    path = tmp_path / "contacts.json"
    grouped = {"Anna Schmidt": [("+4917612345678", "mobile")], "Ben Weber": [("+4930123456", "work")]}

    count = _sync_from_grouped(grouped, overwrite_local=True, path=path)

    assert count == 2
    assert load_contacts(path) == [
        Contact(name="Anna Schmidt", number="+4917612345678", source="google", number_type="mobile"),
        Contact(name="Ben Weber", number="+4930123456", source="google", number_type="work"),
    ]


def test_sync_from_grouped_skips_local_wins_names(tmp_path):
    path = tmp_path / "contacts.json"
    save_contacts([Contact(name="Anna Schmidt", number="+4917600000000", source="local")], path)
    grouped = {"Anna Schmidt": [("+4917612345678", "mobile")]}

    count = _sync_from_grouped(grouped, overwrite_local=False, path=path)

    assert count == 0
    assert load_contacts(path) == [Contact(name="Anna Schmidt", number="+4917600000000", source="local")]


class _FakeExpiredCreds:
    """Fake credentials whose refresh() simulates a revoked/expired refresh token."""

    expired = True
    refresh_token = "fake-refresh-token"
    valid = False

    def refresh(self, request):
        raise RefreshError("invalid_grant")


class _FakeFreshCreds:
    valid = True

    def to_json(self):
        return "{}"


def test_get_credentials_recovers_from_refresh_error(monkeypatch, tmp_path):
    token_path = tmp_path / "google_token.json"
    token_path.write_text("{}")
    client_secret_path = tmp_path / "google_client_secret.json"
    client_secret_path.write_text("{}")

    import voice2fritz.google_contacts as google_contacts

    monkeypatch.setattr(google_contacts, "TOKEN_PATH", token_path)
    monkeypatch.setattr(google_contacts, "CLIENT_SECRET_PATH", client_secret_path)
    monkeypatch.setattr(
        google_contacts.Credentials,
        "from_authorized_user_file",
        classmethod(lambda cls, path, scopes: _FakeExpiredCreds()),
    )

    fresh_creds = _FakeFreshCreds()

    class _FakeFlow:
        def run_local_server(self, port):
            return fresh_creds

    monkeypatch.setattr(
        google_contacts.InstalledAppFlow,
        "from_client_secrets_file",
        classmethod(lambda cls, path, scopes: _FakeFlow()),
    )

    creds = _get_credentials()

    assert creds is fresh_creds
