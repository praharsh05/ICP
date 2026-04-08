"""
Centralized application settings.

All configuration is driven by environment variables. Set AUTH_PROVIDER
to switch between authentication backends:

  AUTH_PROVIDER=keycloak   → validate Keycloak OIDC tokens (default)
  AUTH_PROVIDER=local      → use local JWT tokens with username/password login
"""
import os


# ── Auth provider flag ──────────────────────────────────────────────
AUTH_PROVIDER: str = os.getenv("AUTH_PROVIDER", "local").lower()

# ── Keycloak settings (only used when AUTH_PROVIDER=keycloak) ───────
KEYCLOAK_URL: str = os.getenv("KEYCLOAK_URL", "http://localhost:8080")
KEYCLOAK_REALM: str = os.getenv("KEYCLOAK_REALM", "icp")
KEYCLOAK_CLIENT_ID: str = os.getenv("KEYCLOAK_CLIENT_ID", "icp-frontend")

# ── Local JWT settings (only used when AUTH_PROVIDER=local) ─────────
JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
JWT_ALGORITHM: str = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))


def is_keycloak_enabled() -> bool:
    return AUTH_PROVIDER == "keycloak"
