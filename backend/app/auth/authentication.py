"""
Authentication — switches between Keycloak OIDC and local JWT based on AUTH_PROVIDER flag.

  AUTH_PROVIDER=keycloak  → validates Keycloak tokens via JWKS, auto-provisions users
  AUTH_PROVIDER=local     → validates local JWT tokens, authenticates via username/password
"""
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import is_keycloak_enabled
from app.db.postgres_client import get_db
from app.models.user_db import UserDB

security = HTTPBearer()


# ── Keycloak auth path ──────────────────────────────────────────────

async def _get_user_keycloak(
    token: str,
    db: Session,
) -> UserDB:
    from app.auth.keycloak_auth import verify_keycloak_token, extract_user_info

    payload = await verify_keycloak_token(token)
    user_info = extract_user_info(payload)

    keycloak_sub = user_info["sub"]
    if not keycloak_sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is missing the 'sub' claim",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(UserDB).filter(UserDB.keycloak_sub == keycloak_sub).first()

    if user is None:
        # Auto-provision on first login
        user = UserDB(
            username=user_info["username"] or keycloak_sub,
            email=user_info["email"] or f"{keycloak_sub}@keycloak.local",
            first_name=user_info["first_name"],
            last_name=user_info["last_name"],
            display_name=user_info["display_name"],
            keycloak_sub=keycloak_sub,
            roles=user_info["roles"],
            groups=user_info["groups"],
            active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # Sync profile and roles from latest token claims
        if user_info["email"]:
            user.email = user_info["email"]
        user.first_name = user_info["first_name"]
        user.last_name = user_info["last_name"]
        user.display_name = user_info["display_name"]
        user.roles = user_info["roles"]
        user.groups = user_info["groups"]
        db.commit()
        db.refresh(user)

    return user


# ── Local JWT auth path ─────────────────────────────────────────────

async def _get_user_local(
    token: str,
    db: Session,
) -> UserDB:
    from app.auth.jwt_handler import verify_token

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

    return user


async def authenticate_user(
    username: str,
    password: str,
    db: Session,
) -> Optional[UserDB]:
    """
    Authenticate via username/password (local mode only).
    Returns the user if credentials are valid, None otherwise.
    """
    from app.auth.jwt_handler import verify_password

    user = db.query(UserDB).filter(UserDB.username == username).first()
    if not user or not user.active:
        return None

    # If the user has a hashed password, verify it
    if hasattr(user, "hashed_password") and user.hashed_password:
        if not verify_password(password, user.hashed_password):
            return None
        return user

    # Dev fallback: accept any password for existing users without a hashed password
    return user


# ── Unified dependency ──────────────────────────────────────────────

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> UserDB:
    """
    FastAPI dependency — resolves the current user from the Bearer token.
    Delegates to Keycloak or local JWT handler based on AUTH_PROVIDER.
    """
    token = credentials.credentials

    if is_keycloak_enabled():
        user = await _get_user_keycloak(token, db)
    else:
        user = await _get_user_local(token, db)

    if not user.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    return user
