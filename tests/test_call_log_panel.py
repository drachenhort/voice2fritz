from PySide6.QtCore import Qt

from voice2fritz import call_log as call_log_module
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
