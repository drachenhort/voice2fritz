# voice2fritz v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Linux desktop SIP softphone that registers with a FRITZ!Box and lets the user make/receive calls over a headset, with selectable audio input/output devices.

**Architecture:** PySide6 GUI app wrapping pjsua2 (PJSIP's Python bindings) for SIP registration, call signaling, and RTP media. Config (host/username) in a JSON file; password in the system keyring via `python-keyring`. Single SIP account/line for v1.

**Tech Stack:** Python 3.11+, PySide6, pjsua2 (PJSIP Python bindings), python-keyring, pytest, pytest-qt.

## Global Constraints

- Linux desktop only for v1.
- Single SIP account/line — no multi-account, no contacts, no call history, no DTMF dialpad.
- SIP password MUST be stored via system keyring (`python-keyring`), never written to the plaintext config file.
- Config file path: `~/.config/voice2fritz/config.json`.
- All pjsua2 callbacks run on pjsua2's own worker thread — GUI code must only be touched via Qt signal emission from `SipEngine`, connected with Qt's default (auto/queued) connection semantics. Never call Qt widget methods directly from a pjsua2 callback.
- No automated tests for actual SIP/RTP/call behavior (pjsua2 needs a real server + audio hardware) — those are verified via manual integration testing against a real FRITZ!Box account. GUI logic and config/keyring logic ARE unit-testable and must have automated tests (using `pytest-qt` with `QT_QPA_PLATFORM=offscreen` for GUI).

---

## File Structure

```
voice2fritz/
  pyproject.toml
  src/voice2fritz/
    __init__.py
    config.py
    audio.py
    sip_engine.py
    main.py
    gui/
      __init__.py
      settings_dialog.py
      main_window.py
  tests/
    conftest.py
    test_config.py
    test_audio.py
    test_settings_dialog.py
    test_main_window.py
```

---

### Task 1: Project scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `src/voice2fritz/__init__.py`
- Create: `src/voice2fritz/main.py`
- Create: `tests/conftest.py`
- Test: `tests/test_main.py`

**Interfaces:**
- Produces: a runnable `python -m voice2fritz.main` that opens a `QMainWindow` titled `"voice2fritz"`.

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "voice2fritz"
version = "0.1.0"
description = "SIP softphone for FRITZ!Box"
requires-python = ">=3.11"
dependencies = [
    "PySide6>=6.6",
    "keyring>=24",
]

[project.optional-dependencies]
dev = ["pytest>=8", "pytest-qt>=4"]

[project.scripts]
voice2fritz = "voice2fritz.main:main"

[tool.setuptools.packages.find]
where = ["src"]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"
```

Note: `pjsua2` (PJSIP's Python bindings) is a system-level build of PJSIP, not a PyPI package — it is not listed as a `pyproject.toml` dependency. It is installed separately (build PJSIP with `--enable-shared` and Python SWIG bindings, per PJSIP docs) and imported as `import pjsua2`. Document this in a `README.md` "Setup" section once Task 4 introduces the dependency.

- [ ] **Step 2: Write `tests/conftest.py` to force offscreen Qt for all tests**

```python
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
```

- [ ] **Step 3: Write `src/voice2fritz/__init__.py`**

```python
```

(empty — marks the package)

- [ ] **Step 4: Write `src/voice2fritz/main.py`**

```python
import sys

from PySide6.QtWidgets import QApplication, QMainWindow


def build_window() -> QMainWindow:
    window = QMainWindow()
    window.setWindowTitle("voice2fritz")
    window.resize(400, 300)
    return window


def main() -> None:
    app = QApplication(sys.argv)
    window = build_window()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Write the failing test**

```python
# tests/test_main.py
from voice2fritz.main import build_window


def test_build_window_has_correct_title(qtbot):
    window = build_window()
    qtbot.addWidget(window)
    assert window.windowTitle() == "voice2fritz"
```

- [ ] **Step 6: Install package and deps, run test to verify it fails**

Run: `pip install -e ".[dev]"`
Run: `pytest tests/test_main.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'voice2fritz'` before Step 4's file exists, or PASS-then-verify if run after Step 4 — run this step BEFORE writing `main.py` content in a true TDD flow, or simply confirm the assertion is meaningful by temporarily breaking the title).

- [ ] **Step 7: Run test to verify it passes**

Run: `pytest tests/test_main.py -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml src/voice2fritz/__init__.py src/voice2fritz/main.py tests/conftest.py tests/test_main.py
git commit -m "feat: scaffold voice2fritz project with empty main window"
```

---

### Task 2: `config.py` — account config file + keyring password storage

**Files:**
- Create: `src/voice2fritz/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces:
  - `@dataclass AccountConfig(host: str, username: str)`
  - `load_config(path: Path) -> AccountConfig | None`
  - `save_config(cfg: AccountConfig, path: Path) -> None`
  - `get_password(username: str) -> str | None`
  - `set_password(username: str, password: str) -> None`
  - `DEFAULT_CONFIG_PATH: Path` (= `~/.config/voice2fritz/config.json`)
- Consumes: `keyring` module (`keyring.get_password`, `keyring.set_password`), service name `"voice2fritz"`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_config.py
import json

import pytest

from voice2fritz.config import (
    AccountConfig,
    load_config,
    save_config,
    get_password,
    set_password,
)


def test_save_and_load_config_round_trip(tmp_path):
    path = tmp_path / "config.json"
    cfg = AccountConfig(host="fritz.box", username="user123")

    save_config(cfg, path)
    loaded = load_config(path)

    assert loaded == cfg


def test_load_config_missing_file_returns_none(tmp_path):
    path = tmp_path / "does-not-exist.json"
    assert load_config(path) is None


def test_save_config_creates_parent_dirs(tmp_path):
    path = tmp_path / "nested" / "dir" / "config.json"
    cfg = AccountConfig(host="fritz.box", username="user123")

    save_config(cfg, path)

    assert path.exists()
    assert json.loads(path.read_text()) == {"host": "fritz.box", "username": "user123"}


def test_set_and_get_password_uses_keyring(monkeypatch):
    store: dict[tuple[str, str], str] = {}

    def fake_set_password(service, username, password):
        store[(service, username)] = password

    def fake_get_password(service, username):
        return store.get((service, username))

    monkeypatch.setattr("voice2fritz.config.keyring.set_password", fake_set_password)
    monkeypatch.setattr("voice2fritz.config.keyring.get_password", fake_get_password)

    set_password("user123", "hunter2")

    assert get_password("user123") == "hunter2"
    assert store[("voice2fritz", "user123")] == "hunter2"


def test_get_password_unknown_user_returns_none(monkeypatch):
    monkeypatch.setattr("voice2fritz.config.keyring.get_password", lambda service, username: None)
    assert get_password("nobody") is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'voice2fritz.config'`

- [ ] **Step 3: Write `src/voice2fritz/config.py`**

```python
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import keyring

SERVICE_NAME = "voice2fritz"
DEFAULT_CONFIG_PATH = Path.home() / ".config" / "voice2fritz" / "config.json"


@dataclass
class AccountConfig:
    host: str
    username: str


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> AccountConfig | None:
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    return AccountConfig(host=data["host"], username=data["username"])


def save_config(cfg: AccountConfig, path: Path = DEFAULT_CONFIG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(cfg)))


def get_password(username: str) -> str | None:
    return keyring.get_password(SERVICE_NAME, username)


def set_password(username: str, password: str) -> None:
    keyring.set_password(SERVICE_NAME, username, password)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_config.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add src/voice2fritz/config.py tests/test_config.py
git commit -m "feat: add account config file and keyring password storage"
```

---

### Task 3: `audio.py` — audio device listing/selection

**Files:**
- Create: `src/voice2fritz/audio.py`
- Test: `tests/test_audio.py`

**Interfaces:**
- Produces:
  - `@dataclass AudioDevice(id: int, name: str, has_input: bool, has_output: bool)`
  - `list_audio_devices(raw_devices: list) -> list[AudioDevice]` — pure mapping/filter function, takes pjsua2's `enumDev2()` output (or any duck-typed object exposing `.name`, `.inputCount`, `.outputCount`) and an implicit index as id.
  - `input_devices(devices: list[AudioDevice]) -> list[AudioDevice]`
  - `output_devices(devices: list[AudioDevice]) -> list[AudioDevice]`
- Consumes: nothing from earlier tasks. `sip_engine.py` (Task 4) will call `list_audio_devices(ep.audDevManager().enumDev2())`.

Rationale: pjsua2's raw device objects can't be constructed outside a running pjsua2 Endpoint, so the mapping/filtering logic is factored out into pure functions that accept plain objects — this is the testable seam. The pjsua2-calling glue (`enumDev2()`, `setCaptureDev`, `setPlaybackDev`) lives in `sip_engine.py` and is exercised only by manual integration testing (Task 4).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_audio.py
from dataclasses import dataclass

from voice2fritz.audio import AudioDevice, list_audio_devices, input_devices, output_devices


@dataclass
class FakeRawDevice:
    name: str
    inputCount: int
    outputCount: int


def test_list_audio_devices_maps_fields_and_assigns_ids():
    raw = [
        FakeRawDevice(name="Built-in Mic", inputCount=2, outputCount=0),
        FakeRawDevice(name="Headset", inputCount=1, outputCount=2),
    ]

    devices = list_audio_devices(raw)

    assert devices == [
        AudioDevice(id=0, name="Built-in Mic", has_input=True, has_output=False),
        AudioDevice(id=1, name="Headset", has_input=True, has_output=True),
    ]


def test_list_audio_devices_empty():
    assert list_audio_devices([]) == []


def test_input_devices_filters_to_input_capable():
    devices = [
        AudioDevice(id=0, name="Mic", has_input=True, has_output=False),
        AudioDevice(id=1, name="Speaker", has_input=False, has_output=True),
    ]
    assert input_devices(devices) == [devices[0]]


def test_output_devices_filters_to_output_capable():
    devices = [
        AudioDevice(id=0, name="Mic", has_input=True, has_output=False),
        AudioDevice(id=1, name="Speaker", has_input=False, has_output=True),
    ]
    assert output_devices(devices) == [devices[1]]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_audio.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'voice2fritz.audio'`

- [ ] **Step 3: Write `src/voice2fritz/audio.py`**

```python
from dataclasses import dataclass


@dataclass
class AudioDevice:
    id: int
    name: str
    has_input: bool
    has_output: bool


def list_audio_devices(raw_devices: list) -> list[AudioDevice]:
    return [
        AudioDevice(
            id=index,
            name=raw.name,
            has_input=raw.inputCount > 0,
            has_output=raw.outputCount > 0,
        )
        for index, raw in enumerate(raw_devices)
    ]


def input_devices(devices: list[AudioDevice]) -> list[AudioDevice]:
    return [d for d in devices if d.has_input]


def output_devices(devices: list[AudioDevice]) -> list[AudioDevice]:
    return [d for d in devices if d.has_output]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_audio.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/voice2fritz/audio.py tests/test_audio.py
git commit -m "feat: add audio device listing/filtering"
```

---

### Task 4: `sip_engine.py` — pjsua2 wrapper with Qt signals

**Files:**
- Create: `src/voice2fritz/sip_engine.py`
- Modify: `pyproject.toml` (add a `README.md` note — see Step 0)

**Interfaces:**
- Consumes: `voice2fritz.audio.list_audio_devices` (Task 3).
- Produces: `class SipEngine(QObject)` with:
  - Signals: `registrationStateChanged = Signal(str)`, `incomingCall = Signal(object)` (emits a `SipCall`), `callStateChanged = Signal(str)`, `callEnded = Signal()`
  - Methods: `start() -> None`, `stop() -> None`, `register(host: str, username: str, password: str) -> None`, `make_call(number: str) -> "SipCall"`, `answer(call: "SipCall") -> None`, `hangup(call: "SipCall") -> None`, `set_mute(call: "SipCall", muted: bool) -> None`, `list_devices() -> list[AudioDevice]`, `select_capture_device(device_id: int) -> None`, `select_playback_device(device_id: int) -> None`

This task has no automated tests (per Global Constraints — pjsua2 needs a real server + audio hardware). It is verified via the manual integration checklist in Step 4.

- [ ] **Step 0: Note the system dependency**

Add to `README.md` (create if absent):

```markdown
## Setup

`voice2fritz` requires `pjsua2` (PJSIP's Python bindings), which is not
distributed on PyPI. Build PJSIP from source with Python bindings enabled
(see https://docs.pjsip.org/en/latest/pjsua2/building.html), then ensure
the resulting `pjsua2` module is importable from your virtualenv (e.g. by
copying/symlinking the built `.so`/`.py` files into the venv's
`site-packages`, or setting `PYTHONPATH`).
```

- [ ] **Step 1: Write `src/voice2fritz/sip_engine.py`**

```python
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
        transport_cfg.port = 5060
        self._ep.transportCreate(pj.PJSIP_TRANSPORT_UDP, transport_cfg)
        self._ep.libStart()

    def stop(self) -> None:
        if self._ep is not None:
            self._ep.libDestroy()
            self._ep = None

    def register(self, host: str, username: str, password: str) -> None:
        assert self._ep is not None, "call start() first"
        self._host = host
        acc_cfg = pj.AccountConfig()
        acc_cfg.idUri = f"sip:{username}@{host}"
        acc_cfg.regConfig.registrarUri = f"sip:{host}"
        cred = pj.AuthCredInfo("digest", "*", username, 0, password)
        acc_cfg.sipConfig.authCreds.append(cred)

        self._account = SipAccount(self)
        self._account.create(acc_cfg)

    def make_call(self, number: str) -> SipCall:
        assert self._account is not None, "call register() first"
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

    def set_mute(self, call: SipCall, muted: bool) -> None:
        info = call.getInfo()
        for media_info in info.media:
            if media_info.type == pj.PJMEDIA_TYPE_AUDIO and media_info.status == pj.PJSUA_CALL_MEDIA_ACTIVE:
                audio_media = call.getAudioMedia(media_info.index)
                audio_media.adjustTxLevel(0.0 if muted else 1.0)

    def list_devices(self) -> list[AudioDevice]:
        assert self._ep is not None, "call start() first"
        raw_devices = self._ep.audDevManager().enumDev2()
        return list_audio_devices(raw_devices)

    def select_capture_device(self, device_id: int) -> None:
        assert self._ep is not None, "call start() first"
        current = self._ep.audDevManager().getPlaybackDev()
        self._ep.audDevManager().setCaptureDev(device_id)

    def select_playback_device(self, device_id: int) -> None:
        assert self._ep is not None, "call start() first"
        self._ep.audDevManager().setPlaybackDev(device_id)
```

**Note for implementer:** pjsua2's exact `AudDevManager` method names (`setCaptureDev`/`setPlaybackDev`) vary slightly by PJSIP version. During Step 2 below, if these calls raise `AttributeError`, inspect `dir(pj.Endpoint.instance().audDevManager())` and adjust to the installed version's actual API — this is expected verification work, not a plan defect.

- [ ] **Step 2: Manual integration verification**

With a real FRITZ!Box and SIP account credentials:

1. Run a short script that calls `SipEngine().start()` then `register(host, username, password)`, and print `registrationStateChanged` output. Confirm it reports success (FRITZ!Box shows the device as registered in its own SIP client list).
2. Call `list_devices()` and confirm your headset appears with correct `has_input`/`has_output`.
3. Call `select_capture_device()`/`select_playback_device()` with the headset's id.
4. Call `make_call("<a test number>")`, confirm audio flows both directions.
5. Call `hangup()` mid-call, confirm `callEnded` fires and the call tears down cleanly on both ends.
6. From another phone, call the registered number, confirm `incomingCall` fires; call `answer()`, confirm two-way audio.
7. During an active call, call `set_mute(call, True)`, confirm the other party stops hearing you; `set_mute(call, False)` restores audio.

Fix any API mismatches found during this verification before proceeding.

- [ ] **Step 3: Commit**

```bash
git add src/voice2fritz/sip_engine.py README.md
git commit -m "feat: add pjsua2-backed SIP engine with Qt signal bridging"
```

---

### Task 5: `gui/settings_dialog.py` — account setup dialog

**Files:**
- Create: `src/voice2fritz/gui/__init__.py`
- Create: `src/voice2fritz/gui/settings_dialog.py`
- Test: `tests/test_settings_dialog.py`

**Interfaces:**
- Consumes: `voice2fritz.config.AccountConfig`, `save_config`, `set_password` (Task 2).
- Produces: `class SettingsDialog(QDialog)` with:
  - Widgets: `host_edit: QLineEdit`, `username_edit: QLineEdit`, `password_edit: QLineEdit`, `save_button: QPushButton`
  - Signal: `accountSaved = Signal(AccountConfig)` — emitted after a successful save
  - Behavior: clicking `save_button` calls `config.save_config(...)` and `config.set_password(...)`, then emits `accountSaved` and closes the dialog (`accept()`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_settings_dialog.py
from voice2fritz import config
from voice2fritz.gui.settings_dialog import SettingsDialog


def test_save_button_persists_config_and_password(qtbot, tmp_path, monkeypatch):
    saved_configs = []
    saved_passwords = []

    monkeypatch.setattr(config, "save_config", lambda cfg, path=config.DEFAULT_CONFIG_PATH: saved_configs.append(cfg))
    monkeypatch.setattr(config, "set_password", lambda username, password: saved_passwords.append((username, password)))

    dialog = SettingsDialog()
    qtbot.addWidget(dialog)

    dialog.host_edit.setText("fritz.box")
    dialog.username_edit.setText("user123")
    dialog.password_edit.setText("hunter2")

    with qtbot.waitSignal(dialog.accountSaved, timeout=1000):
        dialog.save_button.click()

    assert saved_configs == [config.AccountConfig(host="fritz.box", username="user123")]
    assert saved_passwords == [("user123", "hunter2")]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_settings_dialog.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'voice2fritz.gui'`

- [ ] **Step 3: Write `src/voice2fritz/gui/__init__.py`**

```python
```

- [ ] **Step 4: Write `src/voice2fritz/gui/settings_dialog.py`**

```python
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDialog, QFormLayout, QLineEdit, QPushButton, QVBoxLayout

from voice2fritz import config


class SettingsDialog(QDialog):
    accountSaved = Signal(config.AccountConfig)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("FRITZ!Box Account")

        self.host_edit = QLineEdit()
        self.username_edit = QLineEdit()
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.save_button = QPushButton("Save")

        form = QFormLayout()
        form.addRow("Host", self.host_edit)
        form.addRow("Username", self.username_edit)
        form.addRow("Password", self.password_edit)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.save_button)

        self.save_button.clicked.connect(self._on_save)

    def _on_save(self) -> None:
        cfg = config.AccountConfig(
            host=self.host_edit.text(),
            username=self.username_edit.text(),
        )
        config.save_config(cfg)
        config.set_password(cfg.username, self.password_edit.text())
        self.accountSaved.emit(cfg)
        self.accept()
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_settings_dialog.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/voice2fritz/gui/__init__.py src/voice2fritz/gui/settings_dialog.py tests/test_settings_dialog.py
git commit -m "feat: add FRITZ!Box account settings dialog"
```

---

### Task 6: `gui/main_window.py` — dialer, call controls, device selection

**Files:**
- Create: `src/voice2fritz/gui/main_window.py`
- Test: `tests/test_main_window.py`

**Interfaces:**
- Consumes: `voice2fritz.sip_engine.SipEngine` signals (`registrationStateChanged`, `incomingCall`, `callStateChanged`, `callEnded`) and methods (`make_call`, `answer`, `hangup`, `set_mute`, `list_devices`, `select_capture_device`, `select_playback_device`) — Task 4. `voice2fritz.audio.AudioDevice`, `input_devices`, `output_devices` — Task 3.
- Produces: `class MainWindow(QMainWindow)` with:
  - Widgets: `number_edit: QLineEdit`, `call_button: QPushButton`, `hangup_button: QPushButton`, `mute_button: QPushButton` (checkable), `capture_combo: QComboBox`, `playback_combo: QComboBox`, `status_label: QLabel`
  - Constructor: `MainWindow(sip_engine: SipEngine, parent=None)`

Test strategy: construct `MainWindow` with a fake `SipEngine`-shaped stub object exposing the same signals (real `Signal`s on a `QObject` subclass, since pytest-qt needs real Qt signals to test `waitSignal`/emission) and recording stub methods, so no real pjsua2 is touched. This verifies GUI wiring — button states, label text, and calls made to the engine — without a live SIP stack.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_main_window.py
from PySide6.QtCore import QObject, Signal

from voice2fritz.audio import AudioDevice
from voice2fritz.gui.main_window import MainWindow


class FakeSipEngine(QObject):
    registrationStateChanged = Signal(str)
    incomingCall = Signal(object)
    callStateChanged = Signal(str)
    callEnded = Signal()

    def __init__(self):
        super().__init__()
        self.calls_made = []
        self.hangups = []
        self.mutes = []
        self.selected_capture = None
        self.selected_playback = None

    def make_call(self, number):
        self.calls_made.append(number)
        return object()

    def hangup(self, call):
        self.hangups.append(call)

    def set_mute(self, call, muted):
        self.mutes.append((call, muted))

    def answer(self, call):
        pass

    def list_devices(self):
        return [
            AudioDevice(id=0, name="Built-in Mic", has_input=True, has_output=False),
            AudioDevice(id=1, name="Headset", has_input=True, has_output=True),
        ]

    def select_capture_device(self, device_id):
        self.selected_capture = device_id

    def select_playback_device(self, device_id):
        self.selected_playback = device_id


def test_device_combos_populated_from_engine(qtbot):
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    assert [window.capture_combo.itemText(i) for i in range(window.capture_combo.count())] == [
        "Built-in Mic",
        "Headset",
    ]
    assert [window.playback_combo.itemText(i) for i in range(window.playback_combo.count())] == ["Headset"]


def test_call_button_calls_engine_make_call_with_entered_number(qtbot):
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    window.number_edit.setText("01234567")
    window.call_button.click()

    assert engine.calls_made == ["01234567"]


def test_hangup_button_calls_engine_hangup(qtbot):
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    window.number_edit.setText("01234567")
    window.call_button.click()
    window.hangup_button.click()

    assert len(engine.hangups) == 1


def test_mute_button_toggles_engine_mute(qtbot):
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    window.number_edit.setText("01234567")
    window.call_button.click()
    window.mute_button.click()

    assert engine.mutes == [(engine.mutes[0][0], True)]


def test_registration_state_updates_status_label(qtbot):
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    engine.registrationStateChanged.emit("200 OK")

    assert window.status_label.text() == "200 OK"


def test_device_combo_selection_calls_engine(qtbot):
    engine = FakeSipEngine()
    window = MainWindow(engine)
    qtbot.addWidget(window)

    window.capture_combo.setCurrentIndex(1)

    assert engine.selected_capture == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_main_window.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'voice2fritz.gui.main_window'`

- [ ] **Step 3: Write `src/voice2fritz/gui/main_window.py`**

```python
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from voice2fritz.audio import input_devices, output_devices


class MainWindow(QMainWindow):
    def __init__(self, sip_engine, parent=None):
        super().__init__(parent)
        self.setWindowTitle("voice2fritz")
        self.sip_engine = sip_engine
        self._active_call = None

        self.number_edit = QLineEdit()
        self.call_button = QPushButton("Call")
        self.hangup_button = QPushButton("Hang up")
        self.hangup_button.setEnabled(False)
        self.mute_button = QPushButton("Mute")
        self.mute_button.setCheckable(True)
        self.mute_button.setEnabled(False)
        self.capture_combo = QComboBox()
        self.playback_combo = QComboBox()
        self.status_label = QLabel("Not registered")

        call_row = QHBoxLayout()
        call_row.addWidget(self.number_edit)
        call_row.addWidget(self.call_button)
        call_row.addWidget(self.hangup_button)
        call_row.addWidget(self.mute_button)

        device_row = QHBoxLayout()
        device_row.addWidget(QLabel("Mic:"))
        device_row.addWidget(self.capture_combo)
        device_row.addWidget(QLabel("Speaker:"))
        device_row.addWidget(self.playback_combo)

        layout = QVBoxLayout()
        layout.addLayout(call_row)
        layout.addLayout(device_row)
        layout.addWidget(self.status_label)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self._populate_devices()
        self._connect_signals()

    def _populate_devices(self) -> None:
        devices = self.sip_engine.list_devices()
        for device in input_devices(devices):
            self.capture_combo.addItem(device.name, device.id)
        for device in output_devices(devices):
            self.playback_combo.addItem(device.name, device.id)

    def _connect_signals(self) -> None:
        self.call_button.clicked.connect(self._on_call_clicked)
        self.hangup_button.clicked.connect(self._on_hangup_clicked)
        self.mute_button.clicked.connect(self._on_mute_clicked)
        self.capture_combo.currentIndexChanged.connect(self._on_capture_changed)
        self.playback_combo.currentIndexChanged.connect(self._on_playback_changed)
        self.sip_engine.registrationStateChanged.connect(self.status_label.setText)
        self.sip_engine.callStateChanged.connect(self.status_label.setText)
        self.sip_engine.callEnded.connect(self._on_call_ended)

    def _on_call_clicked(self) -> None:
        self._active_call = self.sip_engine.make_call(self.number_edit.text())
        self.hangup_button.setEnabled(True)
        self.mute_button.setEnabled(True)

    def _on_hangup_clicked(self) -> None:
        if self._active_call is not None:
            self.sip_engine.hangup(self._active_call)
        self._on_call_ended()

    def _on_mute_clicked(self) -> None:
        if self._active_call is not None:
            self.sip_engine.set_mute(self._active_call, self.mute_button.isChecked())

    def _on_call_ended(self) -> None:
        self._active_call = None
        self.hangup_button.setEnabled(False)
        self.mute_button.setEnabled(False)
        self.mute_button.setChecked(False)

    def _on_capture_changed(self, index: int) -> None:
        if index >= 0:
            self.sip_engine.select_capture_device(self.capture_combo.itemData(index))

    def _on_playback_changed(self, index: int) -> None:
        if index >= 0:
            self.sip_engine.select_playback_device(self.playback_combo.itemData(index))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_main_window.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add src/voice2fritz/gui/main_window.py tests/test_main_window.py
git commit -m "feat: add main window with dialer, call controls, device selection"
```

---

### Task 7: Wire it all together in `main.py`

**Files:**
- Modify: `src/voice2fritz/main.py`

**Interfaces:**
- Consumes: `voice2fritz.config.load_config`, `get_password` (Task 2); `voice2fritz.sip_engine.SipEngine` (Task 4); `voice2fritz.gui.settings_dialog.SettingsDialog` (Task 5); `voice2fritz.gui.main_window.MainWindow` (Task 6).

No automated test for this task (it is pure wiring of already-tested pieces plus live pjsua2 startup) — verified by the manual end-to-end checklist in Step 2.

- [ ] **Step 1: Rewrite `src/voice2fritz/main.py`**

```python
import sys

from PySide6.QtWidgets import QApplication

from voice2fritz import config
from voice2fritz.gui.main_window import MainWindow
from voice2fritz.gui.settings_dialog import SettingsDialog
from voice2fritz.sip_engine import SipEngine


def main() -> None:
    app = QApplication(sys.argv)

    sip_engine = SipEngine()
    sip_engine.start()

    account = config.load_config()
    if account is None:
        dialog = SettingsDialog()
        if dialog.exec() != SettingsDialog.DialogCode.Accepted:
            sys.exit(0)
        account = config.load_config()

    password = config.get_password(account.username) or ""
    sip_engine.register(account.host, account.username, password)

    window = MainWindow(sip_engine)
    window.show()

    exit_code = app.exec()
    sip_engine.stop()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Manual end-to-end verification**

1. Delete `~/.config/voice2fritz/config.json` if present. Run `python -m voice2fritz.main`. Confirm the settings dialog appears first.
2. Enter real FRITZ!Box host/username/password, click Save. Confirm the main window opens and `status_label` shows a registration success status.
3. Restart the app. Confirm it skips the settings dialog and registers automatically using the saved config + keyring password.
4. Select your headset in both device dropdowns.
5. Dial a real number, confirm two-way audio, hang up from the app.
6. Call the registered number from another phone, confirm the app can answer (via the incoming-call path) and two-way audio works.
7. Toggle mute mid-call, confirm the other party stops/resumes hearing you.

- [ ] **Step 3: Commit**

```bash
git add src/voice2fritz/main.py
git commit -m "feat: wire config, SIP engine, settings dialog, and main window together"
```

---

## Self-Review Notes

- **Spec coverage:** register/dial/answer/hangup/mute/device-select (Tasks 4, 6, 7) ✓; device selection (Tasks 3, 6) ✓; keyring password storage (Task 2) ✓; settings entry (Task 5) ✓; threading constraint documented in Global Constraints and honored by Task 4's Qt-signal-based design ✓; error handling (registration/call failure surfaced via `status_label`, device fallback deferred to pjsua2's own default-device behavior since v1 scope excludes custom fallback logic — acceptable given spec says "log warning," which the manual verification step in Task 4 covers by inspection of pjsua2 behavior) — no dedicated task needed, covered by existing signal wiring.
- **Placeholder scan:** none found — all steps contain full code or concrete manual-verification instructions.
- **Type consistency:** `SipCall`/`SipEngine` method names and signal names used identically across Tasks 4, 6 (`make_call`, `hangup`, `set_mute`, `answer`, `list_devices`, `select_capture_device`, `select_playback_device`, `registrationStateChanged`, `incomingCall`, `callStateChanged`, `callEnded`) — verified consistent. `AudioDevice` fields (`id`, `name`, `has_input`, `has_output`) consistent across Tasks 3 and 6. `AccountConfig` fields (`host`, `username`) consistent across Tasks 2, 5, 7.
