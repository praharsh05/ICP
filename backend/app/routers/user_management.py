"""
User management endpoints (activation, password reset, etc.)
"""
import os
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID
from datetime import datetime, timedelta
import secrets

from app.db.postgres_client import get_db
from app.models.user_db import UserDB
from app.auth.authentication import get_current_user
from app.auth.jwt_handler import create_access_token
from app.services.email_service import email_service
from pydantic import BaseModel, EmailStr

router = APIRouter(prefix="/api/v1/user-management", tags=["user-management"])


class PasswordResetRequest(BaseModel):
    """Password reset request model"""
    email: EmailStr


class PasswordReset(BaseModel):
    """Password reset model"""
    token: str
    new_password: str


class UserActivationRequest(BaseModel):
    """User activation request model"""
    user_id: UUID
    active: bool


@router.post("/activate")
async def activate_user(
    request: UserActivationRequest,
    current_user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Activate or deactivate a user.
    Requires admin role.
    
    Args:
        request: User activation request
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Updated user object
    
    Raises:
        403: If user doesn't have admin role
        404: If user not found
    """
    # Check if current user has admin role
    if "admin" not in (current_user.roles or []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can activate/deactivate users"
        )
    
    user = db.query(UserDB).filter(UserDB.id == request.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {request.user_id} not found"
        )
    
    user.active = request.active
    db.commit()
    db.refresh(user)
    
    return {
        "message": f"User {'activated' if request.active else 'deactivated'} successfully",
        "user_id": str(user.id),
        "active": user.active
    }


@router.post("/request-password-reset")
async def request_password_reset(
    request: PasswordResetRequest,
    db: Session = Depends(get_db)
):
    """
    Request a password reset token.
    Note: In a real implementation, this would send an email.
    For now, it returns a token (in production, send via email).
    
    Args:
        request: Password reset request with email
        db: Database session
    
    Returns:
        Message indicating reset token was generated
    """
    user = db.query(UserDB).filter(UserDB.email == request.email).first()
    
    # Always return success message (security: don't reveal if email exists)
    if user:
        # Generate reset token (in production, store this with expiration in database)
        reset_token = secrets.token_urlsafe(32)
        
        # Send password reset email
        email_sent = email_service.send_password_reset_email(
            to_email=user.email,
            reset_token=reset_token,
            username=user.username
        )
        
        if not email_sent:
            # Log token if email service is not configured
            print(f"[PASSWORD RESET] Token for {user.email}: {reset_token}")
            print(f"[PASSWORD RESET] Reset URL: {os.getenv('APP_URL', 'http://localhost:6693')}/reset-password?token={reset_token}")
    
    return {
        "message": "If the email exists, a password reset link has been sent",
        "note": "Check your email for the reset link. If email service is not configured, check server logs for the token."
    }


@router.post("/reset-password")
async def reset_password(
    reset_data: PasswordReset,
    db: Session = Depends(get_db)
):
    """
    Reset password using a reset token.
    Note: In production, validate token and expiration.
    
    Args:
        reset_data: Password reset data with token and new password
        db: Database session
    
    Returns:
        Success message
    """
    # In production: validate token from database
    # For now, this is a placeholder
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Password reset via token not yet implemented."
    )


@router.get("/my-roles")
async def get_my_roles(
    current_user: UserDB = Depends(get_current_user)
):
    """
    Get current user's roles and permissions.
    
    Args:
        current_user: Current authenticated user
    
    Returns:
        User roles and groups
    """
    return {
        "username": current_user.username,
        "roles": current_user.roles or [],
        "groups": current_user.groups or [],
        "active": current_user.active
    }


@router.post("/refresh-roles")
async def refresh_roles(
    current_user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Refresh user roles from groups.

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        Updated roles
    """
    from app.services.role_mapping import role_mapping_service

    # Re-map roles from current groups
    updated_roles = role_mapping_service.map_groups_to_roles(current_user.groups or [])

    current_user.roles = updated_roles
    db.commit()
    db.refresh(current_user)

    return {
        "message": "Roles refreshed from groups",
        "roles": current_user.roles,
        "groups": current_user.groups
    }

