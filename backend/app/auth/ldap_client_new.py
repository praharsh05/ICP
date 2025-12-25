"""
LDAP Client for authentication and user management
"""
from typing import Optional, List, Dict, Any
from ldap3 import Server, Connection, ALL, SUBTREE
from app.auth.ldap_config import LDAPConfig
from app.models.ldap_user import LDAPUser


class LDAPClient:
    """
    LDAP client for user authentication and search operations
    """
    
    def __init__(self):
        self.config = LDAPConfig()
        self._connection: Optional[Connection] = None
    
    def _get_connection(self) -> Connection:
        """
        Get or create LDAP connection.
        
        Returns:
            LDAP Connection object
        """
        if self._connection and self._connection.bound:
            return self._connection
        
        server = Server(
            self.config.host,
            port=self.config.port,
            use_ssl=self.config.use_ssl,
            get_info=ALL
        )
        
        connection = Connection(
            server,
            user=self.config.bind_dn,
            password=self.config.bind_password,
            auto_bind=True,
            raise_exceptions=False
        )
        
        if not connection.bound:
            raise Exception(f"Failed to bind to LDAP server: {connection.result}")
        
        self._connection = connection
        return connection
    
    def authenticate(self, username: str, password: str) -> Optional[LDAPUser]:
        """
        Authenticate a user with LDAP.
        
        Args:
            username: Username to authenticate
            password: Password to verify
        
        Returns:
            LDAPUser object if authentication successful, None otherwise
        """
        try:
            # First, search for the user
            user_dn = self._find_user_dn(username)
            if not user_dn:
                return None
            
            # Try to bind with user credentials
            server = Server(
                self.config.host,
                port=self.config.port,
                use_ssl=self.config.use_ssl,
                get_info=ALL
            )
            
            user_conn = Connection(
                server,
                user=user_dn,
                password=password,
                auto_bind=True,
                raise_exceptions=False
            )
            
            if not user_conn.bound:
                return None
            
            # Get user attributes - need to use admin connection to read attributes
            admin_conn = self._get_connection()
            admin_conn.search(
                user_dn,
                '(objectClass=*)',
                attributes=self.config.user_attributes
            )
            
            if admin_conn.entries:
                entry = admin_conn.entries[0]
                entry_dict = self._entry_to_dict(entry, user_dn)
                user_conn.unbind()
                return LDAPUser.from_ldap_entry(entry_dict, self.config)
            
            user_conn.unbind()
            return None
            
        except Exception as e:
            print(f"LDAP authentication error: {e}")
            return None
    
    def _find_user_dn(self, username: str) -> Optional[str]:
        """
        Find the distinguished name (DN) for a username.
        
        Args:
            username: Username to search for
        
        Returns:
            Distinguished name if found, None otherwise
        """
        try:
            conn = self._get_connection()
            search_filter = f"({self.config.username_attribute}={username})"
            search_base = self.config.user_search_base or self.config.base_dn
            
            conn.search(
                search_base,
                search_filter,
                search_scope=SUBTREE,
                attributes=['distinguishedName', self.config.username_attribute]
            )
            
            if conn.entries:
                return str(conn.entries[0].entry_dn)
            
            return None
            
        except Exception as e:
            print(f"Error finding user DN: {e}")
            return None
    
    def search_users(self, filter_str: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for users in LDAP.
        
        Args:
            filter_str: Optional LDAP filter string
        
        Returns:
            List of user dictionaries
        """
        try:
            conn = self._get_connection()
            search_filter = filter_str or self.config.user_filter
            search_base = self.config.user_search_base or self.config.base_dn
            
            # Ensure we include memberOf in attributes for group lookup
            attrs = list(set(self.config.user_attributes + [self.config.groups_attribute]))
            
            conn.search(
                search_base,
                search_filter,
                search_scope=SUBTREE,
                attributes=attrs
            )
            
            users = []
            for entry in conn.entries:
                entry_dict = self._entry_to_dict(entry, str(entry.entry_dn))
                users.append(entry_dict)
            
            return users
            
        except Exception as e:
            print(f"Error searching LDAP users: {e}")
            return []
    
    def get_user_by_dn(self, user_dn: str) -> Optional[Dict[str, Any]]:
        """
        Get a user by their distinguished name.
        
        Args:
            user_dn: Distinguished name of the user
        
        Returns:
            User dictionary if found, None otherwise
        """
        try:
            conn = self._get_connection()
            attrs = list(set(self.config.user_attributes + [self.config.groups_attribute]))
            
            conn.search(
                user_dn,
                '(objectClass=*)',
                attributes=attrs
            )
            
            if conn.entries:
                entry = conn.entries[0]
                return self._entry_to_dict(entry, user_dn)
            
            return None
            
        except Exception as e:
            print(f"Error getting user by DN: {e}")
            return None
    
    def _entry_to_dict(self, entry, dn: str) -> Dict[str, Any]:
        """
        Convert LDAP entry to dictionary.
        
        Args:
            entry: LDAP entry object
            dn: Distinguished name
        
        Returns:
            Dictionary with user attributes
        """
        entry_dict = {'dn': dn}
        
        for attr in self.config.user_attributes:
            if hasattr(entry, attr):
                value = getattr(entry, attr).value if hasattr(getattr(entry, attr), 'value') else getattr(entry, attr)
                if isinstance(value, list) and len(value) > 0:
                    entry_dict[attr] = [str(v) for v in value]
                elif value:
                    entry_dict[attr] = str(value)
                else:
                    entry_dict[attr] = None
            else:
                entry_dict[attr] = None
        
        # Extract username
        username_attr = self.config.username_attribute
        if username_attr in entry_dict and entry_dict[username_attr]:
            if isinstance(entry_dict[username_attr], list):
                entry_dict['username'] = entry_dict[username_attr][0]
            else:
                entry_dict['username'] = entry_dict[username_attr]
        else:
            entry_dict['username'] = None
        
        # For OpenLDAP, memberOf might not be populated automatically
        # We need to search for groups that contain this user
        if not entry_dict.get(self.config.groups_attribute) or not entry_dict[self.config.groups_attribute]:
            groups = self._get_user_groups(dn)
            entry_dict[self.config.groups_attribute] = groups
        
        return entry_dict
    
    def _get_user_groups(self, user_dn: str) -> List[str]:
        """
        Get groups that a user belongs to by searching for groups with this user as a member.
        This is needed for OpenLDAP where memberOf is not automatically populated.
        
        Args:
            user_dn: Distinguished name of the user
        
        Returns:
            List of group DNs
        """
        try:
            conn = self._get_connection()
            groups = []
            
            # Search for groups that have this user as a member
            search_filter = f"(&(objectClass=groupOfNames)(member={user_dn}))"
            search_base = f"ou=groups,{self.config.base_dn}"
            
            conn.search(
                search_base,
                search_filter,
                search_scope=SUBTREE,
                attributes=['dn', 'cn']
            )
            
            for entry in conn.entries:
                groups.append(str(entry.entry_dn))
            
            # Also try posixGroup
            username = user_dn.split(',')[0].split('=')[1] if '=' in user_dn.split(',')[0] else user_dn
            search_filter = f"(&(objectClass=posixGroup)(memberUid={username}))"
            conn.search(
                search_base,
                search_filter,
                search_scope=SUBTREE,
                attributes=['cn']
            )
            
            for entry in conn.entries:
                group_dn = str(entry.entry_dn)
                if group_dn not in groups:
                    groups.append(group_dn)
            
            return groups
            
        except Exception as e:
            print(f"Error getting user groups: {e}")
            return []
    
    def close(self):
        """Close LDAP connection"""
        if self._connection:
            self._connection.unbind()
            self._connection = None



