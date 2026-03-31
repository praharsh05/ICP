"""
Role-Based Access Control (RBAC) middleware and dependencies
"""
from fastapi import HTTPException, Depends, status
from typing import List, Optional
from functools import wraps

from app.auth.authentication import get_current_user
from app.models.user_db import UserDB


def require_roles(*allowed_roles: str):
    """
    Dependency factory for requiring specific roles.
    
    Usage:
        @router.get("/admin-only")
        def admin_endpoint(user: UserDB = Depends(require_roles("admin"))):
            ...
    
    Args:
        *allowed_roles: Roles that are allowed to access the endpoint
    
    Returns:
        Dependency function that checks user roles
    """
    def role_checker(current_user: UserDB = Depends(get_current_user)) -> UserDB:
        user_roles = current_user.roles or []
        
        # Check if user has any of the allowed roles
        if not any(role in user_roles for role in allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(allowed_roles)}"
            )
        
        return current_user
    
    return role_checker


def require_any_role(*allowed_roles: str):
    """
    Alias for require_roles for clarity.
    """
    return require_roles(*allowed_roles)


def require_all_roles(*required_roles: str):
    """
    Dependency factory for requiring all specified roles.
    
    Usage:
        @router.get("/super-admin")
        def super_admin_endpoint(user: UserDB = Depends(require_all_roles("admin", "super"))):
            ...
    
    Args:
        *required_roles: All roles that must be present
    
    Returns:
        Dependency function that checks user roles
    """
    def role_checker(current_user: UserDB = Depends(get_current_user)) -> UserDB:
        user_roles = current_user.roles or []
        
        # Check if user has all required roles
        if not all(role in user_roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required all roles: {', '.join(required_roles)}"
            )
        
        return current_user
    
    return role_checker


# Common role checkers
require_admin = require_roles("admin")
require_manager = require_roles("manager", "admin")
require_developer = require_roles("developer", "admin")





