import os

import pjsua2 as pj
from PySide6.QtCore import QObject, Signal

from voice2fritz.audio import AudioDevice, list_audio_devices, list_pulse_devices

# Not exported by the pjsua2 bindings: PJSIP_ERRNO_START_PJSIP + 111.
PJSIP_EAUTHSTALECOUNT = 171111
_AUTH_FAILURE_CODES = {401, 403, 407}


def registration_error_message(account: str, status: int, code: int, reason: str, status_text: str) -> str | None:
    """Describe a registration that failed authorization, or None if it didn't."""
    if status != PJSIP_EAUTHSTALECOUNT and code not in _AUTH_FAILURE_CODES:
        return None
    detail = status_text if status != 0 else f"{code} {reason}"
    return f"Authorization failed for {account}: {detail}"


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
        self.engine.registrationStateChanged.emit(f"{info.regStatus} {info.regStatusText}")
        status_text = pj.Endpoint.instance().utilStrError(prm.status) if prm.status != 0 else ""
        message = registration_error_message(self.engine.account_label, prm.status, prm.code, prm.reason, status_text)
        if message is not None:
            self.engine.registrationFailed.emit(message)

    def onIncomingCall(self, prm):
        call = SipCall(self.engine, self, call_id=prm.callId)
        self.engine.incomingCall.emit(call)


class SipEngine(QObject):
    registrationStateChanged = Signal(str)
    registrationFailed = Signal(str)
    incomingCall = Signal(object)
    callStateChanged = Signal(str)
    callEnded = Signal()

    def __init__(self):
        super().__init__()
        self._ep: pj.Endpoint | None = None
        self._account: SipAccount | None = None
        self._host: str = ""
        self.account_label: str = ""
        self._pulse_device_index: int | None = None

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
        if self._account is not None:
            self._account.delete()
            self._account = None
        self._host = host
        self.account_label = f"{username}@{host}"
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
        number = number.strip()
        if not number:
            raise ValueError("cannot dial an empty number")
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
        prm.statusCode = pj.PJSIP_SC_OK
        call.hangup(prm)

    def decline(self, call: SipCall) -> None:
        prm = pj.CallOpParam()
        prm.statusCode = pj.PJSIP_SC_DECLINE
        call.answer(prm)

    def get_remote_number(self, call) -> str:
        remote_uri = call.getInfo().remoteUri
        start = remote_uri.find("sip:")
        if start == -1:
            return ""
        start += len("sip:")
        end = remote_uri.find("@", start)
        if end == -1:
            return ""
        return remote_uri[start:end]

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
        alsa_devices = list_audio_devices(self._ep.audDevManager().enumDev2())
        # PipeWire/PulseAudio owns most hardware, so ALSA names are cryptic and incomplete.
        # Offer the sound server's devices instead and route through ALSA's "pulse" plugin.
        self._pulse_device_index = next(
            (d.id for d in alsa_devices if d.name == "pulse" and d.has_input and d.has_output),
            None,
        )
        if self._pulse_device_index is not None:
            pulse_devices = list_pulse_devices()
            if pulse_devices:
                return pulse_devices
        return alsa_devices

    def select_capture_device(self, device_id: int | str) -> None:
        if self._ep is None:
            raise RuntimeError("call start() first")
        if isinstance(device_id, str):
            self._select_pulse_device("PULSE_SOURCE", device_id)
        else:
            self._ep.audDevManager().setCaptureDev(device_id)

    def select_playback_device(self, device_id: int | str) -> None:
        if self._ep is None:
            raise RuntimeError("call start() first")
        if isinstance(device_id, str):
            self._select_pulse_device("PULSE_SINK", device_id)
        else:
            self._ep.audDevManager().setPlaybackDev(device_id)

    def _select_pulse_device(self, env_var: str, node_name: str) -> None:
        # The pulse plugin reads PULSE_SINK/PULSE_SOURCE whenever the ALSA device is opened.
        if node_name:
            os.environ[env_var] = node_name
        else:
            os.environ.pop(env_var, None)
        dev_manager = self._ep.audDevManager()
        if dev_manager.sndIsActive():
            # Reopen the device mid-call so the new target takes effect immediately.
            dev_manager.setNullDev()
        dev_manager.setCaptureDev(self._pulse_device_index)
        dev_manager.setPlaybackDev(self._pulse_device_index)
