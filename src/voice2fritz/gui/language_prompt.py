from PySide6.QtWidgets import QMessageBox

from voice2fritz.i18n import LANGUAGES, current_language, set_language, tr


def ask_to_switch_language(offered: str, parent=None) -> bool:
    """Ask, in the offered language, whether to switch to it. True if the user agrees."""
    previous = current_language()
    set_language(offered)
    try:
        box = QMessageBox(parent)
        box.setIcon(QMessageBox.Icon.Question)
        box.setWindowTitle(tr("Language"))
        offered_name, previous_name = LANGUAGES[offered], LANGUAGES[previous]
        box.setText(tr("Your system language is {language}. Switch voice2fritz to {language}?", language=offered_name))
        box.setInformativeText(tr("You can change this later in Settings."))
        switch_button = box.addButton(
            tr("Switch to {language}", language=offered_name), QMessageBox.ButtonRole.AcceptRole
        )
        box.addButton(tr("Keep {language}", language=previous_name), QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(switch_button)
    finally:
        set_language(previous)
    box.exec()
    return box.clickedButton() is switch_button
