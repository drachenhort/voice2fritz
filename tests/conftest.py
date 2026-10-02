import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(autouse=True)
def no_real_keyring(monkeypatch):
    # Settings looks up the saved password; never touch the user's real keyring in tests.
    from voice2fritz import config

    monkeypatch.setattr(config, "get_password", lambda username: None)
