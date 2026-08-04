from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from voice2fritz import config, contacts as contacts_module
from voice2fritz import google_contacts


class ContactsDialog(QDialog):
    contactSelected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Contacts")
        self.resize(420, 480)
        self._displayed_contacts: list[contacts_module.Contact] = []

        self.contact_list = QListWidget()

        sort_label = QLabel("Sort by:")
        self.sort_combo = QComboBox()
        self.sort_combo.addItem("Name", "name")
        self.sort_combo.addItem("Number", "number")
        current_sort = config.load_contacts_sort_order()
        self.sort_combo.setCurrentIndex(self.sort_combo.findData(current_sort))

        sort_row = QHBoxLayout()
        sort_row.addWidget(sort_label)
        sort_row.addWidget(self.sort_combo)
        sort_row.addStretch()

        add_label = QLabel("Add contact")
        add_label.setObjectName("sectionLabel")

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Name")
        self.number_edit = QLineEdit()
        self.number_edit.setPlaceholderText("Number")
        self.add_button = QPushButton("Add")
        self.add_button.setObjectName("addButton")

        add_row = QHBoxLayout()
        add_row.addWidget(self.name_edit)
        add_row.addWidget(self.number_edit)
        add_row.addWidget(self.add_button)

        self.delete_button = QPushButton("Delete")
        self.delete_button.setObjectName("deleteButton")
        self.select_button = QPushButton("Select")
        self.sync_button = QPushButton("Sync Google")

        button_row = QHBoxLayout()
        button_row.addWidget(self.delete_button)
        button_row.addWidget(self.select_button)
        button_row.addStretch()
        button_row.addWidget(self.sync_button)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.addLayout(sort_row)
        layout.addWidget(self.contact_list)
        layout.addWidget(add_label)
        layout.addLayout(add_row)
        layout.addLayout(button_row)

        self.contact_list.itemDoubleClicked.connect(self._on_item_activated)
        self.sort_combo.currentIndexChanged.connect(self._on_sort_changed)
        self.add_button.clicked.connect(self._on_add_clicked)
        self.delete_button.clicked.connect(self._on_delete_clicked)
        self.select_button.clicked.connect(self._on_select_clicked)
        self.sync_button.clicked.connect(self._on_sync_clicked)

        self._reload_list()

    def _sort_key(self, contact: contacts_module.Contact):
        field = self.sort_combo.currentData()
        if field == "number":
            return contact.number
        return contact.name.lower()

    def _reload_list(self) -> None:
        self._displayed_contacts = sorted(contacts_module.load_contacts(), key=self._sort_key)
        self.contact_list.clear()
        for contact in self._displayed_contacts:
            self.contact_list.addItem(QListWidgetItem(f"{contact.name} — {contact.number}"))

    def _on_sort_changed(self, index: int) -> None:
        config.save_contacts_sort_order(self.sort_combo.currentData())
        self._reload_list()

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
            contacts_module.delete_contact_by_value(self._displayed_contacts[row])
            self._reload_list()

    def _on_sync_clicked(self) -> None:
        try:
            count = google_contacts.sync_google_contacts()
        except Exception as exc:
            QMessageBox.warning(self, "Contacts", f"Could not sync Google contacts: {exc}")
            return
        self._reload_list()
        QMessageBox.information(self, "Contacts", f"{count} contact(s) added or updated.")

    def _on_item_activated(self, item: QListWidgetItem) -> None:
        self._select_row(self.contact_list.row(item))

    def _on_select_clicked(self) -> None:
        row = self.contact_list.currentRow()
        if row >= 0:
            self._select_row(row)

    def _select_row(self, row: int) -> None:
        contact = self._displayed_contacts[row]
        self.contactSelected.emit(contact.number)
        self.accept()
