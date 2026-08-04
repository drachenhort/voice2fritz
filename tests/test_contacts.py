import json

from voice2fritz.contacts import (
    Contact,
    add_contact,
    delete_contact,
    delete_contact_by_value,
    load_contacts,
    save_contacts,
    sync_contact_for_name,
)


def test_save_and_load_contacts_round_trip(tmp_path):
    path = tmp_path / "contacts.json"
    contacts = [Contact(name="Anna Schmidt", number="+4917612345678"), Contact(name="Ben Weber", number="+4930123456")]

    save_contacts(contacts, path)

    assert load_contacts(path) == contacts


def test_load_contacts_missing_file_returns_empty_list(tmp_path):
    path = tmp_path / "does-not-exist.json"
    assert load_contacts(path) == []


def test_load_contacts_malformed_json_returns_empty_list(tmp_path):
    path = tmp_path / "contacts.json"
    path.write_text("{not valid json")
    assert load_contacts(path) == []


def test_add_contact_appends_and_persists(tmp_path):
    path = tmp_path / "contacts.json"
    save_contacts([Contact(name="Anna Schmidt", number="+4917612345678")], path)

    add_contact("Ben Weber", "+4930123456", path=path)

    assert load_contacts(path) == [
        Contact(name="Anna Schmidt", number="+4917612345678"),
        Contact(name="Ben Weber", number="+4930123456"),
    ]


def test_add_contact_creates_parent_dirs(tmp_path):
    path = tmp_path / "nested" / "dir" / "contacts.json"

    add_contact("Anna Schmidt", "+4917612345678", path=path)

    assert path.exists()
    assert load_contacts(path) == [Contact(name="Anna Schmidt", number="+4917612345678")]


def test_add_contact_stores_number_type(tmp_path):
    path = tmp_path / "contacts.json"

    add_contact("Anna Schmidt", "+4917612345678", number_type="mobile", path=path)

    assert load_contacts(path) == [Contact(name="Anna Schmidt", number="+4917612345678", number_type="mobile")]


def test_delete_contact_removes_by_index(tmp_path):
    path = tmp_path / "contacts.json"
    save_contacts(
        [Contact(name="Anna Schmidt", number="+4917612345678"), Contact(name="Ben Weber", number="+4930123456")],
        path,
    )

    delete_contact(0, path)

    assert load_contacts(path) == [Contact(name="Ben Weber", number="+4930123456")]


def test_delete_contact_out_of_range_is_noop(tmp_path):
    path = tmp_path / "contacts.json"
    save_contacts([Contact(name="Anna Schmidt", number="+4917612345678")], path)

    delete_contact(5, path)

    assert load_contacts(path) == [Contact(name="Anna Schmidt", number="+4917612345678")]


def test_delete_contact_by_value_removes_matching_entry(tmp_path):
    path = tmp_path / "contacts.json"
    save_contacts(
        [Contact(name="Anna Schmidt", number="+4917612345678"), Contact(name="Ben Weber", number="+4930123456")],
        path,
    )

    delete_contact_by_value(Contact(name="Anna Schmidt", number="+4917612345678"), path)

    assert load_contacts(path) == [Contact(name="Ben Weber", number="+4930123456")]


def test_delete_contact_by_value_unknown_contact_is_noop(tmp_path):
    path = tmp_path / "contacts.json"
    save_contacts([Contact(name="Anna Schmidt", number="+4917612345678")], path)

    delete_contact_by_value(Contact(name="Nobody", number="+490000000"), path)

    assert load_contacts(path) == [Contact(name="Anna Schmidt", number="+4917612345678")]


def test_load_contacts_defaults_missing_source_to_local(tmp_path):
    path = tmp_path / "contacts.json"
    path.write_text(json.dumps([{"name": "Anna Schmidt", "number": "+4917612345678"}]))

    assert load_contacts(path) == [Contact(name="Anna Schmidt", number="+4917612345678", source="local")]


def test_load_contacts_defaults_missing_number_type_to_empty(tmp_path):
    path = tmp_path / "contacts.json"
    path.write_text(json.dumps([{"name": "Anna Schmidt", "number": "+4917612345678"}]))

    assert load_contacts(path) == [Contact(name="Anna Schmidt", number="+4917612345678", number_type="")]


def test_sync_contact_for_name_adds_new_google_contact(tmp_path):
    path = tmp_path / "contacts.json"

    changed = sync_contact_for_name("Anna Schmidt", [("+4917612345678", "mobile")], overwrite_local=True, path=path)

    assert changed is True
    assert load_contacts(path) == [
        Contact(name="Anna Schmidt", number="+4917612345678", source="google", number_type="mobile")
    ]


def test_sync_contact_for_name_replaces_changed_google_numbers(tmp_path):
    path = tmp_path / "contacts.json"
    save_contacts([Contact(name="Anna Schmidt", number="+4917612345678", source="google", number_type="mobile")], path)

    changed = sync_contact_for_name("Anna Schmidt", [("+4917699999999", "home")], overwrite_local=True, path=path)

    assert changed is True
    assert load_contacts(path) == [
        Contact(name="Anna Schmidt", number="+4917699999999", source="google", number_type="home")
    ]


def test_sync_contact_for_name_noop_when_unchanged(tmp_path):
    path = tmp_path / "contacts.json"
    save_contacts([Contact(name="Anna Schmidt", number="+4917612345678", source="google", number_type="mobile")], path)

    changed = sync_contact_for_name("Anna Schmidt", [("+4917612345678", "mobile")], overwrite_local=True, path=path)

    assert changed is False
    assert load_contacts(path) == [
        Contact(name="Anna Schmidt", number="+4917612345678", source="google", number_type="mobile")
    ]


def test_sync_contact_for_name_local_wins_skips_entirely(tmp_path):
    path = tmp_path / "contacts.json"
    save_contacts([Contact(name="Anna Schmidt", number="+4917600000000", source="local")], path)

    changed = sync_contact_for_name("Anna Schmidt", [("+4917612345678", "mobile")], overwrite_local=False, path=path)

    assert changed is False
    assert load_contacts(path) == [Contact(name="Anna Schmidt", number="+4917600000000", source="local")]


def test_sync_contact_for_name_google_wins_overwrites_local(tmp_path):
    path = tmp_path / "contacts.json"
    save_contacts([Contact(name="Anna Schmidt", number="+4917600000000", source="local")], path)

    changed = sync_contact_for_name("Anna Schmidt", [("+4917612345678", "mobile")], overwrite_local=True, path=path)

    assert changed is True
    assert load_contacts(path) == [
        Contact(name="Anna Schmidt", number="+4917612345678", source="google", number_type="mobile")
    ]


def test_sync_contact_for_name_detects_type_only_change(tmp_path):
    path = tmp_path / "contacts.json"
    save_contacts([Contact(name="Anna Schmidt", number="+4917612345678", source="google", number_type="")], path)

    changed = sync_contact_for_name("Anna Schmidt", [("+4917612345678", "mobile")], overwrite_local=True, path=path)

    assert changed is True
    assert load_contacts(path) == [
        Contact(name="Anna Schmidt", number="+4917612345678", source="google", number_type="mobile")
    ]


def test_sync_contact_for_name_ignores_number_order_for_noop_check(tmp_path):
    path = tmp_path / "contacts.json"
    save_contacts(
        [
            Contact(name="Anna Schmidt", number="+4917612345678", source="google", number_type="mobile"),
            Contact(name="Anna Schmidt", number="+4917698765432", source="google", number_type="home"),
        ],
        path,
    )

    changed = sync_contact_for_name(
        "Anna Schmidt",
        [("+4917698765432", "home"), ("+4917612345678", "mobile")],
        overwrite_local=True,
        path=path,
    )

    assert changed is False
