from app.domain.services import (
    generate_4digit_code,
    make_code_digest,
    secure_compare,
    verify_code_digest,
)


def test_generate_4digit_code_format_and_range():
    for _ in range(100):
        c = generate_4digit_code()
        assert len(c) == 4 and c.isdigit(), c
        assert 0 <= int(c) <= 9999


def test_code_digest_verify_success_and_failure():
    code = "1234"
    salt_b64, dig_b64 = make_code_digest(code)
    assert verify_code_digest("1234", salt_b64, dig_b64)
    assert not verify_code_digest("0000", salt_b64, dig_b64)


def test_secure_compare_constant_api():
    assert secure_compare("abc", "abc")
    assert not secure_compare("abc", "abd")
