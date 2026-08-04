from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDialog, QVBoxLayout

from voice2fritz.gui.contacts_panel import ContactsPanel


class ContactsDialog(QDialog):
    contactSelected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Contacts")
        self.resize(480, 480)

        self.panel = ContactsPanel()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.panel)

        self.panel.contactSelected.connect(self._on_contact_selected)

        self.contact_table = self.panel.contact_table
        self.sort_combo = self.panel.sort_combo
        self.name_edit = self.panel.name_edit
        self.type_edit = self.panel.type_edit
        self.number_edit = self.panel.number_edit
        self.add_button = self.panel.add_button
        self.delete_button = self.panel.delete_button
        self.select_button = self.panel.select_button
        self.sync_button = self.panel.sync_button

    def _on_item_activated(self, item) -> None:
        self.panel._on_item_activated(item)

    def _on_contact_selected(self, number: str) -> None:
        self.contactSelected.emit(number)
        self.accept()
