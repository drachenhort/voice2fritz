import array
import math
import os
import socket

import pjsua2 as pj
from PySide6.QtCore import QObject, Signal

from voice2fritz.audio import AudioDevice, list_audio_devices, list_pulse_devices
from voice2fritz.i18n import tr

# Not exported by the pjsua2 bindings: PJSIP_ERRNO_START_PJSIP + 111.
PJSIP_EAUTHSTALECOUNT = 171111
_AUTH_FAILURE_CODES = {401, 403, 407}


class RegistrationError(RuntimeError):
    """The account could not be set up, e.g. because the host makes an invalid SIP URI."""


def registration_error_message(account: str, status: int, code: int, reason: str, status_text: str) -> str | None:
    """Describe a registration that failed authorization, or None if it didn't."""
    if status != PJSIP_EAUTHSTALECOUNT and code not in _AUTH_FAILURE_CODES:
        return None
    detail = status_text if status != 0 else f"{code} {reason}"
    return tr("Authorization failed for {account}: {detail}", account=account, detail=detail)


# German/European ringback tone: 425 Hz, 1 s on, 4 s off.
_RINGBACK_FREQ_HZ = 425
_RINGBACK_ON_MS = 1000
_RINGBACK_OFF_MS = 4000


def local_address_toward(host: str, port: int = 5060) -> str | None:
    """The local IP the OS would use to reach host, or None if it can't be determined.

    Connecting a UDP socket only picks a route; no packet is sent.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect((host, port))
            return probe.getsockname()[0]
    except OSError:
        return None


def should_play_ringback(role: int, state: int) -> bool:
    """True while our own outgoing call is being set up and the far end hasn't answered."""
    return role == pj.PJSIP_ROLE_UAC and state in (pj.PJSIP_INV_STATE_CALLING, pj.PJSIP_INV_STATE_EARLY)


class SipCall(pj.Call):
    def __init__(self, engine: "SipEngine", account: "SipAccount", call_id: int = pj.PJSUA_INVALID_ID):
        pj.Call.__init__(self, account, call_id)
        self.engine = engine
        self.has_early_media = False

    def onCallState(self, prm):
        info = self.getInfo()
        self.engine.callStateChanged.emit(info.stateText)
        # Early media (e.g. a network announcement) stops the local tone in onCallMediaState.
        if should_play_ringback(info.role, info.state):
            if not self.has_early_media:
                self.engine.start_ringback()
        else:
            self.engine.stop_ringback()
        if info.state == pj.PJSIP_INV_STATE_DISCONNECTED:
            self.engine.callEnded.emit()

    def onCallMediaState(self, prm):
        info = self.getInfo()
        for media_info in info.media:
            if media_info.type == pj.PJMEDIA_TYPE_AUDIO and media_info.status == pj.PJSUA_CALL_MEDIA_ACTIVE:
                # The far end now supplies audio (ringback, announcement or the call itself).
                self.has_early_media = True
                self.engine.stop_ringback()
                audio_media = self.getAudioMedia(media_info.index)
                dev_manager = pj.Endpoint.instance().audDevManager()
                dev_manager.getCaptureDevMedia().startTransmit(audio_media)
                audio_media.startTransmit(dev_manager.getPlaybackDevMedia())


class _LevelMeterPort(pj.AudioMediaPort):
    """Sink port on the conference bridge that tracks the peak of the frames sent to it."""

    def __init__(self):
        pj.AudioMediaPort.__init__(self)
        self.peak = 0

    def onFrameReceived(self, frame):
        samples = array.array("h", bytes(frame.buf))
        if samples:
            self.peak = max(self.peak, max(samples), -min(samples))


def peak_to_level(peak: int) -> float:
    """Map a 16-bit sample peak to 0..1 on a -60..0 dBFS scale."""
    if peak <= 0:
        return 0.0
    db = 20 * math.log10(min(peak, 32768) / 32768)
    return max(0.0, (db + 60) / 60)


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
        self.media_address: str | None = None
        self._pulse_device_index: int | None = None
        self._level_meter: _LevelMeterPort | None = None
        self._echo_recorder: pj.AudioMediaRecorder | None = None
        self._echo_player: pj.AudioMediaPlayer | None = None
        self._ringback: pj.ToneGenerator | None = None

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
            self.stop_level_monitor()
            self.stop_echo_recording()
            self.stop_echo_playback()
            self.stop_ringback()
            self._account = None
            self._ep.libDestroy()
            self._ep = None

    def register(self, host: str, username: str, password: str) -> None:
        if self._ep is None:
            raise RuntimeError("call start() first")
        if self._account is not None:
            self._account.shutdown()
            self._account = None
        self._host = host
        self.account_label = f"{username}@{host}"
        acc_cfg = pj.AccountConfig()
        acc_cfg.idUri = f"sip:{username}@{host}"
        acc_cfg.regConfig.registrarUri = f"sip:{host}"
        cred = pj.AuthCredInfo("digest", "*", username, 0, password)
        acc_cfg.sipConfig.authCreds.append(cred)
        # PJSIP advertises the default route's address for audio (SDP). With a VPN as the
        # default route that address is unreachable for the FRITZ!Box, so calls stay silent.
        # Bind media to the local address that actually leads to the registrar instead.
        media_address = local_address_toward(host)
        self.media_address = media_address
        if media_address is not None:
            acc_cfg.mediaConfig.transportConfig.boundAddress = media_address

        account = SipAccount(self)
        try:
            account.create(acc_cfg)
        except pj.Error as exc:
            raise RegistrationError(exc.reason) from exc
        self._account = account

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

    def start_level_monitor(self) -> None:
        if self._ep is None:
            raise RuntimeError("call start() first")
        if self._level_meter is not None:
            return
        fmt = pj.MediaFormatAudio()
        fmt.type = pj.PJMEDIA_TYPE_AUDIO
        fmt.clockRate = 16000
        fmt.channelCount = 1
        fmt.bitsPerSample = 16
        fmt.frameTimeUsec = 20000
        meter = _LevelMeterPort()
        meter.createPort("level-meter", fmt)
        self._ep.audDevManager().getCaptureDevMedia().startTransmit(meter)
        self._level_meter = meter

    def stop_level_monitor(self) -> None:
        if self._level_meter is None:
            return
        self._ep.audDevManager().getCaptureDevMedia().stopTransmit(self._level_meter)
        self._level_meter = None

    def capture_level(self) -> float:
        """Mic level (0..1) since the previous call; 0 while the monitor is off."""
        if self._level_meter is None:
            return 0.0
        peak, self._level_meter.peak = self._level_meter.peak, 0
        return peak_to_level(peak)

    def start_echo_recording(self, path: str) -> None:
        if self._ep is None:
            raise RuntimeError("call start() first")
        self.stop_echo_recording()
        recorder = pj.AudioMediaRecorder()
        recorder.createRecorder(path)
        self._ep.audDevManager().getCaptureDevMedia().startTransmit(recorder)
        self._echo_recorder = recorder

    def stop_echo_recording(self) -> None:
        if self._echo_recorder is None:
            return
        self._ep.audDevManager().getCaptureDevMedia().stopTransmit(self._echo_recorder)
        # Dropping the recorder closes the WAV file.
        self._echo_recorder = None

    def start_echo_playback(self, path: str) -> None:
        if self._ep is None:
            raise RuntimeError("call start() first")
        self.stop_echo_playback()
        player = pj.AudioMediaPlayer()
        player.createPlayer(path, pj.PJMEDIA_FILE_NO_LOOP)
        player.startTransmit(self._ep.audDevManager().getPlaybackDevMedia())
        self._echo_player = player

    def stop_echo_playback(self) -> None:
        if self._echo_player is None:
            return
        self._echo_player.stopTransmit(self._ep.audDevManager().getPlaybackDevMedia())
        self._echo_player = None

    def start_ringback(self) -> None:
        if self._ep is None or self._ringback is not None:
            return
        tone = pj.ToneDesc()
        tone.freq1 = _RINGBACK_FREQ_HZ
        tone.freq2 = 0
        tone.on_msec = _RINGBACK_ON_MS
        tone.off_msec = _RINGBACK_OFF_MS
        tones = pj.ToneDescVector()
        tones.append(tone)
        generator = pj.ToneGenerator()
        generator.createToneGenerator()
        generator.play(tones, True)
        generator.startTransmit(self._ep.audDevManager().getPlaybackDevMedia())
        self._ringback = generator

    def stop_ringback(self) -> None:
        if self._ringback is None:
            return
        self._ringback.stopTransmit(self._ep.audDevManager().getPlaybackDevMedia())
        self._ringback.stop()
        self._ringback = None
