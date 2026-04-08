"""
UserDB — alias for the in-memory UserRecord.
Keeps existing import paths working across routers and auth modules.
"""
from app.db.user_store import UserRecord as UserDB

__all__ = ["UserDB"]
