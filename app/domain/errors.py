class DomainError(Exception):
    """Base class for all domain-level errors."""

    pass


class InvalidStatusTransition(DomainError):
    """Tried to change a user's status in a way that's not allowed."""

    pass


class UserLocked(DomainError):
    """Action attempted on a locked user."""

    pass


class UserNotFound(DomainError):
    """No user matches the lookup criteria (e.g., email)."""

    pass


class UserAlreadyExists(DomainError):
    """User with the given identity already exists (when creation forbids upsert)."""

    pass
