from voice2fritz import contacts as contacts_module
from voice2fritz.gui.contacts_dialog import ContactsDialog


def test_populates_list_from_stored_contacts(qtbot, monkeypatch):
    monkeypatch.setattr(
        contacts_module,
        "load_contacts",
        lambda path=contacts_module.DEFAULT_CONTACTS_PATH: [
            contacts_module.Contact(name="Anna Schmidt", number="+4917612345678"),
            contacts_module.Contact(name="Ben Weber", number="+4930123456"),
        ],
    )

    dialog = ContactsDialog()
    qtbot.addWidget(dialog)

    assert dialog.contact_list.count() == 2
    assert dialog.contact_list.item(0).text() == "Anna Schmidt — +4917612345678"
    assert dialog.contact_list.item(1).text() == "Ben Weber — +4930123456"


def test_double_click_emits_selected_number_and_closes(qtbot, monkeypatch):
    monkeypatch.setattr(
        contacts_module,
        "load_contacts",
        lambda path=contacts_module.DEFAULT_CONTACTS_PATH: [contacts_module.Contact(name="Anna Schmidt", number="+4917612345678")],
    )

    dialog = ContactsDialog()
    qtbot.addWidget(dialog)

    with qtbot.waitSignal(dialog.contactSelected, timeout=1000) as blocker:
        dialog._on_item_activated(dialog.contact_list.item(0))

    assert blocker.args == ["+4917612345678"]


def test_add_button_adds_contact_and_reloads_list(qtbot, monkeypatch):
    monkeypatch.setattr(contacts_module, "load_contacts", lambda path=contacts_module.DEFAULT_CONTACTS_PATH: [])
    added = []
    monkeypatch.setattr(contacts_module, "add_contact", lambda name, number, path=contacts_module.DEFAULT_CONTACTS_PATH: added.append((name, number)))

    dialog = ContactsDialog()
    qtbot.addWidget(dialog)

    dialog.name_edit.setText("Anna Schmidt")
    dialog.number_edit.setText("+4917612345678")
    dialog.add_button.click()

    assert added == [("Anna Schmidt", "+4917612345678")]
    assert dialog.name_edit.text() == ""
    assert dialog.number_edit.text() == ""


def test_add_button_does_nothing_with_empty_fields(qtbot, monkeypatch):
    monkeypatch.setattr(contacts_module, "load_contacts", lambda path=contacts_module.DEFAULT_CONTACTS_PATH: [])
    added = []
    monkeypatch.setattr(contacts_module, "add_contact", lambda name, number, path=contacts_module.DEFAULT_CONTACTS_PATH: added.append((name, number)))

    dialog = ContactsDialog()
    qtbot.addWidget(dialog)

    dialog.add_button.click()

    assert added == []


def test_delete_button_removes_selected_contact(qtbot, monkeypatch):
    monkeypatch.setattr(
        contacts_module,
        "load_contacts",
        lambda path=contacts_module.DEFAULT_CONTACTS_PATH: [contacts_module.Contact(name="Anna Schmidt", number="+4917612345678")],
    )
    deleted = []
    monkeypatch.setattr(contacts_module, "delete_contact", lambda index, path=contacts_module.DEFAULT_CONTACTS_PATH: deleted.append(index))

    dialog = ContactsDialog()
    qtbot.addWidget(dialog)

    dialog.contact_list.setCurrentRow(0)
    dialog.delete_button.click()

    assert deleted == [0]
