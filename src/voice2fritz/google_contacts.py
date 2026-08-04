from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from voice2fritz import config, contacts

TOKEN_PATH = Path.home() / ".config" / "voice2fritz" / "google_token.json"
CLIENT_SECRET_PATH = Path.home() / ".config" / "voice2fritz" / "google_client_secret.json"
SCOPES = ["https://www.googleapis.com/auth/contacts.readonly"]


def _get_credentials() -> Credentials:
    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())

    if not creds or not creds.valid:
        if not CLIENT_SECRET_PATH.exists():
            raise FileNotFoundError(
                f"Google client secret not found at {CLIENT_SECRET_PATH}. "
                "See the README for how to create one."
            )
        flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET_PATH), SCOPES)
        creds = flow.run_local_server(port=0)

    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(creds.to_json())
    return creds


def _fetch_google_contacts(service) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    page_token = None

    while True:
        response = (
            service.people()
            .connections()
            .list(
                resourceName="people/me",
                personFields="names,phoneNumbers",
                pageSize=1000,
                pageToken=page_token,
            )
            .execute()
        )

        for person in response.get("connections", []):
            names = person.get("names") or []
            phone_numbers = person.get("phoneNumbers") or []
            if not names or not phone_numbers:
                continue
            name = names[0].get("displayName", "")
            numbers = [pn["value"] for pn in phone_numbers if pn.get("value")]
            if name and numbers:
                grouped.setdefault(name, []).extend(numbers)

        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return grouped


def _sync_from_grouped(
    grouped: dict[str, list[str]],
    overwrite_local: bool,
    path: Path = contacts.DEFAULT_CONTACTS_PATH,
) -> int:
    changed = 0
    for name, numbers in grouped.items():
        if contacts.sync_contact_for_name(name, numbers, overwrite_local, path):
            changed += 1
    return changed


def sync_google_contacts() -> int:
    creds = _get_credentials()
    service = build("people", "v1", credentials=creds)
    grouped = _fetch_google_contacts(service)
    overwrite_local = config.load_google_sync_overwrites_local()
    return _sync_from_grouped(grouped, overwrite_local)
