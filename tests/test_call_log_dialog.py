from PySide6.QtCore import Qt

from voice2fritz import call_log as call_log_module
from voice2fritz.gui.call_log_dialog import CallLogDialog


def _entry(number="+4917612345678", name="Anna Schmidt", direction="outgoing", timestamp="2026-08-04T14:32:00", duration_seconds=135):
    return call_log_module.CallLogEntry(number=number, name=name, direction=direction, timestamp=timestamp, duration_seconds=duration_seconds)


def test_populates_list_from_stored_entries(qtbot, monkeypatch):
    monkeypatch.setattr(call_log_module, "load_call_log", lambda path=call_log_module.DEFAULT_CALL_LOG_PATH: [_entry(), _entry(number="+4930123456", name="Ben Weber")])

    dialog = CallLogDialog()
    qtbot.addWidget(dialog)

    assert dialog.entry_list.count() == 2


def test_double_click_emits_selected_number_and_closes(qtbot, monkeypatch):
    monkeypatch.setattr(call_log_module, "load_call_log", lambda path=call_log_module.DEFAULT_CALL_LOG_PATH: [_entry(number="+4917612345678")])

    dialog = CallLogDialog()
    qtbot.addWidget(dialog)

    with qtbot.waitSignal(dialog.callSelected, timeout=1000) as blocker:
        dialog._on_item_activated(dialog.entry_list.item(0))

    assert blocker.args == ["+4917612345678"]


def test_clear_button_empties_list(qtbot, monkeypatch):
    monkeypatch.setattr(call_log_module, "load_call_log", lambda path=call_log_module.DEFAULT_CALL_LOG_PATH: [_entry()])
    cleared = []
    monkeypatch.setattr(call_log_module, "clear_call_log", lambda path=call_log_module.DEFAULT_CALL_LOG_PATH: cleared.append(True))

    dialog = CallLogDialog()
    qtbot.addWidget(dialog)
    assert dialog.entry_list.count() == 1

    monkeypatch.setattr(call_log_module, "load_call_log", lambda path=call_log_module.DEFAULT_CALL_LOG_PATH: [])
    dialog.clear_button.click()

    assert cleared == [True]
    assert dialog.entry_list.count() == 0


def test_missed_entry_has_zero_duration_row_text(qtbot, monkeypatch):
    monkeypatch.setattr(call_log_module, "load_call_log", lambda path=call_log_module.DEFAULT_CALL_LOG_PATH: [_entry(direction="missed", duration_seconds=0, name="")])

    dialog = CallLogDialog()
    qtbot.addWidget(dialog)

    item = dialog.entry_list.item(0)
    entry = item.data(Qt.ItemDataRole.UserRole)
    assert entry.direction == "missed"
