#!/bin/bash
# Script to populate OpenLDAP with test users and groups

LDAP_HOST="${LDAP_HOST:-openldap}"
LDAP_PORT="${LDAP_PORT:-389}"
ADMIN_DN="cn=admin,dc=icp,dc=local"
ADMIN_PW="admin"
BASE_DN="dc=icp,dc=local"

echo "Setting up OpenLDAP users and groups..."

# Create organizational units
ldapadd -x -H ldap://${LDAP_HOST}:${LDAP_PORT} -D "${ADMIN_DN}" -w "${ADMIN_PW}" <<EOF
dn: ou=users,${BASE_DN}
objectClass: organizationalUnit
ou: users

dn: ou=groups,${BASE_DN}
objectClass: organizationalUnit
ou: groups
EOF

# Create test users
ldapadd -x -H ldap://${LDAP_HOST}:${LDAP_PORT} -D "${ADMIN_DN}" -w "${ADMIN_PW}" <<EOF
dn: uid=testuser,ou=users,${BASE_DN}
objectClass: inetOrgPerson
objectClass: posixAccount
objectClass: shadowAccount
uid: testuser
sn: User
givenName: Test
cn: Test User
displayName: Test User
mail: test@example.com
uidNumber: 1000
gidNumber: 1000
userPassword: testpass
homeDirectory: /home/testuser
loginShell: /bin/bash

dn: uid=newuser,ou=users,${BASE_DN}
objectClass: inetOrgPerson
objectClass: posixAccount
objectClass: shadowAccount
uid: newuser
sn: User
givenName: New
cn: New User
displayName: New User
mail: newuser@example.com
uidNumber: 1001
gidNumber: 1001
userPassword: newpass
homeDirectory: /home/newuser
loginShell: /bin/bash

dn: uid=adminuser,ou=users,${BASE_DN}
objectClass: inetOrgPerson
objectClass: posixAccount
objectClass: shadowAccount
uid: adminuser
sn: Admin
givenName: Admin
cn: Admin User
displayName: Admin User
mail: admin@example.com
uidNumber: 1002
gidNumber: 1002
userPassword: adminpass
homeDirectory: /home/adminuser
loginShell: /bin/bash
EOF

# Create groups
ldapadd -x -H ldap://${LDAP_HOST}:${LDAP_PORT} -D "${ADMIN_DN}" -w "${ADMIN_PW}" <<EOF
dn: cn=admins,ou=groups,${BASE_DN}
objectClass: posixGroup
objectClass: groupOfNames
cn: admins
gidNumber: 2000
member: uid=adminuser,ou=users,${BASE_DN}
member: uid=testuser,ou=users,${BASE_DN}

dn: cn=developers,ou=groups,${BASE_DN}
objectClass: posixGroup
objectClass: groupOfNames
cn: developers
gidNumber: 2001
member: uid=newuser,ou=users,${BASE_DN}
member: uid=testuser,ou=users,${BASE_DN}

dn: cn=users,ou=groups,${BASE_DN}
objectClass: posixGroup
objectClass: groupOfNames
cn: users
gidNumber: 2002
member: uid=newuser,ou=users,${BASE_DN}
member: uid=testuser,ou=users,${BASE_DN}
member: uid=adminuser,ou=users,${BASE_DN}
EOF

echo "OpenLDAP setup complete!"



