"""
Database initialization script
Creates all database tables
"""
import sys
import os

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.db.postgres_client import init_db, engine, Base
from app.models.user_db import UserDB  # Import models to register them

def main():
    """Initialize database tables"""
    print("Initializing PostgreSQL database...")
    print(f"Database URL: {engine.url}")
    
    try:
        # Create all tables
        init_db()
        print("✓ Database tables created successfully!")
        
        # Verify tables were created
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"✓ Created tables: {', '.join(tables)}")
        
    except Exception as e:
        print(f"✗ Error initializing database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()





