import pjsua2 as pj

from voice2fritz.sip_engine import SipEngine


class _FakeAnswerCall:
    def __init__(self):
        self.answered_with_status = None

    def answer(self, prm):
        self.answered_with_status = prm.statusCode


def test_decline_answers_incoming_call_with_decline_status_code():
    engine = SipEngine()
    call = _FakeAnswerCall()

    engine.decline(call)

    assert call.answered_with_status == pj.PJSIP_SC_DECLINE
