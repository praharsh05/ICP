"""
Role mapping service for LDAP groups to application roles
"""
import os
import yaml
import re
from typing import List, Dict, Set
from pathlib import Path


class RoleMappingService:
    """
    Service for mapping LDAP groups to application roles
    """
    
    def __init__(self, config_path: str = None):
        """
        Initialize role mapping service.
        
        Args:
            config_path: Path to role mapping YAML file
        """
        self.config_path = config_path or os.getenv(
            "ROLE_MAPPING_CONFIG",
            "backend/config/role_mapping.yaml"
        )
        self.mapping_config = self._load_config()
    
    def _load_config(self) -> Dict:
        """
        Load role mapping configuration from YAML file.
        
        Returns:
            Dictionary with role mapping configuration
        """
        # Try to load from config file
        config_file = Path(self.config_path)
        
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    config = yaml.safe_load(f)
                    return config.get('role_mapping', {})
            except Exception as e:
                print(f"Warning: Could not load role mapping config: {e}")
        
        # Return default empty config
        return {
            "default": ["viewer"]
        }
    
    def map_groups_to_roles(self, ldap_groups: List[str]) -> List[str]:
        """
        Map LDAP groups to application roles.
        
        Args:
            ldap_groups: List of LDAP group DNs or names
        
        Returns:
            List of application roles
        """
        if not ldap_groups:
            return self.mapping_config.get("default", ["viewer"])
        
        roles: Set[str] = set()
        
        # Direct mapping
        direct_mapping = {k: v for k, v in self.mapping_config.items() 
                         if k not in ["patterns", "default"]}
        
        for group in ldap_groups:
            # Check for exact match
            if group in direct_mapping:
                roles.update(direct_mapping[group])
            
            # Check pattern-based mapping
            patterns = self.mapping_config.get("patterns", [])
            for pattern_config in patterns:
                pattern = pattern_config.get("pattern", "")
                if pattern and re.match(pattern, group, re.IGNORECASE):
                    roles.update(pattern_config.get("roles", []))
        
        # If no roles found, use default
        if not roles:
            roles.update(self.mapping_config.get("default", ["viewer"]))
        
        return sorted(list(roles))
    
    def get_roles_for_user(self, ldap_groups: List[str]) -> List[str]:
        """
        Get roles for a user based on their LDAP groups.
        Alias for map_groups_to_roles for clarity.
        
        Args:
            ldap_groups: List of LDAP group DNs or names
        
        Returns:
            List of application roles
        """
        return self.map_groups_to_roles(ldap_groups)


# Global instance
role_mapping_service = RoleMappingService()





