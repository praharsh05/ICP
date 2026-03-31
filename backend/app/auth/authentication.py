"""
Authentication functions for LDAP and database users
"""
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.db.postgres_client import get_db
from app.models.user_db import UserDB
from app.auth.ldap_client_new import LDAPClient
from app.auth.jwt_handler import verify_token, create_access_token
from app.auth.ldap_config import LDAPConfig
from app.services.role_mapping import role_mapping_service

security = HTTPBearer()
ldap_config = LDAPConfig()


async def authenticate_user(
    username: str,
    password: str,
    db: Session
) -> Optional[UserDB]:
    """
    Authenticate a user via LDAP and return database user.
    Falls back to development mode if LDAP is not configured.
    
    Args:
        username: Username to authenticate
        password: Password to verify
        db: Database session
    
    Returns:
        UserDB object if authentication successful, None otherwise
    """
    # Check if LDAP is configured
    ldap_configured = bool(ldap_config.bind_dn and ldap_config.host != "localhost")
    
    # Try LDAP authentication first if configured
    if ldap_configured:
        ldap_client = LDAPClient()
        
        try:
            # Authenticate with LDAP
            ldap_user = ldap_client.authenticate(username, password)
            
            if ldap_user:
                # Find or create user in database
                db_user = db.query(UserDB).filter(UserDB.username == username).first()
                
                # Map LDAP groups to application roles
                mapped_roles = role_mapping_service.map_groups_to_roles(ldap_user.groups)
                
                if not db_user:
                    # Create new user from LDAP data
                    db_user = UserDB(
                        username=ldap_user.username,
                        email=ldap_user.email or f"{username}@example.com",
                        first_name=ldap_user.first_name,
                        last_name=ldap_user.last_name,
                        display_name=ldap_user.display_name,
                        ldap_dn=ldap_user.dn,
                        groups=ldap_user.groups,
                        roles=mapped_roles,  # Roles mapped from LDAP groups
                        active=True
                    )
                    db.add(db_user)
                    db.commit()
                    db.refresh(db_user)
                else:
                    # Update existing user with latest LDAP data
                    if ldap_user.email:
                        db_user.email = ldap_user.email
                    if ldap_user.first_name:
                        db_user.first_name = ldap_user.first_name
                    if ldap_user.last_name:
                        db_user.last_name = ldap_user.last_name
                    if ldap_user.display_name:
                        db_user.display_name = ldap_user.display_name
                    db_user.groups = ldap_user.groups
                    db_user.roles = mapped_roles  # Update roles from groups
                    db_user.ldap_dn = ldap_user.dn
                    db.commit()
                    db.refresh(db_user)
                
                return db_user
        except Exception as e:
            # LDAP authentication failed, try fallback
            print(f"LDAP authentication failed: {e}")
    
    # Development/Testing Fallback: Allow login for existing database users
    # This is useful when LDAP is not configured
    # In production, remove this fallback and require LDAP
    if not ldap_configured:
        # Check if user exists in database
        db_user = db.query(UserDB).filter(UserDB.username == username).first()
        
        if db_user and db_user.active:
            # For development: accept any password if user exists
            # In production, this should be removed or use a different method
            print(f"[DEV MODE] Authenticating user {username} without LDAP (development mode)")
            return db_user
    
    return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> UserDB:
    """
    Get current authenticated user from JWT token.
    
    Args:
        credentials: HTTP Bearer token credentials
        db: Database session
    
    Returns:
        UserDB object for authenticated user
    
    Raises:
        401: If token is invalid or user not found
    """
    token = credentials.credentials
    payload = verify_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    username: str = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(UserDB).filter(UserDB.username == username).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    return user

