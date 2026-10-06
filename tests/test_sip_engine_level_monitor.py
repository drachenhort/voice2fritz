from voice2fritz import sip_engine


class _FakeCaptureMedia:
    def __init__(self):
        self.listeners = []

    def startTransmit(self, port):
        self.listeners.append(port)

    def stopTransmit(self, port):
        self.listeners.remove(port)


class _FakeEndpoint:
    def __init__(self):
        self.capture = _FakeCaptureMedia()

    def audDevManager(self):
        return self

    def getCaptureDevMedia(self):
        return self.capture

    def libDestroy(self):
        pass


class _FakeMeterPort:
    def createPort(self, name, fmt):
        pass


def _engine(monkeypatch):
    monkeypatch.setattr(sip_engine, "_LevelMeterPort", _FakeMeterPort)
    engine = sip_engine.SipEngine()
    engine._ep = _FakeEndpoint()
    return engine


def test_level_monitor_runs_until_the_last_user_stops(monkeypatch):
    engine = _engine(monkeypatch)
    capture = engine._ep.capture

    engine.start_level_monitor()  # Settings on screen
    engine.start_level_monitor()  # wizard audio page on screen
    engine.stop_level_monitor()  # Settings hidden

    assert len(capture.listeners) == 1

    engine.stop_level_monitor()
    assert capture.listeners == []


def test_stopping_the_engine_releases_the_monitor_for_all_users(monkeypatch):
    engine = _engine(monkeypatch)
    capture = engine._ep.capture
    engine.start_level_monitor()
    engine.start_level_monitor()

    engine.stop()

    assert capture.listeners == []
