from app.domain.services import generate_4digit_code, secure_compare


def test_code_is_4_digits_and_randomish():
    seen = set()
    for _ in range(200):
        c = generate_4digit_code()
        assert len(c) == 4 and c.isdigit()
        assert 0 <= int(c) <= 9999
        seen.add(c)
    # not a strict randomness test, but should produce some variety
    assert len(seen) > 10


def test_secure_compare_behavior():
    assert secure_compare("abcd", "abcd") is True
    assert secure_compare("abcd", "abce") is False
    assert secure_compare("", "") is True
    assert secure_compare("a", "") is False
