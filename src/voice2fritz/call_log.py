import json
from dataclasses import asdict, dataclass
from pathlib import Path

DEFAULT_CALL_LOG_PATH = Path.home() / ".config" / "voice2fritz" / "call_log.json"


@dataclass
class CallLogEntry:
    number: str
    name: str
    direction: str
    timestamp: str
    duration_seconds: int


def load_call_log(path: Path = DEFAULT_CALL_LOG_PATH) -> list[CallLogEntry]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        return []
    return [
        CallLogEntry(
            number=item["number"],
            name=item["name"],
            direction=item["direction"],
            timestamp=item["timestamp"],
            duration_seconds=item["duration_seconds"],
        )
        for item in data
    ]


def _save_call_log(entries: list[CallLogEntry], path: Path = DEFAULT_CALL_LOG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([asdict(entry) for entry in entries]))


def append_call_log_entry(entry: CallLogEntry, path: Path = DEFAULT_CALL_LOG_PATH) -> None:
    entries = load_call_log(path)
    entries.append(entry)
    _save_call_log(entries, path)


def clear_call_log(path: Path = DEFAULT_CALL_LOG_PATH) -> None:
    _save_call_log([], path)
