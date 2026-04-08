"""
Authentication module — supports Keycloak OIDC and local JWT (flag-based).
"""
from .authentication import get_current_user, authenticate_user

__all__ = [
    "get_current_user",
    "authenticate_user",
]
