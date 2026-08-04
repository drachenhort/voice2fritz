from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

from voice2fritz import contacts as contacts_module


class ContactsDialog(QDialog):
    contactSelected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Contacts")

        self.contact_list = QListWidget()
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Name")
        self.number_edit = QLineEdit()
        self.number_edit.setPlaceholderText("Number")
        self.add_button = QPushButton("Add")
        self.delete_button = QPushButton("Delete")
        self.select_button = QPushButton("Select")

        add_row = QHBoxLayout()
        add_row.addWidget(self.name_edit)
        add_row.addWidget(self.number_edit)
        add_row.addWidget(self.add_button)

        button_row = QHBoxLayout()
        button_row.addWidget(self.delete_button)
        button_row.addWidget(self.select_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.contact_list)
        layout.addLayout(add_row)
        layout.addLayout(button_row)

        self.contact_list.itemDoubleClicked.connect(self._on_item_activated)
        self.add_button.clicked.connect(self._on_add_clicked)
        self.delete_button.clicked.connect(self._on_delete_clicked)
        self.select_button.clicked.connect(self._on_select_clicked)

        self._reload_list()

    def _reload_list(self) -> None:
        self.contact_list.clear()
        for contact in contacts_module.load_contacts():
            self.contact_list.addItem(QListWidgetItem(f"{contact.name} — {contact.number}"))

    def _on_add_clicked(self) -> None:
        name = self.name_edit.text().strip()
        number = self.number_edit.text().strip()
        if name and number:
            contacts_module.add_contact(name, number)
            self.name_edit.clear()
            self.number_edit.clear()
            self._reload_list()

    def _on_delete_clicked(self) -> None:
        row = self.contact_list.currentRow()
        if row >= 0:
            contacts_module.delete_contact(row)
            self._reload_list()

    def _on_item_activated(self, item: QListWidgetItem) -> None:
        self._select_row(self.contact_list.row(item))

    def _on_select_clicked(self) -> None:
        row = self.contact_list.currentRow()
        if row >= 0:
            self._select_row(row)

    def _select_row(self, row: int) -> None:
        contact = contacts_module.load_contacts()[row]
        self.contactSelected.emit(contact.number)
        self.accept()
