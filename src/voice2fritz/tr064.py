import xml.etree.ElementTree as ET
from dataclasses import dataclass
from urllib.request import (
    HTTPDigestAuthHandler,
    HTTPPasswordMgrWithDefaultRealm,
    Request,
    build_opener,
)

TR064_PORT = 49000
SERVICE_TYPE = "urn:dslforum-org:service:X_AVM-DE_OnTel:1"
CONTROL_PATH = "/upnp/control/x_contact"


@dataclass
class Contact:
    name: str
    numbers: list[str]


def parse_phonebook_xml(xml_text: str) -> list[Contact]:
    root = ET.fromstring(xml_text)
    contacts = []
    for contact_el in root.iter("contact"):
        person_el = contact_el.find("person")
        name = person_el.findtext("realName", default="") if person_el is not None else ""

        numbers = []
        telephony_el = contact_el.find("telephony")
        if telephony_el is not None:
            for number_el in telephony_el.findall("number"):
                if number_el.text:
                    numbers.append(number_el.text.strip())

        contacts.append(Contact(name=name, numbers=numbers))
    return contacts


def _soap_request(opener, host: str, action: str, body_xml: str) -> str:
    url = f"http://{host}:{TR064_PORT}{CONTROL_PATH}"
    envelope = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" '
        's:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'
        f"<s:Body>{body_xml}</s:Body></s:Envelope>"
    ).encode("utf-8")
    request = Request(
        url,
        data=envelope,
        headers={
            "Content-Type": 'text/xml; charset="utf-8"',
            "SOAPAction": f'"{SERVICE_TYPE}#{action}"',
        },
    )
    with opener.open(request, timeout=10) as response:
        return response.read().decode("utf-8")


def get_phonebook(host: str, username: str, password: str) -> list[Contact]:
    password_manager = HTTPPasswordMgrWithDefaultRealm()
    password_manager.add_password(None, f"http://{host}:{TR064_PORT}/", username, password)
    opener = build_opener(HTTPDigestAuthHandler(password_manager))

    list_body = f'<u:GetPhonebookList xmlns:u="{SERVICE_TYPE}" />'
    list_response = _soap_request(opener, host, "GetPhonebookList", list_body)
    list_root = ET.fromstring(list_response)
    ids_el = list_root.find(".//NewPhonebookList")
    phonebook_id = ids_el.text.split(",")[0].strip() if ids_el is not None and ids_el.text else "0"

    get_body = f'<u:GetPhonebook xmlns:u="{SERVICE_TYPE}"><NewPhonebookID>{phonebook_id}</NewPhonebookID></u:GetPhonebook>'
    get_response = _soap_request(opener, host, "GetPhonebook", get_body)
    get_root = ET.fromstring(get_response)
    url_el = get_root.find(".//NewPhonebookURL")
    if url_el is None or not url_el.text:
        raise ValueError("FritzBox did not return a phonebook URL")

    with opener.open(url_el.text, timeout=10) as response:
        xml_text = response.read().decode("utf-8")

    return parse_phonebook_xml(xml_text)
