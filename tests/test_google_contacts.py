from voice2fritz.contacts import Contact, load_contacts, save_contacts
from voice2fritz.google_contacts import _fetch_google_contacts, _sync_from_grouped


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
            {"names": [{"displayName": "Anna Schmidt"}], "phoneNumbers": [{"value": "+4917612345678"}]},
        ],
        "nextPageToken": "tok1",
    }
    page1 = {
        "connections": [
            {"names": [{"displayName": "Anna Schmidt"}], "phoneNumbers": [{"value": "+4917698765432"}]},
            {"names": [{"displayName": "Ben Weber"}], "phoneNumbers": [{"value": "+4930123456"}]},
        ],
    }
    service = _FakeService({None: page0, "tok1": page1})

    result = _fetch_google_contacts(service)

    assert result == {
        "Anna Schmidt": ["+4917612345678", "+4917698765432"],
        "Ben Weber": ["+4930123456"],
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


def test_sync_from_grouped_adds_and_counts_changes(tmp_path):
    path = tmp_path / "contacts.json"
    grouped = {"Anna Schmidt": ["+4917612345678"], "Ben Weber": ["+4930123456"]}

    count = _sync_from_grouped(grouped, overwrite_local=True, path=path)

    assert count == 2
    assert load_contacts(path) == [
        Contact(name="Anna Schmidt", number="+4917612345678", source="google"),
        Contact(name="Ben Weber", number="+4930123456", source="google"),
    ]


def test_sync_from_grouped_skips_local_wins_names(tmp_path):
    path = tmp_path / "contacts.json"
    save_contacts([Contact(name="Anna Schmidt", number="+4917600000000", source="local")], path)
    grouped = {"Anna Schmidt": ["+4917612345678"]}

    count = _sync_from_grouped(grouped, overwrite_local=False, path=path)

    assert count == 0
    assert load_contacts(path) == [Contact(name="Anna Schmidt", number="+4917600000000", source="local")]
