from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDialog, QListWidget, QListWidgetItem, QMessageBox, QPushButton, QVBoxLayout

from voice2fritz import config, tr064


class ContactsDialog(QDialog):
    contactSelected = Signal(str)

    def __init__(self, host: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Contacts")
        self.host = host
        self._numbers_by_row: list[str] = []

        self.contact_list = QListWidget()
        self.select_button = QPushButton("Select")

        layout = QVBoxLayout(self)
        layout.addWidget(self.contact_list)
        layout.addWidget(self.select_button)

        self.contact_list.itemDoubleClicked.connect(self._on_item_activated)
        self.select_button.clicked.connect(self._on_select_clicked)

        self._load_contacts()

    def _load_contacts(self) -> None:
        username = config.load_fritzbox_username()
        if username is None:
            QMessageBox.warning(self, "Contacts", "FritzBox credentials not configured — set them in Settings.")
            return

        password = config.get_fritzbox_password(username) or ""
        try:
            contacts = tr064.get_phonebook(self.host, username, password)
        except Exception as exc:
            QMessageBox.warning(self, "Contacts", f"Could not load contacts: {exc}")
            return

        for contact in contacts:
            for number in contact.numbers:
                self.contact_list.addItem(QListWidgetItem(f"{contact.name} — {number}"))
                self._numbers_by_row.append(number)

    def _on_item_activated(self, item: QListWidgetItem) -> None:
        self._select_row(self.contact_list.row(item))

    def _on_select_clicked(self) -> None:
        row = self.contact_list.currentRow()
        if row >= 0:
            self._select_row(row)

    def _select_row(self, row: int) -> None:
        self.contactSelected.emit(self._numbers_by_row[row])
        self.accept()
