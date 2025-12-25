"""
Authentication API endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from app.db.postgres_client import get_db
from app.auth.authentication import authenticate_user, get_current_user
from app.auth.jwt_handler import create_access_token
from app.models.user import User
from app.models.user_db import UserDB

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return JWT token.
    
    Args:
        form_data: OAuth2 password form with username and password
    
    Returns:
        Access token and token type
    
    Raises:
        401: If authentication fails
    """
    user = await authenticate_user(form_data.username, form_data.password, db)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user.username, "email": user.email, "roles": user.roles},
        expires_delta=access_token_expires
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
            "groups": user.groups
        }
    }


@router.get("/me", response_model=User)
async def get_current_user_info(
    current_user: UserDB = Depends(get_current_user)
):
    """
    Get current authenticated user information.
    
    Returns:
        Current user object
    """
    return current_user


@router.post("/logout")
async def logout():
    """
    Logout endpoint (client should discard token).
    
    Note: JWT tokens are stateless, so logout is handled client-side
    by discarding the token. This endpoint exists for API consistency.
    """
    return {"message": "Successfully logged out"}





