"""
User models for the application
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
from uuid import UUID, uuid4


class UserBase(BaseModel):
    """Base user model"""
    username: str
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: Optional[str] = None


class UserCreate(UserBase):
    """User creation model"""
    roles: List[str] = Field(default_factory=list)
    groups: List[str] = Field(default_factory=list)


class UserUpdate(BaseModel):
    """User update model"""
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: Optional[str] = None
    roles: Optional[List[str]] = None
    groups: Optional[List[str]] = None
    active: Optional[bool] = None


class User(UserBase):
    """User model"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    roles: List[str] = Field(default_factory=list)
    groups: List[str] = Field(default_factory=list)
    active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True







