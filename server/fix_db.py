#!/usr/bin/env python3
import sqlite3
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_database():
    # Check if the database file exists
    db_path = 'instance/saved_pages.db'
    if not os.path.exists(db_path):
        logger.error(f"Database file not found at {db_path}")
        return False
    
    # Connect to the SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='saved_page'")
        if not cursor.fetchone():
            logger.error("Table 'saved_page' does not exist")
            return False
            
        # Check existing columns
        cursor.execute('PRAGMA table_info(saved_page)')
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        logger.info(f"Existing columns: {column_names}")
        
        # Add the gumloop_data column if it doesn't exist
        if 'gumloop_data' not in column_names:
            try:
                cursor.execute('ALTER TABLE saved_page ADD COLUMN gumloop_data JSON')
                logger.info("Successfully added gumloop_data column to saved_page table")
            except sqlite3.OperationalError as e:
                logger.error(f"Error adding gumloop_data column: {e}")
        else:
            logger.info("gumloop_data column already exists")

        # Add the saved_item_id column if it doesn't exist
        if 'saved_item_id' not in column_names:
            try:
                cursor.execute('ALTER TABLE saved_page ADD COLUMN saved_item_id VARCHAR(50)')
                logger.info("Successfully added saved_item_id column to saved_page table")
                
                # Check if any rows exist
                cursor.execute('SELECT COUNT(*) FROM saved_page')
                row_count = cursor.fetchone()[0]
                
                if row_count > 0:
                    # Update existing rows to have a saved_item_id
                    cursor.execute('UPDATE saved_page SET saved_item_id = "legacy-" || id WHERE saved_item_id IS NULL')
                    logger.info(f"Updated {row_count} rows with legacy saved_item_id")
            except sqlite3.OperationalError as e:
                logger.error(f"Error adding saved_item_id column: {e}")
        else:
            logger.info("saved_item_id column already exists")

        # Try making saved_item_id non-nullable
        if 'saved_item_id' in column_names:
            try:
                # First, make sure all rows have a value
                cursor.execute('UPDATE saved_page SET saved_item_id = "legacy-" || id WHERE saved_item_id IS NULL')
                
                # Then add unique constraint (this is often the best we can do with SQLite)
                cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_saved_item_id ON saved_page(saved_item_id)')
                logger.info("Added unique constraint to saved_item_id")
            except sqlite3.OperationalError as e:
                logger.error(f"Error adding constraints to saved_item_id: {e}")

        conn.commit()
        logger.info("Database migration completed successfully")
        return True
    except Exception as e:
        conn.rollback()
        logger.error(f"Error during migration: {e}")
        return False
    finally:
        conn.close()

if __name__ == '__main__':
    success = fix_database()
    if success:
        print("Database fixed successfully. Try running your app now.")
    else:
        print("Failed to fix database. Check the logs for details.") 