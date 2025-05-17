import sqlite3
import os
from app import create_app, db
from App.models import SavedPage

def migrate_database():
    # Create app context
    app = create_app()
    
    with app.app_context():
        # Check current schema
        try:
            # This will throw an error if the table doesn't exist
            SavedPage.query.first()
            print("Table exists, checking columns...")
        except Exception as e:
            print(f"Creating tables from scratch: {e}")
            db.create_all()
            print("Tables created")
            return
    
    # Now we'll manually add columns that might be missing
    # Connect to the SQLite database
    conn = sqlite3.connect('instance/saved_pages.db')
    cursor = conn.cursor()
    
    try:
        # Check if columns exist
        cursor.execute('PRAGMA table_info(saved_page)')
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        # Add the gumloop_data column if it doesn't exist
        if 'gumloop_data' not in column_names:
            try:
                cursor.execute('ALTER TABLE saved_page ADD COLUMN gumloop_data JSON')
                print("Successfully added gumloop_data column to saved_page table")
            except sqlite3.OperationalError as e:
                print(f"Error adding gumloop_data column: {e}")
        else:
            print("gumloop_data column already exists")

        # Add the saved_item_id column if it doesn't exist
        if 'saved_item_id' not in column_names:
            try:
                cursor.execute('ALTER TABLE saved_page ADD COLUMN saved_item_id VARCHAR(50)')
                print("Successfully added saved_item_id column to saved_page table")
                
                # Update existing rows to have a saved_item_id
                cursor.execute('UPDATE saved_page SET saved_item_id = "legacy-" || id WHERE saved_item_id IS NULL')
                print("Updated existing rows with legacy saved_item_id")
            except sqlite3.OperationalError as e:
                print(f"Error adding saved_item_id column: {e}")
        else:
            print("saved_item_id column already exists")

        # Add unique constraint to saved_item_id if not present
        try:
            cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_saved_item_id ON saved_page(saved_item_id)')
            print("Added unique constraint to saved_item_id")
        except sqlite3.OperationalError as e:
            print(f"Error adding unique constraint: {e}")

        conn.commit()
        print("Migration completed successfully")
    except Exception as e:
        conn.rollback()
        print(f"Error during migration: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    migrate_database() 