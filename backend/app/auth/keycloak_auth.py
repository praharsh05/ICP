"""
Keycloak OIDC token validation.

Validates Keycloak-issued JWTs using the realm's public keys (JWKS endpoint).
Only active when AUTH_PROVIDER=keycloak.
"""
import httpx
from typing import Optional, Dict, Any
from jose import jwt, JWTError
from fastapi import HTTPException, status

from app.config import KEYCLOAK_URL, KEYCLOAK_REALM, KEYCLOAK_CLIENT_ID

JWKS_URL = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs"

# In-memory JWKS cache — refreshed when a key mismatch is detected
_jwks_cache: Optional[Dict] = None


async def _fetch_jwks() -> Dict:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(JWKS_URL)
        response.raise_for_status()
        return response.json()


async def get_jwks() -> Dict:
    """Return cached JWKS, fetching from Keycloak on first call."""
    global _jwks_cache
    if _jwks_cache is None:
        _jwks_cache = await _fetch_jwks()
    return _jwks_cache


def _clear_jwks_cache():
    global _jwks_cache
    _jwks_cache = None


async def verify_keycloak_token(token: str) -> Dict[str, Any]:
    """
    Verify a Keycloak access token and return its claims.

    Raises HTTPException 401 on any validation failure.
    """
    try:
        unverified_header = jwt.get_unverified_header(token)
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Malformed token header: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    kid = unverified_header.get("kid")

    async def _find_key(jwks: Dict) -> Optional[Dict]:
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                return key
        return None

    # First attempt with cached JWKS
    jwks = await get_jwks()
    matching_key = await _find_key(jwks)

    if matching_key is None:
        # Key not found — refresh and try once more (handles key rotation)
        _clear_jwks_cache()
        jwks = await get_jwks()
        matching_key = await _find_key(jwks)

    if matching_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No matching public key found for token kid",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(
            token,
            matching_key,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation failed: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )


# Built-in Keycloak roles that are not application-level roles
_SYSTEM_ROLES = {
    "offline_access",
    "uma_authorization",
    f"default-roles-{KEYCLOAK_REALM}",
}


def extract_user_info(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract standardized user information from Keycloak token claims.
    """
    realm_access = payload.get("realm_access", {})
    all_roles = realm_access.get("roles", [])
    app_roles = [r for r in all_roles if r not in _SYSTEM_ROLES]

    return {
        "sub": payload.get("sub"),
        "username": payload.get("preferred_username"),
        "email": payload.get("email"),
        "first_name": payload.get("given_name"),
        "last_name": payload.get("family_name"),
        "display_name": payload.get("name"),
        "roles": app_roles,
        "groups": payload.get("groups", []),
    }
