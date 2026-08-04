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


def _read_raw(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}


def _write_raw(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> AccountConfig | None:
    data = _read_raw(path)
    try:
        return AccountConfig(host=data["host"], username=data["username"])
    except KeyError:
        return None


def save_config(cfg: AccountConfig, path: Path = DEFAULT_CONFIG_PATH) -> None:
    data = _read_raw(path)
    data.update(asdict(cfg))
    _write_raw(data, path)


def load_device_selection(path: Path = DEFAULT_CONFIG_PATH) -> tuple[str | None, str | None]:
    data = _read_raw(path)
    return data.get("capture_device"), data.get("playback_device")


def save_device_selection(
    capture_device: str | None,
    playback_device: str | None,
    path: Path = DEFAULT_CONFIG_PATH,
) -> None:
    data = _read_raw(path)
    data["capture_device"] = capture_device
    data["playback_device"] = playback_device
    _write_raw(data, path)


def load_google_sync_overwrites_local(path: Path = DEFAULT_CONFIG_PATH) -> bool:
    data = _read_raw(path)
    return data.get("google_sync_overwrites_local", True)


def save_google_sync_overwrites_local(value: bool, path: Path = DEFAULT_CONFIG_PATH) -> None:
    data = _read_raw(path)
    data["google_sync_overwrites_local"] = value
    _write_raw(data, path)


FRITZBOX_KEYRING_PREFIX = "fritzbox:"


def load_fritzbox_username(path: Path = DEFAULT_CONFIG_PATH) -> str | None:
    data = _read_raw(path)
    return data.get("fritzbox_username")


def save_fritzbox_username(username: str, path: Path = DEFAULT_CONFIG_PATH) -> None:
    data = _read_raw(path)
    data["fritzbox_username"] = username
    _write_raw(data, path)


def get_fritzbox_password(username: str) -> str | None:
    return keyring.get_password(SERVICE_NAME, f"{FRITZBOX_KEYRING_PREFIX}{username}")


def set_fritzbox_password(username: str, password: str) -> None:
    keyring.set_password(SERVICE_NAME, f"{FRITZBOX_KEYRING_PREFIX}{username}", password)


def get_password(username: str) -> str | None:
    return keyring.get_password(SERVICE_NAME, username)


def set_password(username: str, password: str) -> None:
    keyring.set_password(SERVICE_NAME, username, password)
