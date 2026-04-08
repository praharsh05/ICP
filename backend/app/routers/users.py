"""
User management API endpoints
"""
from fastapi import APIRouter, HTTPException, status
from typing import List, Optional
from uuid import UUID

from app.db import user_store
from app.models.user import User, UserCreate, UserUpdate
from app.models.user_db import UserDB

router = APIRouter(prefix="/api/v1/users", tags=["users"])


def _to_user(u: UserDB) -> User:
    return User(
        id=str(u.id),
        username=u.username,
        email=u.email,
        first_name=u.first_name,
        last_name=u.last_name,
        display_name=u.display_name,
        roles=u.roles or [],
        groups=u.groups or [],
        active=u.active,
        created_at=u.created_at,
        updated_at=u.updated_at,
    )


@router.get("", response_model=List[User])
def get_users(skip: int = 0, limit: int = 100, active: Optional[bool] = None):
    users = user_store.list_users(skip=skip, limit=limit, active=active)
    return [_to_user(u) for u in users]


@router.get("/{user_id}", response_model=User)
def get_user(user_id: UUID):
    user = user_store.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with id {user_id} not found")
    return _to_user(user)


@router.get("/username/{username}", response_model=User)
def get_user_by_username(username: str):
    user = user_store.get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with username {username} not found")
    return _to_user(user)


@router.post("", response_model=User, status_code=status.HTTP_201_CREATED)
def create_user(user_data: UserCreate):
    if user_store.get_user_by_username(user_data.username):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Username {user_data.username} already exists")
    if user_store.get_user_by_email(user_data.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Email {user_data.email} already exists")

    new_user = UserDB(
        username=user_data.username,
        email=user_data.email,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        display_name=user_data.display_name,
        roles=user_data.roles,
        groups=user_data.groups,
    )
    user_store.save_user(new_user)
    return _to_user(new_user)


@router.put("/{user_id}", response_model=User)
def update_user(user_id: UUID, user_data: UserUpdate):
    user = user_store.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with id {user_id} not found")

    if user_data.email and user_data.email != user.email:
        existing = user_store.get_user_by_email(user_data.email)
        if existing and existing.id != user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Email {user_data.email} already exists")
        user.email = user_data.email
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

    user_store.save_user(user)
    return _to_user(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: UUID):
    user = user_store.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with id {user_id} not found")
    user.active = False
    user_store.save_user(user)
    return None
