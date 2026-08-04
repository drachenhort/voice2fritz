from voice2fritz.contacts import Contact, add_contact, delete_contact, load_contacts, save_contacts


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

    add_contact("Ben Weber", "+4930123456", path)

    assert load_contacts(path) == [
        Contact(name="Anna Schmidt", number="+4917612345678"),
        Contact(name="Ben Weber", number="+4930123456"),
    ]


def test_add_contact_creates_parent_dirs(tmp_path):
    path = tmp_path / "nested" / "dir" / "contacts.json"

    add_contact("Anna Schmidt", "+4917612345678", path)

    assert path.exists()
    assert load_contacts(path) == [Contact(name="Anna Schmidt", number="+4917612345678")]


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
