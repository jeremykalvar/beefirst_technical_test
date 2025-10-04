import base64

from app.domain.services import make_code_digest, verify_code_digest


def test_digest_verification_success_and_failure():
    salt_b64, dig_b64 = make_code_digest("1234")
    assert verify_code_digest("1234", salt_b64, dig_b64) is True
    assert verify_code_digest("0000", salt_b64, dig_b64) is False


def test_salts_are_random():
    s1, d1 = make_code_digest("1234")
    s2, d2 = make_code_digest("1234")
    # Very unlikely to collide
    assert s1 != s2 or d1 != d2


def test_outputs_are_base64_strings():
    s, d = make_code_digest("1234")
    base64.b64decode(s)
    base64.b64decode(d)


def test_invalid_base64_inputs_fail():
    assert verify_code_digest("1234", "!!!", "???") is False
