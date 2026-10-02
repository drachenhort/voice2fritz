import pjsua2 as pj
import pytest

from voice2fritz.sip_engine import should_play_ringback


@pytest.mark.parametrize("state", [pj.PJSIP_INV_STATE_CALLING, pj.PJSIP_INV_STATE_EARLY])
def test_ringback_plays_while_outgoing_call_is_being_set_up(state):
    assert should_play_ringback(pj.PJSIP_ROLE_UAC, state) is True


@pytest.mark.parametrize(
    "state",
    [pj.PJSIP_INV_STATE_CONNECTING, pj.PJSIP_INV_STATE_CONFIRMED, pj.PJSIP_INV_STATE_DISCONNECTED],
)
def test_ringback_stops_once_answered_or_ended(state):
    assert should_play_ringback(pj.PJSIP_ROLE_UAC, state) is False


def test_no_ringback_for_incoming_calls():
    assert should_play_ringback(pj.PJSIP_ROLE_UAS, pj.PJSIP_INV_STATE_EARLY) is False
