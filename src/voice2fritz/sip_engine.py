import pjsua2 as pj
from PySide6.QtCore import QObject, Signal

from voice2fritz.audio import AudioDevice, list_audio_devices


class SipCall(pj.Call):
    def __init__(self, engine: "SipEngine", account: "SipAccount", call_id: int = pj.PJSUA_INVALID_ID):
        pj.Call.__init__(self, account, call_id)
        self.engine = engine

    def onCallState(self, prm):
        info = self.getInfo()
        self.engine.callStateChanged.emit(info.stateText)
        if info.state == pj.PJSIP_INV_STATE_DISCONNECTED:
            self.engine.callEnded.emit()

    def onCallMediaState(self, prm):
        info = self.getInfo()
        for media_info in info.media:
            if media_info.type == pj.PJMEDIA_TYPE_AUDIO and media_info.status == pj.PJSUA_CALL_MEDIA_ACTIVE:
                audio_media = self.getAudioMedia(media_info.index)
                dev_manager = pj.Endpoint.instance().audDevManager()
                dev_manager.getCaptureDevMedia().startTransmit(audio_media)
                audio_media.startTransmit(dev_manager.getPlaybackDevMedia())


class SipAccount(pj.Account):
    def __init__(self, engine: "SipEngine"):
        pj.Account.__init__(self)
        self.engine = engine

    def onRegState(self, prm):
        info = self.getInfo()
        self.engine.registrationStateChanged.emit(info.regStatusText)

    def onIncomingCall(self, prm):
        call = SipCall(self.engine, self, call_id=prm.callId)
        self.engine.incomingCall.emit(call)


class SipEngine(QObject):
    registrationStateChanged = Signal(str)
    incomingCall = Signal(object)
    callStateChanged = Signal(str)
    callEnded = Signal()

    def __init__(self):
        super().__init__()
        self._ep: pj.Endpoint | None = None
        self._account: SipAccount | None = None
        self._host: str = ""

    def start(self) -> None:
        self._ep = pj.Endpoint()
        self._ep.libCreate()
        self._ep.libInit(pj.EpConfig())
        transport_cfg = pj.TransportConfig()
        transport_cfg.port = 0
        self._ep.transportCreate(pj.PJSIP_TRANSPORT_UDP, transport_cfg)
        self._ep.libStart()

    def stop(self) -> None:
        if self._ep is not None:
            self._account = None
            self._ep.libDestroy()
            self._ep = None

    def register(self, host: str, username: str, password: str) -> None:
        if self._ep is None:
            raise RuntimeError("call start() first")
        self._host = host
        acc_cfg = pj.AccountConfig()
        acc_cfg.idUri = f"sip:{username}@{host}"
        acc_cfg.regConfig.registrarUri = f"sip:{host}"
        cred = pj.AuthCredInfo("digest", "*", username, 0, password)
        acc_cfg.sipConfig.authCreds.append(cred)

        self._account = SipAccount(self)
        self._account.create(acc_cfg)

    def make_call(self, number: str) -> SipCall:
        if self._account is None:
            raise RuntimeError("call register() first")
        call = SipCall(self, self._account)
        call_prm = pj.CallOpParam(True)
        call.makeCall(f"sip:{number}@{self._host}", call_prm)
        return call

    def answer(self, call: SipCall) -> None:
        prm = pj.CallOpParam()
        prm.statusCode = pj.PJSIP_SC_OK
        call.answer(prm)

    def hangup(self, call: SipCall) -> None:
        prm = pj.CallOpParam()
        prm.statusCode = pj.PJSIP_SC_DECLINE
        call.hangup(prm)

    def send_dtmf(self, call: SipCall, digit: str) -> None:
        call.dialDtmf(digit)

    def set_mute(self, call: SipCall, muted: bool) -> None:
        info = call.getInfo()
        for media_info in info.media:
            if media_info.type == pj.PJMEDIA_TYPE_AUDIO and media_info.status == pj.PJSUA_CALL_MEDIA_ACTIVE:
                audio_media = call.getAudioMedia(media_info.index)
                audio_media.adjustTxLevel(0.0 if muted else 1.0)

    def list_devices(self) -> list[AudioDevice]:
        if self._ep is None:
            raise RuntimeError("call start() first")
        raw_devices = self._ep.audDevManager().enumDev2()
        return list_audio_devices(raw_devices)

    def select_capture_device(self, device_id: int) -> None:
        if self._ep is None:
            raise RuntimeError("call start() first")
        self._ep.audDevManager().setCaptureDev(device_id)

    def select_playback_device(self, device_id: int) -> None:
        if self._ep is None:
            raise RuntimeError("call start() first")
        self._ep.audDevManager().setPlaybackDev(device_id)
