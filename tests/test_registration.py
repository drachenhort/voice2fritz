import pytest

from voice2fritz.registration import REGISTRATION_TIMEOUT_MS, classify_registration


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("200 OK", "ok"),
        ("202 Accepted", "ok"),
        ("401 Unauthorized", "rejected"),
        ("403 Forbidden", "rejected"),
        ("407 Proxy Authentication Required", "rejected"),
        ("408 Request Timeout", None),
        ("503 Service Unavailable", None),
        ("", None),
    ],
)
def test_classify_registration(text, expected):
    assert classify_registration(text) == expected


def test_timeout_is_twenty_seconds():
    assert REGISTRATION_TIMEOUT_MS == 20_000
