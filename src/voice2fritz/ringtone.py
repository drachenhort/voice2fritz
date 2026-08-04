import math
import struct
import wave
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QSoundEffect

DEFAULT_RINGTONE_CACHE_PATH = Path.home() / ".cache" / "voice2fritz" / "ringtone.wav"

_THEME_PATHS = [
    Path("/usr/share/sounds/freedesktop/stereo/phone-incoming-call.oga"),
]

_effect: QSoundEffect | None = None


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


def play_ringtone() -> None:
    global _effect
    try:
        source_path = _system_ringtone_path() or _synthesize_ringtone()
        effect = QSoundEffect()
        effect.setSource(QUrl.fromLocalFile(str(source_path)))
        effect.setLoopCount(QSoundEffect.Infinite)
        effect.play()
        _effect = effect
    except Exception:
        _effect = None


def stop_ringtone() -> None:
    global _effect
    try:
        if _effect is not None:
            _effect.stop()
    except Exception:
        pass
    finally:
        _effect = None
