"""
User management API endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.db.postgres_client import get_db
from app.models.user import User, UserCreate, UserUpdate
from app.models.user_db import UserDB

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("", response_model=List[User])
def get_users(
    skip: int = 0,
    limit: int = 100,
    active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """
    Get list of users with optional filtering.
    
    Args:
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return
        active: Filter by active status (optional)
    
    Returns:
        List of user objects
    """
    query = db.query(UserDB)
    
    if active is not None:
        query = query.filter(UserDB.active == active)
    
    users = query.offset(skip).limit(limit).all()
    # Convert UUID to string for response
    return [User(
        id=str(user.id),
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        display_name=user.display_name,
        ldap_dn=user.ldap_dn,
        roles=user.roles or [],
        groups=user.groups or [],
        active=user.active,
        last_sync=user.last_sync,
        created_at=user.created_at,
        updated_at=user.updated_at
    ) for user in users]


@router.get("/{user_id}", response_model=User)
def get_user(user_id: UUID, db: Session = Depends(get_db)):
    """
    Get a specific user by ID.
    
    Args:
        user_id: UUID of the user
    
    Returns:
        User object
    
    Raises:
        404: If user not found
    """
    user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )
    return User(
        id=str(user.id),
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        display_name=user.display_name,
        ldap_dn=user.ldap_dn,
        roles=user.roles or [],
        groups=user.groups or [],
        active=user.active,
        last_sync=user.last_sync,
        created_at=user.created_at,
        updated_at=user.updated_at
    )


@router.get("/username/{username}", response_model=User)
def get_user_by_username(username: str, db: Session = Depends(get_db)):
    """
    Get a user by username.
    
    Args:
        username: Username of the user
    
    Returns:
        User object
    
    Raises:
        404: If user not found
    """
    user = db.query(UserDB).filter(UserDB.username == username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with username {username} not found"
        )
    return User(
        id=str(user.id),
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        display_name=user.display_name,
        ldap_dn=user.ldap_dn,
        roles=user.roles or [],
        groups=user.groups or [],
        active=user.active,
        last_sync=user.last_sync,
        created_at=user.created_at,
        updated_at=user.updated_at
    )


@router.post("", response_model=User, status_code=status.HTTP_201_CREATED)
def create_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Create a new user.
    
    Args:
        user_data: User creation data
    
    Returns:
        Created user object
    
    Raises:
        400: If username or email already exists
    """
    # Check if username already exists
    existing_user = db.query(UserDB).filter(UserDB.username == user_data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username {user_data.username} already exists"
        )
    
    # Check if email already exists
    existing_email = db.query(UserDB).filter(UserDB.email == user_data.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Email {user_data.email} already exists"
        )
    
    # Create new user
    db_user = UserDB(
        username=user_data.username,
        email=user_data.email,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        display_name=user_data.display_name,
        ldap_dn=user_data.ldap_dn,
        roles=user_data.roles,
        groups=user_data.groups,
        active=True
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return User(
        id=str(db_user.id),
        username=db_user.username,
        email=db_user.email,
        first_name=db_user.first_name,
        last_name=db_user.last_name,
        display_name=db_user.display_name,
        ldap_dn=db_user.ldap_dn,
        roles=db_user.roles or [],
        groups=db_user.groups or [],
        active=db_user.active,
        last_sync=db_user.last_sync,
        created_at=db_user.created_at,
        updated_at=db_user.updated_at
    )


@router.put("/{user_id}", response_model=User)
def update_user(
    user_id: UUID,
    user_data: UserUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an existing user.
    
    Args:
        user_id: UUID of the user to update
        user_data: User update data
    
    Returns:
        Updated user object
    
    Raises:
        404: If user not found
        400: If email already exists (when updating email)
    """
    user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )
    
    # Check email uniqueness if email is being updated
    if user_data.email and user_data.email != user.email:
        existing_email = db.query(UserDB).filter(
            UserDB.email == user_data.email,
            UserDB.id != user_id
        ).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Email {user_data.email} already exists"
            )
        user.email = user_data.email
    
    # Update other fields
    if user_data.first_name is not None:
        user.first_name = user_data.first_name
    if user_data.last_name is not None:
        user.last_name = user_data.last_name
    if user_data.display_name is not None:
        user.display_name = user_data.display_name
    if user_data.roles is not None:
        user.roles = user_data.roles
    if user_data.groups is not None:
        user.groups = user_data.groups
    if user_data.active is not None:
        user.active = user_data.active
    
    db.commit()
    db.refresh(user)
    
    return User(
        id=str(user.id),
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        display_name=user.display_name,
        ldap_dn=user.ldap_dn,
        roles=user.roles or [],
        groups=user.groups or [],
        active=user.active,
        last_sync=user.last_sync,
        created_at=user.created_at,
        updated_at=user.updated_at
    )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: UUID, db: Session = Depends(get_db)):
    """
    Delete a user (soft delete by setting active=False).
    
    Args:
        user_id: UUID of the user to delete
    
    Raises:
        404: If user not found
    """
    user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )
    
    # Soft delete
    user.active = False
    db.commit()
    
    return None

