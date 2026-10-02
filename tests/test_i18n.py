import ast
from pathlib import Path

import pytest

from voice2fritz import i18n
from voice2fritz.gui import nav_rail
from voice2fritz.i18n import _GERMAN, current_language, set_language, tr

SOURCE_DIR = Path(__file__).parent.parent / "src" / "voice2fritz"


@pytest.fixture(autouse=True)
def restore_language():
    yield
    set_language("en")


def _tr_literals():
    """Every string literal passed as the first argument to tr() in the package."""
    for path in SOURCE_DIR.rglob("*.py"):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "tr"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                yield path.name, node.args[0].value


def test_english_is_the_default():
    assert current_language() == "en"
    assert tr("Save") == "Save"


def test_german_translation():
    set_language("de")
    assert tr("Save") == "Speichern"


def test_placeholders_are_filled_in_both_languages():
    assert tr("Name for {number}:", number="0301234") == "Name for 0301234:"
    set_language("de")
    assert tr("Name for {number}:", number="0301234") == "Name für 0301234:"


def test_unknown_text_falls_back_to_english():
    set_language("de")
    assert tr("Not a known text") == "Not a known text"


def test_unsupported_language_falls_back_to_english():
    set_language("fr")
    assert current_language() == "en"


def test_every_tr_text_has_a_german_translation():
    literals = list(_tr_literals())
    assert len(literals) > 50  # sanity check that the scan finds the UI texts
    missing = sorted({f"{name}: {text!r}" for name, text in literals if text not in _GERMAN})
    assert missing == []


def test_navigation_titles_and_call_states_are_translated():
    titles = [title for _, _, title in nav_rail._PAGES]
    states = ["CALLING", "EARLY", "CONNECTING", "CONFIRMED", "DISCONNCTD"]
    missing = [text for text in titles + states if text not in _GERMAN]
    assert missing == []


def test_placeholders_match_between_languages():
    import string

    def fields(text):
        return {name for _, name, _, _ in string.Formatter().parse(text) if name}

    mismatched = [english for english, german in _GERMAN.items() if fields(english) != fields(german)]
    assert mismatched == []


def test_languages_offered_in_settings():
    assert i18n.LANGUAGES == {"en": "English", "de": "Deutsch"}
