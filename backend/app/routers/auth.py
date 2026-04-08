"""
Authentication API endpoints.

Behaviour depends on the AUTH_PROVIDER flag:
  keycloak → exposes /keycloak-config; login is handled by Keycloak redirect
  local    → exposes /login (username + password → JWT)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta

from app.config import is_keycloak_enabled, KEYCLOAK_URL, KEYCLOAK_REALM, KEYCLOAK_CLIENT_ID
from app.auth.authentication import get_current_user, authenticate_user
from app.models.user import User
from app.models.user_db import UserDB

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


@router.get("/me", response_model=User)
async def get_current_user_info(
    current_user: UserDB = Depends(get_current_user),
):
    return current_user


@router.get("/provider")
async def auth_provider():
    provider = "keycloak" if is_keycloak_enabled() else "local"
    return {"provider": provider}


@router.post("/logout")
async def logout():
    if is_keycloak_enabled():
        return {
            "message": "Call keycloak.logout() on the frontend to end the Keycloak session.",
            "keycloak_logout_url": (
                f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}"
                "/protocol/openid-connect/logout"
            ),
        }
    return {"message": "Discard the token on the client side."}


@router.get("/keycloak-config")
async def keycloak_config():
    if not is_keycloak_enabled():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Keycloak is not enabled. Set AUTH_PROVIDER=keycloak to use this endpoint.",
        )
    return {
        "url": KEYCLOAK_URL.replace("keycloak", "localhost"),
        "realm": KEYCLOAK_REALM,
        "clientId": KEYCLOAK_CLIENT_ID,
    }


@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    if is_keycloak_enabled():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Local login is disabled. Use Keycloak login flow instead.",
        )

    from app.auth.jwt_handler import create_access_token

    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": user.username, "email": user.email, "roles": user.roles},
        expires_delta=timedelta(minutes=30),
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "display_name": user.display_name,
            "roles": user.roles,
            "groups": user.groups,
        },
    }
