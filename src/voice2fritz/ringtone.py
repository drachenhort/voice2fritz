import math
import struct
import wave
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

DEFAULT_RINGTONE_CACHE_PATH = Path.home() / ".cache" / "voice2fritz" / "ringtone.wav"

_THEME_PATHS = [
    Path("/usr/share/sounds/freedesktop/stereo/phone-incoming-call.oga"),
]

_player: QMediaPlayer | None = None
_audio_output: QAudioOutput | None = None
_fallback_attempted = False


def _system_ringtone_path() -> Path | None:
    for path in _THEME_PATHS:
        if path.exists():
            return path
    return None


def _synthesize_ringtone(path: Path | None = None) -> Path:
    if path is None:
        path = DEFAULT_RINGTONE_CACHE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return path

    sample_rate = 44100
    frequencies = (950, 1400)
    tone_seconds = 0.4
    silence_seconds = 0.2

    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)

        for frequency in frequencies:
            for i in range(int(sample_rate * tone_seconds)):
                value = int(32767 * 0.5 * math.sin(2 * math.pi * frequency * i / sample_rate))
                wav_file.writeframesraw(struct.pack("<h", value))
        for i in range(int(sample_rate * silence_seconds)):
            wav_file.writeframesraw(struct.pack("<h", 0))

    return path


def _on_error_occurred(*_args) -> None:
    global _fallback_attempted
    if _fallback_attempted:
        return
    _fallback_attempted = True
    try:
        fallback_path = _synthesize_ringtone()
        _start_playback(fallback_path)
    except Exception:
        pass


def _start_playback(source_path: Path) -> None:
    global _player, _audio_output
    player = QMediaPlayer()
    audio_output = QAudioOutput()
    player.setAudioOutput(audio_output)
    player.errorOccurred.connect(_on_error_occurred)
    player.setSource(QUrl.fromLocalFile(str(source_path)))
    player.setLoops(QMediaPlayer.Loops.Infinite)
    player.play()
    _player = player
    _audio_output = audio_output


def play_ringtone() -> None:
    global _fallback_attempted
    _fallback_attempted = False
    try:
        source_path = _system_ringtone_path() or _synthesize_ringtone()
        _start_playback(source_path)
    except Exception:
        global _player, _audio_output
        _player = None
        _audio_output = None


def stop_ringtone() -> None:
    global _player, _audio_output
    try:
        if _player is not None:
            _player.stop()
    except Exception:
        pass
    finally:
        _player = None
        _audio_output = None
