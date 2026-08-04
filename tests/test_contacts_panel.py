import pytest

from voice2fritz import config as config_module
from voice2fritz import contacts as contacts_module
from voice2fritz.gui.contacts_panel import ContactsPanel


@pytest.fixture(autouse=True)
def no_sort_order_persistence(monkeypatch):
    monkeypatch.setattr(config_module, "load_contacts_sort_order", lambda path=config_module.DEFAULT_CONFIG_PATH: "name")
    monkeypatch.setattr(config_module, "save_contacts_sort_order", lambda value, path=config_module.DEFAULT_CONFIG_PATH: None)


def _row_texts(panel, row):
    return (
        panel.contact_table.item(row, 0).text(),
        panel.contact_table.item(row, 1).text(),
        panel.contact_table.item(row, 2).text(),
    )


def test_populates_table_from_stored_contacts(qtbot, monkeypatch):
    monkeypatch.setattr(
        contacts_module,
        "load_contacts",
        lambda path=contacts_module.DEFAULT_CONTACTS_PATH: [
            contacts_module.Contact(name="Anna Schmidt", number="+4917612345678", number_type="mobile"),
            contacts_module.Contact(name="Ben Weber", number="+4930123456"),
        ],
    )

    panel = ContactsPanel()
    qtbot.addWidget(panel)

    assert panel.contact_table.rowCount() == 2
    assert _row_texts(panel, 0) == ("Anna Schmidt", "mobile", "+4917612345678")
    assert _row_texts(panel, 1) == ("Ben Weber", "", "+4930123456")


def test_double_click_emits_selected_number(qtbot, monkeypatch):
    monkeypatch.setattr(
        contacts_module,
        "load_contacts",
        lambda path=contacts_module.DEFAULT_CONTACTS_PATH: [contacts_module.Contact(name="Anna Schmidt", number="+4917612345678")],
    )

    panel = ContactsPanel()
    qtbot.addWidget(panel)

    with qtbot.waitSignal(panel.contactSelected, timeout=1000) as blocker:
        panel._on_item_activated(panel.contact_table.item(0, 0))

    assert blocker.args == ["+4917612345678"]


def test_add_button_adds_contact_and_reloads_table(qtbot, monkeypatch):
    monkeypatch.setattr(contacts_module, "load_contacts", lambda path=contacts_module.DEFAULT_CONTACTS_PATH: [])
    added = []
    monkeypatch.setattr(
        contacts_module,
        "add_contact",
        lambda name, number, number_type="", path=contacts_module.DEFAULT_CONTACTS_PATH: added.append((name, number, number_type)),
    )

    panel = ContactsPanel()
    qtbot.addWidget(panel)

    panel.name_edit.setText("Anna Schmidt")
    panel.number_edit.setText("+4917612345678")
    panel.type_edit.setText("mobile")
    panel.add_button.click()

    assert added == [("Anna Schmidt", "+4917612345678", "mobile")]
    assert panel.name_edit.text() == ""
    assert panel.number_edit.text() == ""
    assert panel.type_edit.text() == ""


def test_add_button_works_without_type(qtbot, monkeypatch):
    monkeypatch.setattr(contacts_module, "load_contacts", lambda path=contacts_module.DEFAULT_CONTACTS_PATH: [])
    added = []
    monkeypatch.setattr(
        contacts_module,
        "add_contact",
        lambda name, number, number_type="", path=contacts_module.DEFAULT_CONTACTS_PATH: added.append((name, number, number_type)),
    )

    panel = ContactsPanel()
    qtbot.addWidget(panel)

    panel.name_edit.setText("Anna Schmidt")
    panel.number_edit.setText("+4917612345678")
    panel.add_button.click()

    assert added == [("Anna Schmidt", "+4917612345678", "")]


def test_add_button_does_nothing_with_empty_fields(qtbot, monkeypatch):
    monkeypatch.setattr(contacts_module, "load_contacts", lambda path=contacts_module.DEFAULT_CONTACTS_PATH: [])
    added = []
    monkeypatch.setattr(
        contacts_module,
        "add_contact",
        lambda name, number, number_type="", path=contacts_module.DEFAULT_CONTACTS_PATH: added.append((name, number, number_type)),
    )

    panel = ContactsPanel()
    qtbot.addWidget(panel)

    panel.add_button.click()

    assert added == []


def test_delete_button_removes_selected_contact(qtbot, monkeypatch):
    contact = contacts_module.Contact(name="Anna Schmidt", number="+4917612345678")
    monkeypatch.setattr(contacts_module, "load_contacts", lambda path=contacts_module.DEFAULT_CONTACTS_PATH: [contact])
    deleted = []
    monkeypatch.setattr(contacts_module, "delete_contact_by_value", lambda c, path=contacts_module.DEFAULT_CONTACTS_PATH: deleted.append(c))

    panel = ContactsPanel()
    qtbot.addWidget(panel)

    panel.contact_table.setCurrentCell(0, 0)
    panel.delete_button.click()

    assert deleted == [contact]


def test_table_sorted_by_name_by_default(qtbot, monkeypatch):
    monkeypatch.setattr(
        contacts_module,
        "load_contacts",
        lambda path=contacts_module.DEFAULT_CONTACTS_PATH: [
            contacts_module.Contact(name="Ben Weber", number="+4930123456"),
            contacts_module.Contact(name="Anna Schmidt", number="+4917612345678"),
        ],
    )

    panel = ContactsPanel()
    qtbot.addWidget(panel)

    assert _row_texts(panel, 0) == ("Anna Schmidt", "", "+4917612345678")
    assert _row_texts(panel, 1) == ("Ben Weber", "", "+4930123456")


def test_switching_sort_to_number_resorts_table_and_persists(qtbot, monkeypatch):
    monkeypatch.setattr(
        contacts_module,
        "load_contacts",
        lambda path=contacts_module.DEFAULT_CONTACTS_PATH: [
            contacts_module.Contact(name="Ben Weber", number="+4930123456"),
            contacts_module.Contact(name="Anna Schmidt", number="+4917612345678"),
        ],
    )
    saved = []
    monkeypatch.setattr(config_module, "save_contacts_sort_order", lambda value, path=config_module.DEFAULT_CONFIG_PATH: saved.append(value))

    panel = ContactsPanel()
    qtbot.addWidget(panel)

    panel.sort_combo.setCurrentIndex(panel.sort_combo.findData("number"))

    assert saved == ["number"]
    assert _row_texts(panel, 0) == ("Anna Schmidt", "", "+4917612345678")
    assert _row_texts(panel, 1) == ("Ben Weber", "", "+4930123456")


def test_sort_combo_initialized_from_saved_setting(qtbot, monkeypatch):
    monkeypatch.setattr(config_module, "load_contacts_sort_order", lambda path=config_module.DEFAULT_CONFIG_PATH: "number")
    monkeypatch.setattr(contacts_module, "load_contacts", lambda path=contacts_module.DEFAULT_CONTACTS_PATH: [])

    panel = ContactsPanel()
    qtbot.addWidget(panel)

    assert panel.sort_combo.currentData() == "number"


def test_select_uses_sorted_row_not_storage_order(qtbot, monkeypatch):
    monkeypatch.setattr(
        contacts_module,
        "load_contacts",
        lambda path=contacts_module.DEFAULT_CONTACTS_PATH: [
            contacts_module.Contact(name="Ben Weber", number="+4930123456"),
            contacts_module.Contact(name="Anna Schmidt", number="+4917612345678"),
        ],
    )

    panel = ContactsPanel()
    qtbot.addWidget(panel)

    with qtbot.waitSignal(panel.contactSelected, timeout=1000) as blocker:
        panel._on_item_activated(panel.contact_table.item(0, 0))

    assert blocker.args == ["+4917612345678"]


def test_sync_button_reloads_table_on_success(qtbot, monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    from voice2fritz.gui import contacts_panel as contacts_panel_module

    monkeypatch.setattr(
        contacts_module,
        "load_contacts",
        lambda path=contacts_module.DEFAULT_CONTACTS_PATH: [
            contacts_module.Contact(name="Anna Schmidt", number="+4917612345678", source="google", number_type="mobile")
        ],
    )
    monkeypatch.setattr(contacts_panel_module.google_contacts, "sync_google_contacts", lambda: 1)
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)

    panel = ContactsPanel()
    qtbot.addWidget(panel)

    panel.sync_button.click()

    assert panel.contact_table.rowCount() == 1
    assert _row_texts(panel, 0) == ("Anna Schmidt", "mobile", "+4917612345678")


def test_sync_button_shows_warning_on_failure(qtbot, monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    from voice2fritz.gui import contacts_panel as contacts_panel_module

    monkeypatch.setattr(contacts_module, "load_contacts", lambda path=contacts_module.DEFAULT_CONTACTS_PATH: [])

    def raise_error():
        raise ValueError("auth failed")

    monkeypatch.setattr(contacts_panel_module.google_contacts, "sync_google_contacts", raise_error)
    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: warnings.append(a))

    panel = ContactsPanel()
    qtbot.addWidget(panel)

    panel.sync_button.click()

    assert len(warnings) == 1
