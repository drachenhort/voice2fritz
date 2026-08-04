import wave

from voice2fritz import ringtone


def test_synthesize_ringtone_writes_valid_wav_file(tmp_path):
    target = tmp_path / "ring.wav"

    result = ringtone._synthesize_ringtone(target)

    assert result == target
    assert target.exists()
    with wave.open(str(target), "rb") as wav_file:
        assert wav_file.getnchannels() == 1
        assert wav_file.getsampwidth() == 2
        assert wav_file.getnframes() > 0


def test_synthesize_ringtone_is_idempotent(tmp_path):
    target = tmp_path / "ring.wav"

    ringtone._synthesize_ringtone(target)
    first_mtime = target.stat().st_mtime_ns
    ringtone._synthesize_ringtone(target)

    assert target.stat().st_mtime_ns == first_mtime


def test_system_ringtone_path_returns_existing_file(monkeypatch, tmp_path):
    theme_file = tmp_path / "phone-incoming-call.oga"
    theme_file.write_bytes(b"fake-audio")
    monkeypatch.setattr(ringtone, "_THEME_PATHS", [theme_file])

    assert ringtone._system_ringtone_path() == theme_file


def test_system_ringtone_path_returns_none_when_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(ringtone, "_THEME_PATHS", [tmp_path / "missing.oga"])

    assert ringtone._system_ringtone_path() is None


def test_play_and_stop_ringtone_do_not_raise(qtbot, monkeypatch, tmp_path):
    monkeypatch.setattr(ringtone, "DEFAULT_RINGTONE_CACHE_PATH", tmp_path / "ring.wav")
    monkeypatch.setattr(ringtone, "_THEME_PATHS", [tmp_path / "missing.oga"])

    ringtone.play_ringtone()
    ringtone.stop_ringtone()


def test_play_ringtone_never_raises_even_if_synthesis_fails(monkeypatch):
    def _boom(path=None):
        raise OSError("disk full")

    monkeypatch.setattr(ringtone, "_synthesize_ringtone", _boom)
    monkeypatch.setattr(ringtone, "_THEME_PATHS", [])

    ringtone.play_ringtone()
    ringtone.stop_ringtone()
