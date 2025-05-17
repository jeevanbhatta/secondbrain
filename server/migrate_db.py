from app import app, db
import sqlite3

def migrate_database():
    # Connect to the SQLite database
    conn = sqlite3.connect('instance/saved_pages.db')
    cursor = conn.cursor()
    
    try:
        # Add the new columns if they don't exist
        try:
            cursor.execute('ALTER TABLE saved_page ADD COLUMN gumloop_data JSON')
            print("Successfully added gumloop_data column to saved_page table")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("gumloop_data column already exists")
            else:
                raise e

        try:
            cursor.execute('ALTER TABLE saved_page ADD COLUMN saved_item_id VARCHAR(50)')
            print("Successfully added saved_item_id column to saved_page table")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("saved_item_id column already exists")
            else:
                raise e

        # Update existing rows to have a saved_item_id
        cursor.execute('UPDATE saved_page SET saved_item_id = "legacy-" || id WHERE saved_item_id IS NULL')
        print("Updated existing rows with legacy saved_item_id")

        # Add unique constraint to saved_item_id
        try:
            cursor.execute('CREATE UNIQUE INDEX idx_saved_item_id ON saved_page(saved_item_id)')
            print("Added unique constraint to saved_item_id")
        except sqlite3.OperationalError as e:
            if "already exists" in str(e):
                print("Unique constraint already exists")
            else:
                raise e

        conn.commit()
        print("Migration completed successfully")
    except Exception as e:
        conn.rollback()
        print(f"Error during migration: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    migrate_database() 