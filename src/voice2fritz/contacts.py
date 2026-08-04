import json
from dataclasses import asdict, dataclass
from pathlib import Path

DEFAULT_CONTACTS_PATH = Path.home() / ".config" / "voice2fritz" / "contacts.json"


@dataclass
class Contact:
    name: str
    number: str


def load_contacts(path: Path = DEFAULT_CONTACTS_PATH) -> list[Contact]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        return []
    return [Contact(name=item["name"], number=item["number"]) for item in data]


def save_contacts(contacts: list[Contact], path: Path = DEFAULT_CONTACTS_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([asdict(contact) for contact in contacts]))


def add_contact(name: str, number: str, path: Path = DEFAULT_CONTACTS_PATH) -> None:
    contacts = load_contacts(path)
    contacts.append(Contact(name=name, number=number))
    save_contacts(contacts, path)


def delete_contact(index: int, path: Path = DEFAULT_CONTACTS_PATH) -> None:
    contacts = load_contacts(path)
    if 0 <= index < len(contacts):
        del contacts[index]
        save_contacts(contacts, path)
