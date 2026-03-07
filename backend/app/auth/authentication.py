"""
Authentication via Keycloak OIDC tokens.

Validates Keycloak JWTs and auto-provisions users in PostgreSQL on first login.
"""
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.db.postgres_client import get_db
from app.models.user_db import UserDB
from app.auth.keycloak_auth import verify_keycloak_token, extract_user_info

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> UserDB:
    """
    Validate a Keycloak Bearer token and return the corresponding database user.

    On first login the user is auto-provisioned in PostgreSQL using claims from
    the Keycloak token. On subsequent logins, profile fields and roles are synced
    from the latest token claims.

    Raises:
        401: Token invalid or missing required claims.
        403: User account is disabled in the local database.
    """
    token = credentials.credentials
    payload = await verify_keycloak_token(token)
    user_info = extract_user_info(payload)

    keycloak_sub = user_info["sub"]
    if not keycloak_sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is missing the 'sub' claim",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Look up user by the stable Keycloak subject identifier
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

    if not user.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    return user
