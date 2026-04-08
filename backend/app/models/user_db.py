"""
SQLAlchemy database models for User
"""
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ARRAY, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.db.postgres_client import Base


class UserDB(Base):
    """
    SQLAlchemy model for User table in PostgreSQL
    """
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    display_name = Column(String(255), nullable=True)
    roles = Column(ARRAY(String), default=[], nullable=False)
    groups = Column(ARRAY(String), default=[], nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    last_sync = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<UserDB(id={self.id}, username={self.username}, email={self.email})>"





