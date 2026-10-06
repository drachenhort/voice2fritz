import os
import tempfile

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QWidget,
)

from voice2fritz import config
from voice2fritz.audio import populate_and_restore_devices, wav_is_finalized, wav_peak
from voice2fritz.i18n import tr

_LEVEL_POLL_MS = 100
ECHO_RECORD_MS = 3000
ECHO_PLAYBACK_MS = 3300
_ECHO_FINALIZE_POLL_MS = 100
_ECHO_FINALIZE_MAX_POLLS = 20
# A muted mic records a peak of about 0-15; normal speech peaks in the thousands.
_SILENCE_PEAK_THRESHOLD = 200
_ECHO_TEST_PATH = os.path.join(tempfile.gettempdir(), "voice2fritz-echo-test.wav")


class AudioSetupWidget(QWidget):
    """Mic and speaker choice, the live mic level and the record-and-play-back echo test."""

    def __init__(self, sip_engine, parent=None):
        super().__init__(parent)
        self.sip_engine = sip_engine

        self.capture_combo = QComboBox()
        self.speaker_combo = QComboBox()

        self.mic_level_bar = QProgressBar()
        self.mic_level_bar.setRange(0, 100)
        self.mic_level_bar.setTextVisible(False)
        self.mic_level_bar.setFixedHeight(8)
        self.mic_level_bar.setToolTip(tr("Live microphone level"))

        self.echo_test_button = QPushButton(tr("Test mic && speaker"))
        self.echo_test_status = QLabel(tr("Records 3 seconds, then plays them back."))
        self.echo_test_status.setStyleSheet("color: #8a8f98;")
        echo_test_row = QHBoxLayout()
        echo_test_row.addWidget(self.echo_test_button)
        echo_test_row.addWidget(self.echo_test_status, 1)

        form = QFormLayout(self)
        form.setContentsMargins(0, 0, 0, 0)
        form.addRow(tr("Mic"), self.capture_combo)
        form.addRow(tr("Mic level"), self.mic_level_bar)
        form.addRow(tr("Speaker"), self.speaker_combo)
        form.addRow(tr("Audio test"), echo_test_row)

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
        # Only hold the mic open while the widget is on screen.
        self.sip_engine.start_level_monitor()
        self._level_timer.start()

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self._level_timer.stop()
        self.sip_engine.stop_level_monitor()
        self.mic_level_bar.setValue(0)
        self._abort_echo_test()

    def resume_level_monitor(self) -> None:
        """Restart the level meter if on screen; another widget may have stopped the shared monitor."""
        if self.isVisible():
            self.sip_engine.start_level_monitor()
            self._level_timer.start()

    def show_saved_devices(self) -> None:
        """Select the saved devices in the combos, e.g. after another window changed them."""
        capture_name, playback_name = config.load_device_selection()
        for combo, name in ((self.capture_combo, capture_name), (self.speaker_combo, playback_name)):
            index = combo.findText(name) if name is not None else -1
            if index >= 0:
                # The device is already selected in the engine and saved; don't do it again.
                combo.blockSignals(True)
                combo.setCurrentIndex(index)
                combo.blockSignals(False)

    def _update_mic_level(self) -> None:
        self.mic_level_bar.setValue(round(self.sip_engine.capture_level() * 100))

    def set_call_active(self, active: bool) -> None:
        # A test during a call would mix its audio into the call.
        self._call_active = active
        if active:
            self._abort_echo_test()
        self.echo_test_button.setEnabled(not active)
        self.echo_test_button.setToolTip(tr("Not available during a call") if active else "")

    def _start_echo_test(self) -> None:
        try:
            self.sip_engine.start_echo_recording(_ECHO_TEST_PATH)
        except Exception as exc:
            self._fail_echo_test(exc)
            return
        self._echo_stage = "recording"
        self.echo_test_button.setEnabled(False)
        self.echo_test_status.setText(tr("Recording - speak now..."))
        self._echo_timer.start(ECHO_RECORD_MS)

    def _advance_echo_test(self) -> None:
        if self._echo_stage == "recording":
            # pjsua2 closes the recorder asynchronously; wait for the finished WAV file.
            self.sip_engine.stop_echo_recording()
            self._echo_stage = "finalizing"
            self._echo_finalize_polls = 0
            self.echo_test_status.setText(tr("Preparing playback..."))
            self._echo_timer.start(_ECHO_FINALIZE_POLL_MS)
        elif self._echo_stage == "finalizing":
            if not wav_is_finalized(_ECHO_TEST_PATH):
                self._echo_finalize_polls += 1
                if self._echo_finalize_polls >= _ECHO_FINALIZE_MAX_POLLS:
                    self._end_echo_test(tr("Test failed: the recording was not saved."))
                else:
                    self._echo_timer.start(_ECHO_FINALIZE_POLL_MS)
                return
            if wav_peak(_ECHO_TEST_PATH) < _SILENCE_PEAK_THRESHOLD:
                self._end_echo_test(tr("Recorded only silence - is the mic muted?"))
                return
            try:
                self.sip_engine.start_echo_playback(_ECHO_TEST_PATH)
            except Exception as exc:
                self._fail_echo_test(exc)
                return
            self._echo_stage = "playing"
            self.echo_test_status.setText(tr("Playing back..."))
            self._echo_timer.start(ECHO_PLAYBACK_MS)
        elif self._echo_stage == "playing":
            self._end_echo_test(tr("Done - did you hear yourself?"))

    def _fail_echo_test(self, exc: Exception) -> None:
        reason = getattr(exc, "reason", "") or str(exc)
        self._end_echo_test(tr("Test failed: {reason}", reason=reason))

    def _abort_echo_test(self) -> None:
        if self._echo_stage is not None:
            self._end_echo_test(tr("Test cancelled."))

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
