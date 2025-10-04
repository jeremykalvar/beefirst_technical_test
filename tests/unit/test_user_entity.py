from app.domain.entities import User
from app.domain.errors import InvalidStatusTransition, UserLocked


def test_email_normalized_and_defaults():
    u = User(id=None, email=" Alice@Example.COM ")
    assert u.email == "alice@example.com"
    assert u.status == "pending"
    assert u.failed_attempts == 0
    assert u.last_code_sent_at is None


def test_activate_from_pending_ok():
    u = User(id=None, email="a@x.com")
    u.activate()
    assert u.status == "active"


def test_activate_from_active_raises():
    u = User(id=None, email="a@x.com")
    u.activate()
    try:
        u.activate()
        assert False, "should have raised"
    except InvalidStatusTransition:
        pass


def test_activate_from_locked_raises_userlocked():
    u = User(id=None, email="a@x.com", status="locked")
    try:
        u.activate()
        assert False, "should have raised"
    except UserLocked:
        pass


def test_lock_transitions_to_locked():
    u = User(id=None, email="a@x.com")
    u.lock()
    assert u.status == "locked"
