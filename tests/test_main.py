from voice2fritz.main import build_window


def test_build_window_has_correct_title(qtbot):
    window = build_window()
    qtbot.addWidget(window)
    assert window.windowTitle() == "voice2fritz"
