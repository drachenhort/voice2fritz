from voice2fritz.gui.incoming_call_popup import IncomingCallPopup


def test_shows_name_and_number(qtbot):
    popup = IncomingCallPopup("Anna Schmidt", "+4917612345678")
    qtbot.addWidget(popup)

    assert popup.name_label.text() == "Anna Schmidt"
    assert popup.number_label.text() == "+4917612345678"


def test_shows_number_as_name_when_no_name(qtbot):
    popup = IncomingCallPopup("", "+4917612345678")
    qtbot.addWidget(popup)

    assert popup.name_label.text() == "+4917612345678"
    assert popup.number_label.text() == "+4917612345678"


def test_avatar_shows_initials_for_named_caller(qtbot):
    popup = IncomingCallPopup("Anna Schmidt", "+4917612345678")
    qtbot.addWidget(popup)

    assert popup.avatar_label.text() == "AS"


def test_avatar_shows_fallback_glyph_for_unnamed_caller(qtbot):
    popup = IncomingCallPopup("", "+4917612345678")
    qtbot.addWidget(popup)

    assert popup.avatar_label.text() == "📞"


def test_answer_button_emits_answered_signal(qtbot):
    popup = IncomingCallPopup("Anna Schmidt", "+4917612345678")
    qtbot.addWidget(popup)

    with qtbot.waitSignal(popup.answered, timeout=1000):
        popup.answer_button.click()


def test_decline_button_emits_declined_signal(qtbot):
    popup = IncomingCallPopup("Anna Schmidt", "+4917612345678")
    qtbot.addWidget(popup)

    with qtbot.waitSignal(popup.declined, timeout=1000):
        popup.decline_button.click()


def test_window_stays_on_top_flag_is_set(qtbot):
    from PySide6.QtCore import Qt

    popup = IncomingCallPopup("Anna Schmidt", "+4917612345678")
    qtbot.addWidget(popup)

    assert popup.windowFlags() & Qt.WindowType.WindowStaysOnTopHint
