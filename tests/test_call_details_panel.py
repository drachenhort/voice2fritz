from voice2fritz.gui.call_details_panel import CallDetailsPanel


def test_starts_idle(qtbot):
    panel = CallDetailsPanel()
    qtbot.addWidget(panel)

    assert panel.name_label.text() == "No active call"
    assert panel.duration_label.text() == ""


def test_set_active_call_with_name(qtbot):
    panel = CallDetailsPanel()
    qtbot.addWidget(panel)

    panel.set_active_call("Anna Schmidt", "+4917612345678")

    assert panel.name_label.text() == "Anna Schmidt"
    assert panel.state_label.text() == "Active"
    assert panel.duration_label.text() == "0:00"


def test_set_active_call_without_name_shows_number(qtbot):
    panel = CallDetailsPanel()
    qtbot.addWidget(panel)

    panel.set_active_call("", "+4917612345678")

    assert panel.name_label.text() == "+4917612345678"


def test_set_idle_resets_everything(qtbot):
    panel = CallDetailsPanel()
    qtbot.addWidget(panel)
    panel.set_active_call("Anna Schmidt", "+4917612345678")

    panel.set_idle()

    assert panel.name_label.text() == "No active call"
    assert panel.state_label.text() == ""
    assert panel.duration_label.text() == ""


def test_set_state_text_updates_state_label(qtbot):
    panel = CallDetailsPanel()
    qtbot.addWidget(panel)
    panel.set_active_call("Anna Schmidt", "+4917612345678")

    panel.set_state_text("Ringing")

    assert panel.state_label.text() == "Ringing"


def test_duration_label_ticks_up(qtbot):
    panel = CallDetailsPanel()
    qtbot.addWidget(panel)
    panel.set_active_call("Anna Schmidt", "+4917612345678")

    qtbot.wait(1100)

    assert panel.duration_label.text() == "0:01"


def test_set_idle_stops_the_timer(qtbot):
    panel = CallDetailsPanel()
    qtbot.addWidget(panel)
    panel.set_active_call("Anna Schmidt", "+4917612345678")
    qtbot.wait(1100)
    panel.set_idle()

    qtbot.wait(1100)

    assert panel.duration_label.text() == ""
