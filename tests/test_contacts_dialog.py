import pytest

from voice2fritz import config as config_module
from voice2fritz import contacts as contacts_module
from voice2fritz.gui.contacts_dialog import ContactsDialog


@pytest.fixture(autouse=True)
def no_sort_order_persistence(monkeypatch):
    monkeypatch.setattr(config_module, "load_contacts_sort_order", lambda path=config_module.DEFAULT_CONFIG_PATH: "name")
    monkeypatch.setattr(config_module, "save_contacts_sort_order", lambda value, path=config_module.DEFAULT_CONFIG_PATH: None)


def test_wraps_a_contacts_panel_with_populated_table(qtbot, monkeypatch):
    monkeypatch.setattr(
        contacts_module,
        "load_contacts",
        lambda path=contacts_module.DEFAULT_CONTACTS_PATH: [
            contacts_module.Contact(name="Anna Schmidt", number="+4917612345678", number_type="mobile"),
        ],
    )

    dialog = ContactsDialog()
    qtbot.addWidget(dialog)

    assert dialog.contact_table.rowCount() == 1
    assert dialog.contact_table.item(0, 0).text() == "Anna Schmidt"


def test_double_click_emits_selected_number_and_closes(qtbot, monkeypatch):
    monkeypatch.setattr(
        contacts_module,
        "load_contacts",
        lambda path=contacts_module.DEFAULT_CONTACTS_PATH: [contacts_module.Contact(name="Anna Schmidt", number="+4917612345678")],
    )

    dialog = ContactsDialog()
    qtbot.addWidget(dialog)
    dialog.show()

    with qtbot.waitSignal(dialog.contactSelected, timeout=1000) as blocker:
        dialog._on_item_activated(dialog.contact_table.item(0, 0))

    assert blocker.args == ["+4917612345678"]
    assert not dialog.isVisible()
