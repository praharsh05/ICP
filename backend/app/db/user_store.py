"""
In-memory user store — replaces PostgreSQL for local dev/testing.

Users are seeded on startup and lost on restart. This is intentional —
when Keycloak is integrated later, users are managed externally.
"""
from datetime import datetime, timezone
from typing import Optional, List, Dict
from uuid import UUID, uuid4


class UserRecord:
    """Simple user object that mimics the old SQLAlchemy UserDB."""

    def __init__(
        self,
        username: str,
        email: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        display_name: Optional[str] = None,
        keycloak_sub: Optional[str] = None,
        roles: Optional[List[str]] = None,
        groups: Optional[List[str]] = None,
        active: bool = True,
        id: Optional[UUID] = None,
    ):
        self.id = id or uuid4()
        self.username = username
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.display_name = display_name
        self.keycloak_sub = keycloak_sub
        self.roles = roles or []
        self.groups = groups or []
        self.active = active
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)


# ── In-memory store ─────────────────────────────────────────────────

_users: Dict[str, UserRecord] = {}  # keyed by username


def _seed_defaults():
    """Seed test users on first import."""
    defaults = [
        UserRecord(
            username="admin",
            email="admin@icp.local",
            first_name="Admin",
            last_name="User",
            display_name="Admin User",
            roles=["admin", "analyst", "viewer"],
            groups=["administrators"],
        ),
        UserRecord(
            username="analyst",
            email="analyst@icp.local",
            first_name="Analyst",
            last_name="User",
            display_name="Analyst User",
            roles=["analyst", "viewer"],
            groups=["analysts"],
        ),
        UserRecord(
            username="viewer",
            email="viewer@icp.local",
            first_name="Viewer",
            last_name="User",
            display_name="Viewer User",
            roles=["viewer"],
            groups=["viewers"],
        ),
    ]
    for u in defaults:
        _users[u.username] = u


_seed_defaults()


# ── Query helpers ────────────────────────────────────────────────────

def get_user_by_username(username: str) -> Optional[UserRecord]:
    return _users.get(username)


def get_user_by_id(user_id: UUID) -> Optional[UserRecord]:
    for u in _users.values():
        if u.id == user_id:
            return u
    return None


def get_user_by_email(email: str) -> Optional[UserRecord]:
    for u in _users.values():
        if u.email == email:
            return u
    return None


def get_user_by_keycloak_sub(sub: str) -> Optional[UserRecord]:
    for u in _users.values():
        if u.keycloak_sub == sub:
            return u
    return None


def list_users(
    skip: int = 0,
    limit: int = 100,
    active: Optional[bool] = None,
) -> List[UserRecord]:
    result = list(_users.values())
    if active is not None:
        result = [u for u in result if u.active == active]
    return result[skip : skip + limit]


def save_user(user: UserRecord) -> UserRecord:
    """Insert or update a user in the store."""
    user.updated_at = datetime.now(timezone.utc)
    _users[user.username] = user
    return user


def delete_user(username: str) -> bool:
    if username in _users:
        _users[username].active = False
        return True
    return False
