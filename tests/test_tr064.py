from voice2fritz.tr064 import Contact, parse_phonebook_xml

SAMPLE_PHONEBOOK_XML = """<?xml version="1.0" encoding="utf-8"?>
<phonebooks>
  <phonebook>
    <contact>
      <person>
        <realName>Anna Schmidt</realName>
      </person>
      <telephony>
        <number type="home">+4917612345678</number>
        <number type="mobile">+4917698765432</number>
      </telephony>
    </contact>
    <contact>
      <person>
        <realName>Ben Weber</realName>
      </person>
      <telephony>
        <number type="mobile">+4930123456</number>
      </telephony>
    </contact>
  </phonebook>
</phonebooks>
"""


def test_parse_phonebook_xml_extracts_name_and_numbers():
    contacts = parse_phonebook_xml(SAMPLE_PHONEBOOK_XML)

    assert contacts == [
        Contact(name="Anna Schmidt", numbers=["+4917612345678", "+4917698765432"]),
        Contact(name="Ben Weber", numbers=["+4930123456"]),
    ]


def test_parse_phonebook_xml_empty_phonebook():
    xml_text = """<?xml version="1.0" encoding="utf-8"?>
<phonebooks><phonebook></phonebook></phonebooks>"""

    assert parse_phonebook_xml(xml_text) == []


def test_parse_phonebook_xml_contact_without_numbers():
    xml_text = """<?xml version="1.0" encoding="utf-8"?>
<phonebooks>
  <phonebook>
    <contact>
      <person><realName>No Number Guy</realName></person>
      <telephony></telephony>
    </contact>
  </phonebook>
</phonebooks>"""

    assert parse_phonebook_xml(xml_text) == [Contact(name="No Number Guy", numbers=[])]
