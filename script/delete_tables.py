#!/usr/bin/env python3
import os
import sys
import argparse
from sqlalchemy import inspect, text
from dotenv import load_dotenv
import traceback

# Add parent directory to path so we can import from there
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Parse command line arguments
parser = argparse.ArgumentParser(description='Delete all tables from the database')
parser.add_argument('--force', action='store_true', help='Force deletion without confirmation')
args = parser.parse_args()

# Load environment variables
load_dotenv()

print("Importing Flask application and database...")
try:
    # Import Flask application and database
    from app import create_app
    from models.models import db
    print("Imports successful.")
except Exception as e:
    print(f"Error importing required modules: {e}")
    traceback.print_exc()
    sys.exit(1)

def delete_all_tables():
    """Delete all tables from the database"""
    print("Preparing to delete all tables from the database...")
    
    try:
        # Get all table names
        inspector = inspect(db.engine)
        table_names = inspector.get_table_names()
        
        if not table_names:
            print("No tables found in the database.")
            return
        
        print(f"Found {len(table_names)} tables: {', '.join(table_names)}")
        
        # Skip confirmation if --force flag is used
        if not args.force:
            confirm = input("Are you sure you want to DELETE ALL TABLES? This cannot be undone! (yes/no): ")
            if confirm.lower() != 'yes':
                print("Operation aborted.")
                return
        else:
            print("Force flag detected. Proceeding with deletion without confirmation.")
        
        print(f"Database type: {db.engine.name}")
        
        # Disable foreign key constraints temporarily
        if db.engine.name == 'mysql':
            db.session.execute(text("SET FOREIGN_KEY_CHECKS=0;"))
            print("Disabled MySQL foreign key constraints")
        elif db.engine.name == 'postgresql':
            db.session.execute(text("SET CONSTRAINTS ALL DEFERRED;"))
            print("Deferred PostgreSQL constraints")
        else:  # SQLite
            db.session.execute(text("PRAGMA foreign_keys = OFF;"))
            print("Disabled SQLite foreign key constraints")
        
        # Drop all tables
        for table in table_names:
            db.session.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE;"))
            print(f"Dropped table: {table}")
        
        # Re-enable foreign key constraints
        if db.engine.name == 'mysql':
            db.session.execute(text("SET FOREIGN_KEY_CHECKS=1;"))
            print("Re-enabled MySQL foreign key constraints")
        elif db.engine.name == 'postgresql':
            db.session.execute(text("SET CONSTRAINTS ALL IMMEDIATE;"))
            print("Restored PostgreSQL constraints")
        else:  # SQLite
            db.session.execute(text("PRAGMA foreign_keys = ON;"))
            print("Re-enabled SQLite foreign key constraints")
        
        db.session.commit()
        print("\nAll tables have been successfully deleted.")
        
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting tables: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    print("Creating Flask app context...")
    try:
        # Create Flask app context
        app = create_app()
        print("Flask app created successfully.")
        
        with app.app_context():
            print("Entered Flask app context.")
            delete_all_tables()
    except Exception as e:
        print(f"Error creating Flask app context: {e}")
        traceback.print_exc()
        sys.exit(1) 