"""
Database migration: LDAP → Keycloak SSO

Run this ONCE on an existing database that was using LDAP auth.
For a fresh installation, this is not needed — init_db.py will create
the correct schema automatically.

Usage:
  cd backend
  python scripts/migrate_to_keycloak.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db.postgres_client import engine
from sqlalchemy import text


def migrate():
    print("Running Keycloak migration on 'users' table...")

    with engine.connect() as conn:
        # Check if the table exists at all
        result = conn.execute(text(
            "SELECT to_regclass('public.users')"
        ))
        if result.scalar() is None:
            print("Table 'users' does not exist — run init_db.py first.")
            sys.exit(0)

        # Add keycloak_sub column if missing
        result = conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='users' AND column_name='keycloak_sub'"
        ))
        if result.fetchone() is None:
            conn.execute(text(
                "ALTER TABLE users ADD COLUMN keycloak_sub VARCHAR(255) UNIQUE"
            ))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_users_keycloak_sub ON users (keycloak_sub)"
            ))
            print("  + Added column: keycloak_sub")
        else:
            print("  ~ Column keycloak_sub already exists, skipping.")

        # Drop ldap_dn column if present (no longer needed)
        result = conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='users' AND column_name='ldap_dn'"
        ))
        if result.fetchone() is not None:
            conn.execute(text("ALTER TABLE users DROP COLUMN IF EXISTS ldap_dn"))
            print("  - Dropped column: ldap_dn")
        else:
            print("  ~ Column ldap_dn not found, skipping.")

        # Drop last_sync column if present (no longer needed)
        result = conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='users' AND column_name='last_sync'"
        ))
        if result.fetchone() is not None:
            conn.execute(text("ALTER TABLE users DROP COLUMN IF EXISTS last_sync"))
            print("  - Dropped column: last_sync")

        conn.commit()

    print("Migration complete.")


if __name__ == "__main__":
    migrate()
