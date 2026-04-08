"""
User management endpoints (activation, password reset, etc.)
"""
import os
from fastapi import APIRouter, HTTPException, Depends, status
from typing import Optional
from uuid import UUID
import secrets

from app.db import user_store
from app.models.user_db import UserDB
from app.auth.authentication import get_current_user
from app.services.email_service import email_service
from pydantic import BaseModel, EmailStr

router = APIRouter(prefix="/api/v1/user-management", tags=["user-management"])


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordReset(BaseModel):
    token: str
    new_password: str


class UserActivationRequest(BaseModel):
    user_id: UUID
    active: bool


@router.post("/activate")
async def activate_user(
    request: UserActivationRequest,
    current_user: UserDB = Depends(get_current_user),
):
    if "admin" not in (current_user.roles or []):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only administrators can activate/deactivate users")

    user = user_store.get_user_by_id(request.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with id {request.user_id} not found")

    user.active = request.active
    user_store.save_user(user)

    return {
        "message": f"User {'activated' if request.active else 'deactivated'} successfully",
        "user_id": str(user.id),
        "active": user.active,
    }


@router.post("/request-password-reset")
async def request_password_reset(request: PasswordResetRequest):
    user = user_store.get_user_by_email(request.email)

    if user:
        reset_token = secrets.token_urlsafe(32)
        email_sent = email_service.send_password_reset_email(
            to_email=user.email, reset_token=reset_token, username=user.username
        )
        if not email_sent:
            print(f"[PASSWORD RESET] Token for {user.email}: {reset_token}")
            print(f"[PASSWORD RESET] Reset URL: {os.getenv('APP_URL', 'http://localhost:6693')}/reset-password?token={reset_token}")

    return {
        "message": "If the email exists, a password reset link has been sent",
        "note": "Check your email for the reset link. If email service is not configured, check server logs for the token.",
    }


@router.post("/reset-password")
async def reset_password(reset_data: PasswordReset):
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Password reset via token not yet implemented.")


@router.get("/my-roles")
async def get_my_roles(current_user: UserDB = Depends(get_current_user)):
    return {
        "username": current_user.username,
        "roles": current_user.roles or [],
        "groups": current_user.groups or [],
        "active": current_user.active,
    }


@router.post("/refresh-roles")
async def refresh_roles(current_user: UserDB = Depends(get_current_user)):
    from app.services.role_mapping import role_mapping_service

    current_user.roles = role_mapping_service.map_groups_to_roles(current_user.groups or [])
    user_store.save_user(current_user)

    return {
        "message": "Roles refreshed from groups",
        "roles": current_user.roles,
        "groups": current_user.groups,
    }
