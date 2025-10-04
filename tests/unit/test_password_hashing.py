from app.infrastructure.security.password import hash_password, verify_password


def test_password_hash_and_verify():
    h = hash_password("s3cret", rounds=12)
    assert h.startswith("$2b$") or h.startswith("$2a$")
    assert verify_password("s3cret", h)
    assert not verify_password("wrong", h)
