#!/usr/bin/env python3
"""
Database Migration Script - Upgrade to Complete Data Storage
Run this ONCE to upgrade your existing database structure
"""

import sqlite3
import os
import json
from datetime import datetime

def migrate_database(db_path="inspection_system.db"):
    """Migrate database to support complete inspection data storage"""
    
    if not os.path.exists(db_path):
        print("Database not found. No migration needed for new installation.")
        return True
    
    print(f"Migrating database: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Step 4A: Create new inspection_items table
        print("Creating inspection_items table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inspection_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inspection_id TEXT NOT NULL,
                unit_number TEXT,
                unit_type TEXT,
                room TEXT,
                component TEXT,
                trade TEXT,
                status_class TEXT CHECK (status_class IN ('OK', 'Not OK', 'Blank')),
                urgency TEXT CHECK (urgency IN ('Normal', 'High Priority', 'Urgent')),
                planned_completion DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (inspection_id) REFERENCES processed_inspections(id)
            )
        ''')
        
        # Step 4B: Create indexes for new table
        print("Creating indexes...")
        indexes = [
            'CREATE INDEX IF NOT EXISTS idx_items_inspection ON inspection_items(inspection_id)',
            'CREATE INDEX IF NOT EXISTS idx_items_unit ON inspection_items(unit_number)',
            'CREATE INDEX IF NOT EXISTS idx_items_status ON inspection_items(status_class)',
            'CREATE INDEX IF NOT EXISTS idx_items_urgency ON inspection_items(urgency)'
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
        
        # Step 4C: Check if there's existing data to migrate
        cursor.execute('SELECT COUNT(*) FROM inspection_defects')
        defect_count = cursor.fetchone()[0]
        
        if defect_count > 0:
            print(f"Found {defect_count} existing defects to migrate...")
            
            # Migrate existing defects to new table
            cursor.execute('''
                INSERT INTO inspection_items 
                (inspection_id, unit_number, unit_type, room, component, trade, 
                 status_class, urgency, planned_completion, created_at)
                SELECT 
                    inspection_id, 
                    unit_number, 
                    unit_type, 
                    room, 
                    component, 
                    trade,
                    'Not OK' as status_class,  -- All existing items are defects
                    urgency,
                    planned_completion,
                    created_at
                FROM inspection_defects
            ''')
            
            migrated_count = cursor.rowcount
            print(f"Migrated {migrated_count} defects to complete data structure")
        
        # Step 4D: Add migration marker
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS migration_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                migration_name TEXT NOT NULL,
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                success BOOLEAN DEFAULT 1
            )
        ''')
        
        cursor.execute('''
            INSERT INTO migration_log (migration_name, success)
            VALUES ('complete_data_storage_v1', 1)
        ''')
        
        conn.commit()
        print("✅ Database migration completed successfully!")
        
        # Step 4E: Show migration summary
        cursor.execute('SELECT COUNT(*) FROM inspection_items')
        total_items = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM inspection_items WHERE status_class = "Not OK"')
        defects = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM inspection_items WHERE status_class = "OK"')
        ok_items = cursor.fetchone()[0]
        
        print(f"\nMigration Summary:")
        print(f"- Total inspection items: {total_items}")
        print(f"- Defects (Not OK): {defects}")
        print(f"- OK items: {ok_items}")
        print(f"- Blank items: {total_items - defects - ok_items}")
        
        if ok_items == 0:
            print(f"\n⚠️  WARNING: No OK items found in migrated data.")
            print(f"   This is expected if you're migrating from the old system.")
            print(f"   Upload a new CSV file to get complete inspection data.")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

def check_migration_status(db_path="inspection_system.db"):
    """Check if migration has been completed"""
    
    if not os.path.exists(db_path):
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if inspection_items table exists
        cursor.execute('''
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='inspection_items'
        ''')
        
        table_exists = cursor.fetchone() is not None
        
        if table_exists:
            # Check migration log
            cursor.execute('''
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='migration_log'
            ''')
            
            if cursor.fetchone():
                cursor.execute('''
                    SELECT COUNT(*) FROM migration_log 
                    WHERE migration_name = 'complete_data_storage_v1' AND success = 1
                ''')
                migration_completed = cursor.fetchone()[0] > 0
            else:
                migration_completed = False
        else:
            migration_completed = False
        
        conn.close()
        return migration_completed
        
    except Exception as e:
        print(f"Error checking migration status: {e}")
        return False

if __name__ == "__main__":
    print("Database Migration Tool")
    print("======================")
    
    # Check current status
    if check_migration_status():
        print("✅ Database is already migrated to complete data storage")
        
        # Show current data
        try:
            conn = sqlite3.connect("inspection_system.db")
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM inspection_items')
            total_items = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM inspection_items WHERE status_class = "Not OK"')
            defects = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM inspection_items WHERE status_class = "OK"')
            ok_items = cursor.fetchone()[0]
            
            print(f"\nCurrent Data:")
            print(f"- Total inspection items: {total_items}")
            print(f"- Defects: {defects}")
            print(f"- OK items: {ok_items}")
            
            conn.close()
            
        except Exception as e:
            print(f"Error checking current data: {e}")
    
    else:
        print("🔄 Starting database migration...")
        success = migrate_database()
        
        if success:
            print("\n🎉 Migration completed! Your Excel reports will now be consistent.")
            print("\nNext steps:")
            print("1. Restart your Streamlit app")
            print("2. Upload a new CSV file to get complete inspection data") 
            print("3. Generate Excel reports - they will now be identical")
        else:
            print("\n❌ Migration failed. Please check the error messages above.")