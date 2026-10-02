import pytest

from voice2fritz import config, i18n, main
from voice2fritz.i18n import language_from_locale, system_language_offer


@pytest.fixture(autouse=True)
def restore_language():
    yield
    i18n.set_language("en")


@pytest.mark.parametrize(("locale_name", "language"), [("de_DE", "de"), ("de-AT", "de"), ("en_US", "en"), ("C", "c")])
def test_language_from_locale(locale_name, language):
    assert language_from_locale(locale_name) == language


def test_offers_supported_system_language_that_is_not_set():
    assert system_language_offer("de_DE", configured="en", declined=None) == "de"


def test_no_offer_when_already_set():
    assert system_language_offer("de_DE", configured="de", declined=None) is None


def test_no_offer_for_unsupported_system_language():
    assert system_language_offer("fr_FR", configured="en", declined=None) is None


def test_no_offer_after_user_declined_it():
    assert system_language_offer("de_DE", configured="en", declined="de") is None


class _Recorder:
    def __init__(self, monkeypatch, system_locale, configured, declined, answer):
        self.saved_language = None
        self.saved_declined = None
        self.asked = []
        monkeypatch.setattr(main.QLocale, "system", staticmethod(lambda: main.QLocale(system_locale)))
        monkeypatch.setattr(config, "load_declined_system_language", lambda path=config.DEFAULT_CONFIG_PATH: declined)
        monkeypatch.setattr(config, "save_language", lambda value, path=config.DEFAULT_CONFIG_PATH: setattr(self, "saved_language", value))
        monkeypatch.setattr(
            config, "save_declined_system_language", lambda value, path=config.DEFAULT_CONFIG_PATH: setattr(self, "saved_declined", value)
        )
        monkeypatch.setattr(main, "ask_to_switch_language", lambda offered: self.asked.append(offered) or answer)
        i18n.set_language(configured)


def test_startup_switches_when_user_accepts(monkeypatch):
    recorder = _Recorder(monkeypatch, "de_DE", configured="en", declined=None, answer=True)

    main._offer_system_language()

    assert recorder.asked == ["de"]
    assert recorder.saved_language == "de"
    assert i18n.current_language() == "de"


def test_startup_remembers_a_declined_offer(monkeypatch):
    recorder = _Recorder(monkeypatch, "de_DE", configured="en", declined=None, answer=False)

    main._offer_system_language()

    assert recorder.saved_declined == "de"
    assert recorder.saved_language is None
    assert i18n.current_language() == "en"


def test_startup_does_not_ask_when_system_language_is_already_set(monkeypatch):
    recorder = _Recorder(monkeypatch, "de_DE", configured="de", declined=None, answer=True)

    main._offer_system_language()

    assert recorder.asked == []


def test_prompt_is_worded_in_the_offered_language(qtbot, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    from voice2fritz.gui import language_prompt

    shown = {}

    def fake_exec(box):
        shown["text"] = box.text()
        shown["buttons"] = [button.text() for button in box.buttons()]
        return 0

    monkeypatch.setattr(QMessageBox, "exec", fake_exec)

    language_prompt.ask_to_switch_language("de")

    assert shown["text"] == "Deine Systemsprache ist Deutsch. voice2fritz auf Deutsch umstellen?"
    assert shown["buttons"] == ["Auf Deutsch umstellen", "English beibehalten"]
    assert i18n.current_language() == "en"
