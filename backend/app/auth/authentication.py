"""
Authentication functions for database users
"""
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.db.postgres_client import get_db
from app.models.user_db import UserDB
from app.auth.jwt_handler import verify_token, create_access_token

security = HTTPBearer()


async def authenticate_user(
    username: str,
    password: str,
    db: Session
) -> Optional[UserDB]:
    """
    Authenticate a user via database lookup.

    Args:
        username: Username to authenticate
        password: Password to verify
        db: Database session

    Returns:
        UserDB object if authentication successful, None otherwise
    """
    # Check if user exists in database
    db_user = db.query(UserDB).filter(UserDB.username == username).first()

    if db_user and db_user.active:
        return db_user

    return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> UserDB:
    """
    Get current authenticated user from JWT token.

    Args:
        credentials: HTTP Bearer token credentials
        db: Database session

    Returns:
        UserDB object for authenticated user

    Raises:
        401: If token is invalid or user not found
    """
    token = credentials.credentials
    payload = verify_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username: str = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(UserDB).filter(UserDB.username == username).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    return user
