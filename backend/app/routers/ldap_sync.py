"""
LDAP synchronization endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.postgres_client import get_db
from app.models.user_db import UserDB
from app.auth.ldap_client_new import LDAPClient
from app.auth.ldap_config import LDAPConfig
from app.models.ldap_user import LDAPUser
from app.services.role_mapping import role_mapping_service

router = APIRouter(prefix="/api/v1/ldap", tags=["ldap"])

ldap_config = LDAPConfig()


@router.post("/sync")
async def sync_users_from_ldap(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Sync all users from LDAP to PostgreSQL database.
    
    This endpoint initiates a background task to sync users.
    
    Returns:
        Message indicating sync has started
    """
    if not ldap_config.sync_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="LDAP sync is disabled"
        )
    
    # Start background sync task
    background_tasks.add_task(sync_ldap_users_task, db)
    
    return {
        "message": "LDAP sync started in background",
        "status": "processing"
    }


@router.post("/sync/sync-now")
async def sync_users_now(
    db: Session = Depends(get_db)
):
    """
    Sync all users from LDAP to PostgreSQL database synchronously.
    
    Returns:
        Sync results with counts of created/updated users
    """
    if not ldap_config.sync_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="LDAP sync is disabled"
        )
    
    return await sync_ldap_users_task(db)


async def sync_ldap_users_task(db: Session):
    """
    Background task to sync users from LDAP.
    
    Args:
        db: Database session
    
    Returns:
        Dictionary with sync results
    """
    ldap_client = LDAPClient()
    created_count = 0
    updated_count = 0
    error_count = 0
    
    try:
        # Search for all users in LDAP
        ldap_users = ldap_client.search_users()
        
        for ldap_user_data in ldap_users:
            try:
                # Convert LDAP entry to LDAPUser model
                ldap_user = LDAPUser.from_ldap_entry(ldap_user_data, ldap_config)
                
                # Check if user exists in database
                db_user = db.query(UserDB).filter(
                    UserDB.username == ldap_user.username
                ).first()
                
                # Map LDAP groups to application roles
                mapped_roles = role_mapping_service.map_groups_to_roles(ldap_user.groups)
                
                if not db_user:
                    # Create new user
                    db_user = UserDB(
                        username=ldap_user.username,
                        email=ldap_user.email or f"{ldap_user.username}@example.com",
                        first_name=ldap_user.first_name,
                        last_name=ldap_user.last_name,
                        display_name=ldap_user.display_name,
                        ldap_dn=ldap_user.dn,
                        groups=ldap_user.groups,
                        roles=mapped_roles,  # Roles mapped from LDAP groups
                        active=True
                    )
                    db.add(db_user)
                    created_count += 1
                else:
                    # Update existing user
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
                    updated_count += 1
                
                db.commit()
                
            except Exception as e:
                error_count += 1
                print(f"Error syncing user {ldap_user_data.get('username', 'unknown')}: {e}")
                db.rollback()
                continue
        
        return {
            "status": "completed",
            "created": created_count,
            "updated": updated_count,
            "errors": error_count,
            "total_processed": created_count + updated_count + error_count
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "created": created_count,
            "updated": updated_count,
            "errors": error_count
        }


@router.get("/users")
async def list_ldap_users():
    """
    List all users found in LDAP (without syncing to database).
    
    Returns:
        List of LDAP users
    """
    ldap_client = LDAPClient()
    
    try:
        ldap_users = ldap_client.search_users()
        return {
            "users": ldap_users,
            "count": len(ldap_users)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error querying LDAP: {str(e)}"
        )

