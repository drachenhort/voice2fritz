from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from voice2fritz import config, contacts as contacts_module
from voice2fritz import google_contacts


class ContactsDialog(QDialog):
    contactSelected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Contacts")
        self.resize(480, 480)
        self._displayed_contacts: list[contacts_module.Contact] = []

        self.contact_table = QTableWidget(0, 3)
        self.contact_table.setHorizontalHeaderLabels(["Name", "Type", "Number"])
        self.contact_table.verticalHeader().setVisible(False)
        self.contact_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.contact_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.contact_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        header = self.contact_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)

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
        self.type_edit = QLineEdit()
        self.type_edit.setPlaceholderText("Type (optional)")
        self.number_edit = QLineEdit()
        self.number_edit.setPlaceholderText("Number")
        self.add_button = QPushButton("Add")
        self.add_button.setObjectName("addButton")

        add_row = QHBoxLayout()
        add_row.addWidget(self.name_edit)
        add_row.addWidget(self.type_edit)
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
        layout.addWidget(self.contact_table)
        layout.addWidget(add_label)
        layout.addLayout(add_row)
        layout.addLayout(button_row)

        self.contact_table.itemDoubleClicked.connect(self._on_item_activated)
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
        self.contact_table.setRowCount(len(self._displayed_contacts))
        for row, contact in enumerate(self._displayed_contacts):
            self.contact_table.setItem(row, 0, QTableWidgetItem(contact.name))
            self.contact_table.setItem(row, 1, QTableWidgetItem(contact.number_type))
            self.contact_table.setItem(row, 2, QTableWidgetItem(contact.number))

    def _on_sort_changed(self, index: int) -> None:
        config.save_contacts_sort_order(self.sort_combo.currentData())
        self._reload_list()

    def _on_add_clicked(self) -> None:
        name = self.name_edit.text().strip()
        number = self.number_edit.text().strip()
        number_type = self.type_edit.text().strip()
        if name and number:
            contacts_module.add_contact(name, number, number_type=number_type)
            self.name_edit.clear()
            self.number_edit.clear()
            self.type_edit.clear()
            self._reload_list()

    def _on_delete_clicked(self) -> None:
        row = self.contact_table.currentRow()
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

    def _on_item_activated(self, item: QTableWidgetItem) -> None:
        self._select_row(item.row())

    def _on_select_clicked(self) -> None:
        row = self.contact_table.currentRow()
        if row >= 0:
            self._select_row(row)

    def _select_row(self, row: int) -> None:
        contact = self._displayed_contacts[row]
        self.contactSelected.emit(contact.number)
        self.accept()
