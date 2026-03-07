"""
SQLAlchemy database model for User (Keycloak-backed)
"""
import uuid
from sqlalchemy import Column, String, Boolean, DateTime, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.db.postgres_client import Base


class UserDB(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Stable Keycloak subject ID — used as the primary lookup key
    keycloak_sub = Column(String(255), unique=True, nullable=True, index=True)

    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    display_name = Column(String(255), nullable=True)

    # Roles and groups synced from Keycloak token claims
    roles = Column(ARRAY(String), default=[], nullable=False)
    groups = Column(ARRAY(String), default=[], nullable=False)

    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self):
        return f"<UserDB(id={self.id}, username={self.username}, keycloak_sub={self.keycloak_sub})>"
