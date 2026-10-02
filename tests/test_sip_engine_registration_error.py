from voice2fritz.sip_engine import PJSIP_EAUTHSTALECOUNT, registration_error_message


def test_stale_retry_error_is_reported_with_pjsip_text():
    message = registration_error_message(
        "microsip@fritz.box", PJSIP_EAUTHSTALECOUNT, 401, "Unauthorized", "Maximum number of stale retries exceeded"
    )

    assert message == "Authorization failed for microsip@fritz.box: Maximum number of stale retries exceeded"


def test_rejected_credentials_without_pj_error_use_sip_reason():
    message = registration_error_message("microsip@fritz.box", 0, 403, "Forbidden", "")

    assert message == "Authorization failed for microsip@fritz.box: 403 Forbidden"


def test_successful_registration_is_not_an_error():
    assert registration_error_message("microsip@fritz.box", 0, 200, "OK", "") is None


def test_non_auth_failure_is_not_reported():
    assert registration_error_message("microsip@fritz.box", 0, 408, "Request Timeout", "") is None
