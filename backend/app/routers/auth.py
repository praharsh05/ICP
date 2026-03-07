"""
Authentication API endpoints (Keycloak SSO)

Login is handled entirely by Keycloak. The frontend redirects to Keycloak's
login page, obtains an OIDC access token, and sends it as a Bearer token to
these endpoints.
"""
import os
from fastapi import APIRouter, Depends

from app.auth.authentication import get_current_user
from app.models.user import User
from app.models.user_db import UserDB

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])

KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://keycloak:8080")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "icp")
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "icp-frontend")


@router.get("/me", response_model=User)
async def get_current_user_info(
    current_user: UserDB = Depends(get_current_user),
):
    """
    Return current user info extracted from the Keycloak Bearer token.
    The user record is auto-created / synced on every call.
    """
    return current_user


@router.get("/keycloak-config")
async def keycloak_config():
    """
    Return the Keycloak configuration needed by the frontend.
    Allows the frontend to be configured at runtime from the backend.
    """
    return {
        "url": KEYCLOAK_URL.replace("keycloak", "localhost"),  # internal → browser URL
        "realm": KEYCLOAK_REALM,
        "clientId": KEYCLOAK_CLIENT_ID,
    }


@router.post("/logout")
async def logout():
    """
    Logout hint.  The frontend must call keycloak.logout() to invalidate the
    Keycloak session — this endpoint exists only for API completeness.
    """
    return {
        "message": "Call keycloak.logout() on the frontend to end the Keycloak session.",
        "keycloak_logout_url": (
            f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}"
            "/protocol/openid-connect/logout"
        ),
    }
