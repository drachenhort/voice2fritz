import json
from dataclasses import asdict, dataclass
from pathlib import Path

DEFAULT_CONTACTS_PATH = Path.home() / ".config" / "voice2fritz" / "contacts.json"


@dataclass
class Contact:
    name: str
    number: str
    source: str = "local"


def load_contacts(path: Path = DEFAULT_CONTACTS_PATH) -> list[Contact]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        return []
    return [
        Contact(name=item["name"], number=item["number"], source=item.get("source", "local"))
        for item in data
    ]


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


def sync_contact_for_name(
    name: str,
    numbers: list[str],
    overwrite_local: bool,
    path: Path = DEFAULT_CONTACTS_PATH,
) -> bool:
    all_contacts = load_contacts(path)
    has_local = any(c.name == name and c.source == "local" for c in all_contacts)

    if has_local and not overwrite_local:
        return False

    existing_google_numbers = {c.number for c in all_contacts if c.name == name and c.source == "google"}

    if not has_local and existing_google_numbers == set(numbers):
        return False

    remaining = [c for c in all_contacts if c.name != name]
    remaining.extend(Contact(name=name, number=number, source="google") for number in numbers)
    save_contacts(remaining, path)
    return True
