from voice2fritz.sip_engine import SipEngine


class _FakeCallInfo:
    def __init__(self, remote_uri):
        self.remoteUri = remote_uri


class _FakeCall:
    def __init__(self, remote_uri):
        self._info = _FakeCallInfo(remote_uri)

    def getInfo(self):
        return self._info


def test_get_remote_number_extracts_from_uri_with_display_name():
    engine = SipEngine()
    call = _FakeCall('"Anna Schmidt" <sip:01761234567@fritz.box>')

    assert engine.get_remote_number(call) == "01761234567"


def test_get_remote_number_extracts_from_bare_uri():
    engine = SipEngine()
    call = _FakeCall("sip:01761234567@fritz.box")

    assert engine.get_remote_number(call) == "01761234567"


def test_get_remote_number_returns_empty_string_for_unexpected_format():
    engine = SipEngine()
    call = _FakeCall("not a sip uri at all")

    assert engine.get_remote_number(call) == ""
