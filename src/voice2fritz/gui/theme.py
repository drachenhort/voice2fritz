DARK_STYLESHEET = """
QWidget {
    background-color: #1c1e26;
    color: #dddddd;
    font-size: 13px;
}

QLineEdit, QComboBox {
    background-color: #12141a;
    border: 1px solid #333333;
    border-radius: 4px;
    padding: 6px;
    color: #ffffff;
}

QPushButton {
    background-color: #2a2d38;
    border: 1px solid #383c48;
    border-radius: 6px;
    padding: 8px;
    color: #eeeeee;
}

QPushButton:hover {
    background-color: #383c48;
}

QPushButton:disabled {
    color: #666666;
}

QPushButton#callButton {
    background-color: #2fa84f;
    color: #ffffff;
    font-weight: bold;
}

QPushButton#callButton:hover {
    background-color: #36bd59;
}

QPushButton:checked {
    background-color: #a83b2f;
}

QPushButton[dtmfMode="true"] {
    border: 2px solid #4a9eff;
}

QPushButton#addButton {
    background-color: #2fa84f;
    color: #ffffff;
    font-weight: bold;
}

QPushButton#addButton:hover {
    background-color: #36bd59;
}

QPushButton#deleteButton {
    background-color: #a83b2f;
    color: #ffffff;
}

QPushButton#deleteButton:hover {
    background-color: #bf4536;
}

QLabel {
    color: #dddddd;
}

QLabel#sectionLabel {
    color: #8a8f98;
    font-size: 11px;
    text-transform: uppercase;
}

QListWidget {
    background-color: #12141a;
    border: 1px solid #333333;
    border-radius: 4px;
    outline: none;
}

QListWidget::item {
    padding: 6px;
}

QListWidget::item:selected {
    background-color: #2a4d6e;
    color: #ffffff;
}

QTableWidget {
    background-color: #12141a;
    border: 1px solid #333333;
    border-radius: 4px;
    gridline-color: #262a33;
    outline: none;
}

QTableWidget::item {
    padding: 6px;
}

QTableWidget::item:selected {
    background-color: #2a4d6e;
    color: #ffffff;
}

QHeaderView::section {
    background-color: #1c1e26;
    color: #8a8f98;
    padding: 6px;
    border: none;
    border-bottom: 1px solid #333333;
    font-size: 11px;
    text-transform: uppercase;
}
"""
