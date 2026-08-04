from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from voice2fritz.audio import input_devices, output_devices


class MainWindow(QMainWindow):
    def __init__(self, sip_engine, parent=None):
        super().__init__(parent)
        self.setWindowTitle("voice2fritz")
        self.sip_engine = sip_engine
        self._active_call = None

        self.number_edit = QLineEdit()
        self.call_button = QPushButton("Call")
        self.hangup_button = QPushButton("Hang up")
        self.hangup_button.setEnabled(False)
        self.mute_button = QPushButton("Mute")
        self.mute_button.setCheckable(True)
        self.mute_button.setEnabled(False)
        self.capture_combo = QComboBox()
        self.playback_combo = QComboBox()
        self.status_label = QLabel("Not registered")

        call_row = QHBoxLayout()
        call_row.addWidget(self.number_edit)
        call_row.addWidget(self.call_button)
        call_row.addWidget(self.hangup_button)
        call_row.addWidget(self.mute_button)

        device_row = QHBoxLayout()
        device_row.addWidget(QLabel("Mic:"))
        device_row.addWidget(self.capture_combo)
        device_row.addWidget(QLabel("Speaker:"))
        device_row.addWidget(self.playback_combo)

        layout = QVBoxLayout()
        layout.addLayout(call_row)
        layout.addLayout(device_row)
        layout.addWidget(self.status_label)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self._populate_devices()
        self._connect_signals()

    def _populate_devices(self) -> None:
        devices = self.sip_engine.list_devices()
        for device in input_devices(devices):
            self.capture_combo.addItem(device.name, device.id)
        for device in output_devices(devices):
            self.playback_combo.addItem(device.name, device.id)

    def _connect_signals(self) -> None:
        self.call_button.clicked.connect(self._on_call_clicked)
        self.hangup_button.clicked.connect(self._on_hangup_clicked)
        self.mute_button.clicked.connect(self._on_mute_clicked)
        self.capture_combo.currentIndexChanged.connect(self._on_capture_changed)
        self.playback_combo.currentIndexChanged.connect(self._on_playback_changed)
        self.sip_engine.registrationStateChanged.connect(self.status_label.setText)
        self.sip_engine.callStateChanged.connect(self.status_label.setText)
        self.sip_engine.callEnded.connect(self._on_call_ended)

    def _on_call_clicked(self) -> None:
        self._active_call = self.sip_engine.make_call(self.number_edit.text())
        self.hangup_button.setEnabled(True)
        self.mute_button.setEnabled(True)

    def _on_hangup_clicked(self) -> None:
        if self._active_call is not None:
            self.sip_engine.hangup(self._active_call)
        self._on_call_ended()

    def _on_mute_clicked(self) -> None:
        if self._active_call is not None:
            self.sip_engine.set_mute(self._active_call, self.mute_button.isChecked())

    def _on_call_ended(self) -> None:
        self._active_call = None
        self.hangup_button.setEnabled(False)
        self.mute_button.setEnabled(False)
        self.mute_button.setChecked(False)

    def _on_capture_changed(self, index: int) -> None:
        if index >= 0:
            self.sip_engine.select_capture_device(self.capture_combo.itemData(index))

    def _on_playback_changed(self, index: int) -> None:
        if index >= 0:
            self.sip_engine.select_playback_device(self.playback_combo.itemData(index))
