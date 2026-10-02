import socket

from voice2fritz import sip_engine
from voice2fritz.sip_engine import local_address_toward


def test_local_address_toward_loopback_is_loopback():
    assert local_address_toward("127.0.0.1") == "127.0.0.1"


def test_local_address_toward_invalid_host_is_none():
    assert local_address_toward("256.256.256.256") is None


class _CapturingAccount:
    def __init__(self, engine):
        self.config = None

    def create(self, acc_cfg):
        self.config = acc_cfg

    def shutdown(self):
        pass


def test_register_binds_media_to_address_toward_registrar(monkeypatch):
    monkeypatch.setattr(sip_engine, "SipAccount", _CapturingAccount)
    monkeypatch.setattr(sip_engine, "local_address_toward", lambda host, port=5060: "192.168.178.26")
    engine = sip_engine.SipEngine()
    engine._ep = object()

    engine.register("192.168.178.1", "user", "pw")

    assert engine._account.config.mediaConfig.transportConfig.boundAddress == "192.168.178.26"


def test_register_leaves_media_address_default_when_unknown(monkeypatch):
    monkeypatch.setattr(sip_engine, "SipAccount", _CapturingAccount)
    monkeypatch.setattr(sip_engine, "local_address_toward", lambda host, port=5060: None)
    engine = sip_engine.SipEngine()
    engine._ep = object()

    engine.register("fritz.box", "user", "pw")

    assert engine._account.config.mediaConfig.transportConfig.boundAddress == ""
