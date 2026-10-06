"""Reading registration status text such as "200 OK" or "401 Unauthorized"."""

# How long to wait for the FRITZ!Box to answer a registration.
REGISTRATION_TIMEOUT_MS = 20_000

_AUTH_REJECTED_CODES = {"401", "403", "407"}


def classify_registration(text: str) -> str | None:
    """"ok", "rejected" (the FRITZ!Box refused the login), or None for anything else.

    None covers unreachable hosts and timeouts, which say nothing about the password.
    """
    if text.startswith("2"):
        return "ok"
    if text.split(" ", 1)[0] in _AUTH_REJECTED_CODES:
        return "rejected"
    return None
