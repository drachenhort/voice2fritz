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
    try:
        data = json.loads(path.read_text())
        return AccountConfig(host=data["host"], username=data["username"])
    except (json.JSONDecodeError, KeyError):
        return None


def save_config(cfg: AccountConfig, path: Path = DEFAULT_CONFIG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(cfg)))


def get_password(username: str) -> str | None:
    return keyring.get_password(SERVICE_NAME, username)


def set_password(username: str, password: str) -> None:
    keyring.set_password(SERVICE_NAME, username, password)
