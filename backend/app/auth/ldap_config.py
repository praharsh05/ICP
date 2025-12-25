"""
LDAP Configuration Management
"""
import os
from typing import List, Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class LDAPConfig(BaseSettings):
    """
    LDAP configuration settings
    """
    # Server configuration
    host: str = Field(default="localhost", env="LDAP_HOST")
    port: int = Field(default=389, env="LDAP_PORT")
    use_ssl: bool = Field(default=False, env="LDAP_USE_SSL")
    use_tls: bool = Field(default=True, env="LDAP_USE_TLS")
    validate_cert: bool = Field(default=True, env="LDAP_VALIDATE_CERT")
    timeout: int = Field(default=10, env="LDAP_TIMEOUT")
    
    # Bind credentials
    bind_dn: str = Field(default="", env="LDAP_BIND_DN")
    bind_password: str = Field(default="", env="LDAP_BIND_PASSWORD")
    
    # Search configuration
    base_dn: str = Field(default="", env="LDAP_BASE_DN")
    user_search_base: str = Field(default="", env="LDAP_USER_SEARCH_BASE")
    user_filter: str = Field(default="(objectClass=inetOrgPerson)", env="LDAP_USER_FILTER")
    
    # Attribute mapping
    username_attribute: str = Field(default="sAMAccountName", env="LDAP_USERNAME_ATTR")
    email_attribute: str = Field(default="mail", env="LDAP_EMAIL_ATTR")
    first_name_attribute: str = Field(default="givenName", env="LDAP_FIRST_NAME_ATTR")
    last_name_attribute: str = Field(default="sn", env="LDAP_LAST_NAME_ATTR")
    display_name_attribute: str = Field(default="displayName", env="LDAP_DISPLAY_NAME_ATTR")
    groups_attribute: str = Field(default="memberOf", env="LDAP_GROUPS_ATTR")
    
    # User attributes to retrieve
    user_attributes: List[str] = Field(
        default=[
            "uid",
            "mail",
            "givenName",
            "sn",
            "cn",
            "displayName",
            "memberOf",
            "distinguishedName"
        ]
    )
    
    # Sync configuration
    sync_enabled: bool = Field(default=True, env="LDAP_SYNC_ENABLED")
    sync_interval_hours: int = Field(default=24, env="LDAP_SYNC_INTERVAL_HOURS")
    sync_batch_size: int = Field(default=100, env="LDAP_SYNC_BATCH_SIZE")
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",  # Ignore extra environment variables
        "env_prefix": "",  # No prefix needed
        "env_ignore_empty": True
    }
    
    def __init__(self, **kwargs):
        # Prioritize environment variables over .env file
        import os
        super().__init__(**kwargs)
        # Override with environment variables if they exist
        if os.getenv("LDAP_HOST"):
            self.host = os.getenv("LDAP_HOST")
        if os.getenv("LDAP_PORT"):
            self.port = int(os.getenv("LDAP_PORT"))
        if os.getenv("LDAP_BIND_DN"):
            self.bind_dn = os.getenv("LDAP_BIND_DN")
        if os.getenv("LDAP_BIND_PASSWORD"):
            self.bind_password = os.getenv("LDAP_BIND_PASSWORD")
        if os.getenv("LDAP_BASE_DN"):
            self.base_dn = os.getenv("LDAP_BASE_DN")
        if os.getenv("LDAP_USER_SEARCH_BASE"):
            self.user_search_base = os.getenv("LDAP_USER_SEARCH_BASE")
        if os.getenv("LDAP_USERNAME_ATTR"):
            self.username_attribute = os.getenv("LDAP_USERNAME_ATTR")


def get_ldap_config() -> LDAPConfig:
    """
    Get LDAP configuration instance
    """
    return LDAPConfig()



