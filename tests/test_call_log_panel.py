from PySide6.QtCore import Qt

from voice2fritz import call_log as call_log_module
from voice2fritz import contacts as contacts_module
from voice2fritz.gui.call_log_panel import CallLogPanel


def _entry(number="+4917612345678", name="Anna Schmidt", direction="outgoing", timestamp="2026-08-04T14:32:00", duration_seconds=135):
    return call_log_module.CallLogEntry(number=number, name=name, direction=direction, timestamp=timestamp, duration_seconds=duration_seconds)


def test_populates_list_from_stored_entries(qtbot, monkeypatch):
    monkeypatch.setattr(call_log_module, "load_call_log", lambda path=call_log_module.DEFAULT_CALL_LOG_PATH: [_entry(), _entry(number="+4930123456", name="Ben Weber")])

    panel = CallLogPanel()
    qtbot.addWidget(panel)

    assert panel.entry_list.count() == 2


def test_double_click_emits_entry_activated_without_closing(qtbot, monkeypatch):
    monkeypatch.setattr(call_log_module, "load_call_log", lambda path=call_log_module.DEFAULT_CALL_LOG_PATH: [_entry(number="+4917612345678")])

    panel = CallLogPanel()
    qtbot.addWidget(panel)

    with qtbot.waitSignal(panel.entryActivated, timeout=1000) as blocker:
        panel._on_item_activated(panel.entry_list.item(0))

    assert blocker.args == ["+4917612345678"]
    assert panel.entry_list.count() == 1  # untouched by activation


def test_clear_button_empties_list(qtbot, monkeypatch):
    monkeypatch.setattr(call_log_module, "load_call_log", lambda path=call_log_module.DEFAULT_CALL_LOG_PATH: [_entry()])
    cleared = []
    monkeypatch.setattr(call_log_module, "clear_call_log", lambda path=call_log_module.DEFAULT_CALL_LOG_PATH: cleared.append(True))

    panel = CallLogPanel()
    qtbot.addWidget(panel)
    assert panel.entry_list.count() == 1

    monkeypatch.setattr(call_log_module, "load_call_log", lambda path=call_log_module.DEFAULT_CALL_LOG_PATH: [])
    panel.clear_button.click()

    assert cleared == [True]
    assert panel.entry_list.count() == 0


def test_missed_entry_has_zero_duration_row_text(qtbot, monkeypatch):
    monkeypatch.setattr(call_log_module, "load_call_log", lambda path=call_log_module.DEFAULT_CALL_LOG_PATH: [_entry(direction="missed", duration_seconds=0, name="")])

    panel = CallLogPanel()
    qtbot.addWidget(panel)

    item = panel.entry_list.item(0)
    entry = item.data(Qt.ItemDataRole.UserRole)
    assert entry.direction == "missed"


def test_reload_list_picks_up_new_entries(qtbot, monkeypatch):
    entries = [_entry()]
    monkeypatch.setattr(call_log_module, "load_call_log", lambda path=call_log_module.DEFAULT_CALL_LOG_PATH: entries)

    panel = CallLogPanel()
    qtbot.addWidget(panel)
    assert panel.entry_list.count() == 1

    entries.append(_entry(number="+4930123456", name="Ben Weber"))
    panel._reload_list()

    assert panel.entry_list.count() == 2


def test_context_menu_offers_redial_for_outgoing_call(qtbot, monkeypatch):
    monkeypatch.setattr(call_log_module, "load_call_log", lambda path=call_log_module.DEFAULT_CALL_LOG_PATH: [_entry(direction="outgoing", number="+4917612345678")])

    panel = CallLogPanel()
    qtbot.addWidget(panel)

    menu = panel._build_context_menu(panel.entry_list.item(0))
    actions = menu.actions()
    assert [action.text() for action in actions][0] == "Redial"

    with qtbot.waitSignal(panel.dialRequested, timeout=1000) as blocker:
        actions[0].trigger()
    assert blocker.args == ["+4917612345678"]


def test_context_menu_offers_call_back_for_incoming_and_missed_calls(qtbot, monkeypatch):
    monkeypatch.setattr(call_log_module, "load_call_log", lambda path=call_log_module.DEFAULT_CALL_LOG_PATH: [
        _entry(direction="incoming", number="+4930111111"),
        _entry(direction="missed", number="+4930222222", duration_seconds=0),
    ])

    panel = CallLogPanel()
    qtbot.addWidget(panel)

    for row in range(2):
        menu = panel._build_context_menu(panel.entry_list.item(row))
        assert menu.actions()[0].text() == "Call back"


def _menu_texts(menu):
    return [action.text() for action in menu.actions()]


def test_context_menu_offers_save_for_unknown_number(qtbot, monkeypatch):
    monkeypatch.setattr(call_log_module, "load_call_log", lambda path=call_log_module.DEFAULT_CALL_LOG_PATH: [_entry(number="+4930111111", name="")])
    monkeypatch.setattr(contacts_module, "load_contacts", lambda path=contacts_module.DEFAULT_CONTACTS_PATH: [])

    panel = CallLogPanel()
    qtbot.addWidget(panel)

    assert "Save to contacts…" in _menu_texts(panel._build_context_menu(panel.entry_list.item(0)))


def test_context_menu_hides_save_for_known_number(qtbot, monkeypatch):
    monkeypatch.setattr(call_log_module, "load_call_log", lambda path=call_log_module.DEFAULT_CALL_LOG_PATH: [_entry(number="+4930111111")])
    monkeypatch.setattr(contacts_module, "load_contacts", lambda path=contacts_module.DEFAULT_CONTACTS_PATH: [contacts_module.Contact(name="Anna", number="+4930111111")])

    panel = CallLogPanel()
    qtbot.addWidget(panel)

    assert "Save to contacts…" not in _menu_texts(panel._build_context_menu(panel.entry_list.item(0)))


def test_save_action_adds_contact_with_prompted_name(qtbot, monkeypatch):
    added = []
    monkeypatch.setattr(contacts_module, "load_contacts", lambda path=contacts_module.DEFAULT_CONTACTS_PATH: [])
    monkeypatch.setattr(
        contacts_module,
        "add_contact",
        lambda name, number, number_type="", path=contacts_module.DEFAULT_CONTACTS_PATH: added.append((name, number)),
    )
    monkeypatch.setattr(call_log_module, "load_call_log", lambda path=call_log_module.DEFAULT_CALL_LOG_PATH: [_entry(number="+4930111111", name="")])

    panel = CallLogPanel()
    qtbot.addWidget(panel)
    monkeypatch.setattr(panel, "_prompt_contact_name", lambda number, default_name: "Carla")

    menu = panel._build_context_menu(panel.entry_list.item(0))
    save_action = next(action for action in menu.actions() if action.text() == "Save to contacts…")
    with qtbot.waitSignal(panel.contactSaved, timeout=1000):
        save_action.trigger()

    assert added == [("Carla", "+4930111111")]


def test_cancelled_save_prompt_adds_nothing(qtbot, monkeypatch):
    added = []
    monkeypatch.setattr(contacts_module, "load_contacts", lambda path=contacts_module.DEFAULT_CONTACTS_PATH: [])
    monkeypatch.setattr(contacts_module, "add_contact", lambda *args, **kwargs: added.append(args))
    monkeypatch.setattr(call_log_module, "load_call_log", lambda path=call_log_module.DEFAULT_CALL_LOG_PATH: [_entry(number="+4930111111")])

    panel = CallLogPanel()
    qtbot.addWidget(panel)
    monkeypatch.setattr(panel, "_prompt_contact_name", lambda number, default_name: None)

    panel._save_to_contacts(panel.entry_list.item(0).data(Qt.ItemDataRole.UserRole))

    assert added == []
