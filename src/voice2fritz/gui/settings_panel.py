import os
import tempfile

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from voice2fritz import config
from voice2fritz.audio import populate_and_restore_devices, wav_is_finalized

_LEVEL_POLL_MS = 100
ECHO_RECORD_MS = 3000
ECHO_PLAYBACK_MS = 3300
_ECHO_FINALIZE_POLL_MS = 100
_ECHO_FINALIZE_MAX_POLLS = 20
_ECHO_TEST_PATH = os.path.join(tempfile.gettempdir(), "voice2fritz-echo-test.wav")


class SettingsPanel(QWidget):
    accountSaved = Signal(config.AccountConfig)

    def __init__(self, sip_engine, parent=None):
        super().__init__(parent)
        self.sip_engine = sip_engine

        self.host_edit = QLineEdit()
        self.username_edit = QLineEdit()
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.save_button = QPushButton("Save")
        self.save_button.setObjectName("addButton")
        self.google_priority_checkbox = QCheckBox("Google sync overwrites local contacts with the same name")
        self.google_priority_checkbox.setChecked(config.load_google_sync_overwrites_local())

        existing_account = config.load_config()
        if existing_account is not None:
            self.host_edit.setText(existing_account.host)
            self.username_edit.setText(existing_account.username)

        self.capture_combo = QComboBox()
        self.speaker_combo = QComboBox()

        self.mic_level_bar = QProgressBar()
        self.mic_level_bar.setRange(0, 100)
        self.mic_level_bar.setTextVisible(False)
        self.mic_level_bar.setFixedHeight(8)
        self.mic_level_bar.setToolTip("Live microphone level")

        self.echo_test_button = QPushButton("Test mic && speaker")
        self.echo_test_status = QLabel("Records 3 seconds, then plays them back.")
        self.echo_test_status.setStyleSheet("color: #8a8f98;")
        echo_test_row = QHBoxLayout()
        echo_test_row.addWidget(self.echo_test_button)
        echo_test_row.addWidget(self.echo_test_status, 1)

        form = QFormLayout()
        form.addRow("Host", self.host_edit)
        form.addRow("Username", self.username_edit)
        form.addRow("Password", self.password_edit)
        form.addRow("Mic", self.capture_combo)
        form.addRow("Mic level", self.mic_level_bar)
        form.addRow("Speaker", self.speaker_combo)
        form.addRow("Audio test", echo_test_row)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.google_priority_checkbox)
        layout.addWidget(self.save_button)
        layout.addStretch()

        self.save_button.clicked.connect(self._on_save)

        populate_and_restore_devices(self.sip_engine, self.capture_combo, self.speaker_combo)

        self.capture_combo.currentIndexChanged.connect(self._on_capture_changed)
        self.speaker_combo.currentIndexChanged.connect(self._on_playback_changed)

        self._level_timer = QTimer(self)
        self._level_timer.setInterval(_LEVEL_POLL_MS)
        self._level_timer.timeout.connect(self._update_mic_level)

        self._call_active = False
        self._echo_stage: str | None = None
        self._echo_timer = QTimer(self)
        self._echo_timer.setSingleShot(True)
        self._echo_timer.timeout.connect(self._advance_echo_test)
        self.echo_test_button.clicked.connect(self._start_echo_test)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        # Only hold the mic open while the settings page is on screen.
        self.sip_engine.start_level_monitor()
        self._level_timer.start()

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self._level_timer.stop()
        self.sip_engine.stop_level_monitor()
        self.mic_level_bar.setValue(0)
        self._abort_echo_test()

    def _update_mic_level(self) -> None:
        self.mic_level_bar.setValue(round(self.sip_engine.capture_level() * 100))

    def set_call_active(self, active: bool) -> None:
        # A test during a call would mix its audio into the call.
        self._call_active = active
        if active:
            self._abort_echo_test()
        self.echo_test_button.setEnabled(not active)
        self.echo_test_button.setToolTip("Not available during a call" if active else "")

    def _start_echo_test(self) -> None:
        try:
            self.sip_engine.start_echo_recording(_ECHO_TEST_PATH)
        except Exception as exc:
            self._fail_echo_test(exc)
            return
        self._echo_stage = "recording"
        self.echo_test_button.setEnabled(False)
        self.echo_test_status.setText("Recording - speak now...")
        self._echo_timer.start(ECHO_RECORD_MS)

    def _advance_echo_test(self) -> None:
        if self._echo_stage == "recording":
            # pjsua2 closes the recorder asynchronously; wait for the finished WAV file.
            self.sip_engine.stop_echo_recording()
            self._echo_stage = "finalizing"
            self._echo_finalize_polls = 0
            self.echo_test_status.setText("Preparing playback...")
            self._echo_timer.start(_ECHO_FINALIZE_POLL_MS)
        elif self._echo_stage == "finalizing":
            if not wav_is_finalized(_ECHO_TEST_PATH):
                self._echo_finalize_polls += 1
                if self._echo_finalize_polls >= _ECHO_FINALIZE_MAX_POLLS:
                    self._end_echo_test("Test failed: the recording was not saved.")
                else:
                    self._echo_timer.start(_ECHO_FINALIZE_POLL_MS)
                return
            try:
                self.sip_engine.start_echo_playback(_ECHO_TEST_PATH)
            except Exception as exc:
                self._fail_echo_test(exc)
                return
            self._echo_stage = "playing"
            self.echo_test_status.setText("Playing back...")
            self._echo_timer.start(ECHO_PLAYBACK_MS)
        elif self._echo_stage == "playing":
            self._end_echo_test("Done - did you hear yourself?")

    def _fail_echo_test(self, exc: Exception) -> None:
        reason = getattr(exc, "reason", "") or str(exc)
        self._end_echo_test(f"Test failed: {reason}")

    def _abort_echo_test(self) -> None:
        if self._echo_stage is not None:
            self._end_echo_test("Test cancelled.")

    def _end_echo_test(self, status: str) -> None:
        self._echo_timer.stop()
        self._echo_stage = None
        self.sip_engine.stop_echo_recording()
        self.sip_engine.stop_echo_playback()
        try:
            os.remove(_ECHO_TEST_PATH)
        except OSError:
            pass
        self.echo_test_status.setText(status)
        self.echo_test_button.setEnabled(not self._call_active)

    def _on_save(self) -> None:
        cfg = config.AccountConfig(
            host=self.host_edit.text(),
            username=self.username_edit.text(),
        )
        config.save_config(cfg)
        if self.password_edit.text():
            config.set_password(cfg.username, self.password_edit.text())
        config.save_google_sync_overwrites_local(self.google_priority_checkbox.isChecked())
        self.accountSaved.emit(cfg)

    def _on_capture_changed(self, index: int) -> None:
        if index >= 0:
            self.sip_engine.select_capture_device(self.capture_combo.itemData(index))
            self._save_device_selection()

    def _on_playback_changed(self, index: int) -> None:
        if index >= 0:
            self.sip_engine.select_playback_device(self.speaker_combo.itemData(index))
            self._save_device_selection()

    def _save_device_selection(self) -> None:
        capture_name = self.capture_combo.currentText() or None
        playback_name = self.speaker_combo.currentText() or None
        config.save_device_selection(capture_name, playback_name)
