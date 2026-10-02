from voice2fritz import sip_engine


class _FakeAccount:
    instances = []

    def __init__(self, engine):
        self.engine = engine
        self.config = None
        self.shut_down = False
        _FakeAccount.instances.append(self)

    def create(self, acc_cfg):
        self.config = acc_cfg

    def shutdown(self):
        self.shut_down = True


def test_reregister_shuts_down_previous_account(monkeypatch):
    _FakeAccount.instances = []
    monkeypatch.setattr(sip_engine, "SipAccount", _FakeAccount)
    engine = sip_engine.SipEngine()
    engine._ep = object()  # register() only checks that start() ran

    engine.register("fritz.box", "user", "first")
    engine.register("fritz.box", "user", "second")

    first, second = _FakeAccount.instances
    assert first.shut_down is True
    assert second.shut_down is False
    assert second.config.sipConfig.authCreds[0].data == "second"
    assert engine.account_label == "user@fritz.box"


def test_rejected_account_config_raises_registration_error_with_reason(monkeypatch):
    import pjsua2 as pj
    import pytest

    class _RejectingAccount(_FakeAccount):
        def create(self, acc_cfg):
            error = pj.Error()
            error.reason = "Invalid URI (PJSIP_EINVALIDURI)"
            raise error

    monkeypatch.setattr(sip_engine, "SipAccount", _RejectingAccount)
    engine = sip_engine.SipEngine()
    engine._ep = object()

    with pytest.raises(sip_engine.RegistrationError, match="Invalid URI"):
        engine.register("bad host", "user", "pw")
    assert engine._account is None
