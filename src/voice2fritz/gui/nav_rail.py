from PySide6.QtCore import Signal
from PySide6.QtWidgets import QButtonGroup, QPushButton, QVBoxLayout, QWidget

_PAGES = [
    ("dialpad", "\N{BLACK TELEPHONE}"),
    ("contacts", "\N{BUST IN SILHOUETTE}"),
    ("call_log", "\N{ALARM CLOCK}"),
    ("settings", "\N{GEAR}"),
]


class NavRail(QWidget):
    pageSelected = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("navRail")

        self.buttons: dict[str, QPushButton] = {}
        group = QButtonGroup(self)
        group.setExclusive(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 12, 8, 12)
        layout.setSpacing(6)

        for index, (name, glyph) in enumerate(_PAGES):
            button = QPushButton(glyph)
            button.setObjectName("railButton")
            button.setCheckable(True)
            button.setToolTip(name.replace("_", " ").title())
            button.clicked.connect(lambda checked=False, i=index: self.pageSelected.emit(i))
            group.addButton(button)
            layout.addWidget(button)
            self.buttons[name] = button

        layout.addStretch()
        self.buttons["dialpad"].setChecked(True)
