"""
Test PostgreSQL connection
"""
import sys
import os

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.db.postgres_client import engine, SessionLocal
from app.models.user_db import UserDB
from sqlalchemy import inspect

def test_connection():
    """Test PostgreSQL connection"""
    print("Testing PostgreSQL connection...")
    print(f"Database URL: {engine.url}")
    
    try:
        # Test connection
        with engine.connect() as conn:
            print("✓ Successfully connected to PostgreSQL!")
        
        # Check if tables exist
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"✓ Found tables: {', '.join(tables) if tables else 'No tables found'}")
        
        # Test session
        db = SessionLocal()
        try:
            # Try to query users table
            user_count = db.query(UserDB).count()
            print(f"✓ Database session works! Users in database: {user_count}")
        except Exception as e:
            print(f"⚠ Could not query users table: {e}")
            print("  (This is OK if tables haven't been created yet)")
        finally:
            db.close()
        
        print("\n✓ All connection tests passed!")
        return True
        
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)





