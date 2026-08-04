import pytest
from PySide6.QtWidgets import QMessageBox

from voice2fritz import config as config_module, tr064
from voice2fritz.gui.contacts_dialog import ContactsDialog


@pytest.fixture(autouse=True)
def no_modal_warnings(monkeypatch):
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)


def test_populates_list_from_fetched_contacts(qtbot, monkeypatch):
    monkeypatch.setattr(config_module, "load_fritzbox_username", lambda path=config_module.DEFAULT_CONFIG_PATH: "fritzuser")
    monkeypatch.setattr(config_module, "get_fritzbox_password", lambda username: "secret")
    monkeypatch.setattr(
        tr064,
        "get_phonebook",
        lambda host, username, password: [
            tr064.Contact(name="Anna Schmidt", numbers=["+4917612345678", "+4917698765432"]),
            tr064.Contact(name="Ben Weber", numbers=["+4930123456"]),
        ],
    )

    dialog = ContactsDialog("fritz.box")
    qtbot.addWidget(dialog)

    assert dialog.contact_list.count() == 3
    assert dialog.contact_list.item(0).text() == "Anna Schmidt — +4917612345678"
    assert dialog.contact_list.item(2).text() == "Ben Weber — +4930123456"


def test_double_click_emits_selected_number_and_closes(qtbot, monkeypatch):
    monkeypatch.setattr(config_module, "load_fritzbox_username", lambda path=config_module.DEFAULT_CONFIG_PATH: "fritzuser")
    monkeypatch.setattr(config_module, "get_fritzbox_password", lambda username: "secret")
    monkeypatch.setattr(
        tr064,
        "get_phonebook",
        lambda host, username, password: [tr064.Contact(name="Anna Schmidt", numbers=["+4917612345678"])],
    )

    dialog = ContactsDialog("fritz.box")
    qtbot.addWidget(dialog)

    with qtbot.waitSignal(dialog.contactSelected, timeout=1000) as blocker:
        dialog._on_item_activated(dialog.contact_list.item(0))

    assert blocker.args == ["+4917612345678"]


def test_no_fritzbox_username_shows_warning_and_empty_list(qtbot, monkeypatch):
    monkeypatch.setattr(config_module, "load_fritzbox_username", lambda path=config_module.DEFAULT_CONFIG_PATH: None)

    dialog = ContactsDialog("fritz.box")
    qtbot.addWidget(dialog)

    assert dialog.contact_list.count() == 0


def test_fetch_failure_shows_warning_and_leaves_list_empty(qtbot, monkeypatch):
    monkeypatch.setattr(config_module, "load_fritzbox_username", lambda path=config_module.DEFAULT_CONFIG_PATH: "fritzuser")
    monkeypatch.setattr(config_module, "get_fritzbox_password", lambda username: "secret")

    def raise_error(host, username, password):
        raise ValueError("network error")

    monkeypatch.setattr(tr064, "get_phonebook", raise_error)

    dialog = ContactsDialog("fritz.box")
    qtbot.addWidget(dialog)

    assert dialog.contact_list.count() == 0
