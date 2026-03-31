"""
LDAP user model for mapping LDAP attributes
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class LDAPUser(BaseModel):
    """
    Model representing a user from LDAP directory
    """
    dn: str  # Distinguished Name
    username: str
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: Optional[str] = None
    groups: List[str] = Field(default_factory=list)
    attributes: Dict[str, Any] = Field(default_factory=dict)
    
    @classmethod
    def from_ldap_entry(cls, entry_dict: Dict[str, Any], config) -> 'LDAPUser':
        """
        Create LDAPUser from LDAP entry dictionary
        """
        return cls(
            dn=entry_dict.get('dn', ''),
            username=entry_dict.get(config.username_attribute, ''),
            email=entry_dict.get(config.email_attribute),
            first_name=entry_dict.get(config.first_name_attribute),
            last_name=entry_dict.get(config.last_name_attribute),
            display_name=entry_dict.get(config.display_name_attribute),
            groups=entry_dict.get(config.groups_attribute, []),
            attributes=entry_dict
        )



