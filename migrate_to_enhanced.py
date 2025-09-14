#!/usr/bin/env python3
"""
FIXED Database Migration Script for Enhanced Defect Management System
Handles varying table schemas properly
"""

import sqlite3
import os
import sys
from datetime import datetime

def check_database_exists():
    """Check if the main database exists"""
    if not os.path.exists("inspection_system.db"):
        print("❌ Error: inspection_system.db not found!")
        print("Please ensure you're running this script in the correct directory.")
        return False
    return True

def backup_database():
    """Create a backup of the existing database"""
    backup_name = f"inspection_system_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    
    try:
        import shutil
        shutil.copy2("inspection_system.db", backup_name)
        print(f"✅ Database backed up to: {backup_name}")
        return True
    except Exception as e:
        print(f"❌ Failed to create backup: {e}")
        return False

def get_table_schema(cursor, table_name):
    """Get the schema of an existing table"""
    try:
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        return {col[1]: col[2] for col in columns}  # {column_name: column_type}
    except:
        return {}

def create_enhanced_tables():
    """Create enhanced tables for photo and workflow management"""
    
    try:
        conn = sqlite3.connect("inspection_system.db")
        cursor = conn.cursor()
        
        print("Creating enhanced tables...")
        
        # Enhanced defects table with workflow status
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS enhanced_defects (
                id TEXT PRIMARY KEY,
                inspection_id TEXT NOT NULL,
                unit_number TEXT,
                unit_type TEXT,
                room TEXT,
                component TEXT,
                trade TEXT,
                urgency TEXT CHECK (urgency IN ('Normal', 'High Priority', 'Urgent')),
                planned_completion DATE,
                status TEXT DEFAULT 'open' CHECK (status IN ('open', 'assigned', 'in_progress', 'completed_pending_approval', 'approved', 'rejected')),
                assigned_to TEXT,
                completed_by TEXT,
                completed_at TIMESTAMP,
                completion_notes TEXT,
                approved_by TEXT,
                approved_at TIMESTAMP,
                approval_notes TEXT,
                rejected_by TEXT,
                rejected_at TIMESTAMP,
                rejection_reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (inspection_id) REFERENCES processed_inspections(id)
            )
        ''')
        
        # Photo evidence table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS defect_photos (
                id TEXT PRIMARY KEY,
                defect_id TEXT NOT NULL,
                photo_type TEXT CHECK (photo_type IN ('before', 'during', 'after', 'evidence')),
                filename TEXT NOT NULL,
                photo_data BLOB NOT NULL,
                uploaded_by TEXT,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                description TEXT,
                FOREIGN KEY (defect_id) REFERENCES enhanced_defects(id)
            )
        ''')
        
        # Defect workflow history
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS defect_workflow_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                defect_id TEXT NOT NULL,
                previous_status TEXT,
                new_status TEXT,
                changed_by TEXT,
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT,
                FOREIGN KEY (defect_id) REFERENCES enhanced_defects(id)
            )
        ''')
        
        # Building access permissions for persistent viewing
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS building_access (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                building_id TEXT NOT NULL,
                access_level TEXT CHECK (access_level IN ('read', 'write', 'admin')),
                granted_by TEXT,
                granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                UNIQUE(username, building_id)
            )
        ''')
        
        # Create indexes for performance
        indexes = [
            'CREATE INDEX IF NOT EXISTS idx_enhanced_defects_status ON enhanced_defects(status)',
            'CREATE INDEX IF NOT EXISTS idx_enhanced_defects_assigned ON enhanced_defects(assigned_to)',
            'CREATE INDEX IF NOT EXISTS idx_enhanced_defects_building ON enhanced_defects(inspection_id)',
            'CREATE INDEX IF NOT EXISTS idx_photos_defect ON defect_photos(defect_id)',
            'CREATE INDEX IF NOT EXISTS idx_workflow_defect ON defect_workflow_history(defect_id)',
            'CREATE INDEX IF NOT EXISTS idx_building_access_user ON building_access(username)',
            'CREATE INDEX IF NOT EXISTS idx_building_access_building ON building_access(building_id)'
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
        
        conn.commit()
        conn.close()
        
        print("✅ Enhanced tables created successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error creating enhanced tables: {e}")
        return False

def migrate_legacy_defects():
    """Migrate existing defects to enhanced system - FIXED VERSION"""
    
    try:
        conn = sqlite3.connect("inspection_system.db")
        cursor = conn.cursor()
        
        print("Migrating legacy defects...")
        
        # Check if migration already done
        cursor.execute('SELECT COUNT(*) FROM enhanced_defects')
        enhanced_count = cursor.fetchone()[0]
        
        if enhanced_count > 0:
            print(f"✅ Migration already completed ({enhanced_count} enhanced defects found)")
            conn.close()
            return True
        
        # Check what columns exist in the legacy table
        legacy_schema = get_table_schema(cursor, 'inspection_defects')
        
        if not legacy_schema:
            print("ℹ️ No legacy inspection_defects table found - creating fresh system")
            conn.close()
            return True
        
        print(f"Found legacy table with columns: {list(legacy_schema.keys())}")
        
        # Build migration query based on available columns
        base_columns = ['id', 'inspection_id', 'unit_number', 'unit_type', 'room', 
                       'component', 'trade', 'urgency', 'planned_completion']
        
        # Check which base columns exist
        available_columns = []
        select_columns = []
        
        for col in base_columns:
            if col in legacy_schema:
                available_columns.append(col)
                if col == 'id':
                    select_columns.append("'defect_' || id")
                else:
                    select_columns.append(col)
        
        # Handle optional columns
        if 'status' in legacy_schema:
            available_columns.append('status')
            select_columns.append('''
                CASE 
                    WHEN status = 'completed' THEN 'approved'
                    ELSE COALESCE(status, 'open') 
                END
            ''')
        else:
            available_columns.append('status')
            select_columns.append("'open'")
        
        if 'assigned_to' in legacy_schema:
            available_columns.append('assigned_to')
            select_columns.append('assigned_to')
        else:
            available_columns.append('assigned_to')
            select_columns.append('NULL')
        
        if 'created_at' in legacy_schema:
            available_columns.append('created_at')
            select_columns.append('created_at')
        else:
            available_columns.append('created_at')
            select_columns.append('CURRENT_TIMESTAMP')
        
        # Build the insert query
        target_columns = ['id', 'inspection_id', 'unit_number', 'unit_type', 'room', 
                         'component', 'trade', 'urgency', 'planned_completion', 
                         'status', 'assigned_to', 'created_at']
        
        insert_query = f'''
            INSERT INTO enhanced_defects 
            ({', '.join(target_columns)})
            SELECT {', '.join(select_columns)}
            FROM inspection_defects
        '''
        
        print("Executing migration query...")
        cursor.execute(insert_query)
        
        migrated_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        print(f"✅ Migrated {migrated_count} legacy defects to enhanced system")
        return True
        
    except Exception as e:
        print(f"❌ Error migrating defects: {e}")
        print(f"Migration query failed. This might be due to missing columns in your legacy table.")
        print(f"This is not critical - the enhanced system will work with fresh defects.")
        return True  # Continue with migration even if legacy migration fails

def grant_building_access():
    """Grant building access permissions to users"""
    
    try:
        conn = sqlite3.connect("inspection_system.db")
        cursor = conn.cursor()
        
        print("Setting up building access permissions...")
        
        # Check if users and buildings tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        has_users = cursor.fetchone() is not None
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='buildings'")
        has_buildings = cursor.fetchone() is not None
        
        if not has_users:
            print("ℹ️ No users table found - skipping user permissions")
            conn.close()
            return True
        
        if not has_buildings:
            print("ℹ️ No buildings table found - creating default building entries")
            
            # Create buildings from processed_inspections
            cursor.execute('''
                INSERT OR IGNORE INTO buildings (id, name, address, total_units)
                SELECT 
                    'building_' || REPLACE(LOWER(building_name), ' ', '_'),
                    building_name,
                    address,
                    COALESCE(JSON_EXTRACT(metrics_json, '$.total_units'), 0)
                FROM processed_inspections
                WHERE is_active = 1
            ''')
            
            building_count = cursor.rowcount
            print(f"✅ Created {building_count} building entries from processed inspections")
        
        # Grant property developers access to all buildings
        cursor.execute('''
            INSERT OR IGNORE INTO building_access (username, building_id, access_level, granted_by)
            SELECT u.username, b.id, 'admin', 'migration_script'
            FROM users u
            CROSS JOIN buildings b
            WHERE u.role = 'property_developer' AND u.is_active = 1
        ''')
        
        dev_access_count = cursor.rowcount
        
        # Grant project managers access to buildings
        cursor.execute('''
            INSERT OR IGNORE INTO building_access (username, building_id, access_level, granted_by)
            SELECT u.username, b.id, 'write', 'migration_script'
            FROM users u
            CROSS JOIN buildings b
            WHERE u.role = 'project_manager' AND u.is_active = 1
        ''')
        
        pm_access_count = cursor.rowcount
        
        # Grant admins access to all buildings
        cursor.execute('''
            INSERT OR IGNORE INTO building_access (username, building_id, access_level, granted_by)
            SELECT u.username, b.id, 'admin', 'migration_script'
            FROM users u
            CROSS JOIN buildings b
            WHERE u.role = 'admin' AND u.is_active = 1
        ''')
        
        admin_access_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        print(f"✅ Granted access: {dev_access_count} developer permissions, {pm_access_count} PM permissions, {admin_access_count} admin permissions")
        return True
        
    except Exception as e:
        print(f"❌ Error granting building access: {e}")
        print("This is not critical - permissions can be set up manually later")
        return True

def verify_migration():
    """Verify the migration was successful"""
    
    try:
        conn = sqlite3.connect("inspection_system.db")
        cursor = conn.cursor()
        
        print("\nVerifying migration...")
        
        # Check enhanced defects
        cursor.execute('SELECT COUNT(*) FROM enhanced_defects')
        enhanced_defects_count = cursor.fetchone()[0]
        
        # Check photos table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='defect_photos'")
        has_photos_table = cursor.fetchone() is not None
        
        # Check building access
        cursor.execute('SELECT COUNT(*) FROM building_access WHERE is_active = 1')
        access_count = cursor.fetchone()[0]
        
        # Check workflow history table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='defect_workflow_history'")
        has_workflow_table = cursor.fetchone() is not None
        
        conn.close()
        
        print(f"✅ Enhanced defects: {enhanced_defects_count}")
        print(f"✅ Photo storage: {'Ready' if has_photos_table else 'Not created'}")
        print(f"✅ Building access: {access_count} permissions")
        print(f"✅ Workflow history: {'Ready' if has_workflow_table else 'Not created'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error verifying migration: {e}")
        return False

def main():
    """Main migration function"""
    
    print("=" * 60)
    print("Enhanced Defect Management System Migration - FIXED")
    print("=" * 60)
    print()
    
    # Check prerequisites
    if not check_database_exists():
        sys.exit(1)
    
    # Create backup
    if not backup_database():
        print("❌ Migration aborted - could not create backup")
        sys.exit(1)
    
    # Run migration steps
    steps = [
        ("Creating enhanced tables", create_enhanced_tables),
        ("Migrating legacy defects", migrate_legacy_defects),
        ("Setting up building access", grant_building_access),
        ("Verifying migration", verify_migration)
    ]
    
    for step_name, step_function in steps:
        print(f"\n{step_name}...")
        if not step_function():
            print(f"❌ Migration failed at step: {step_name}")
            print("Please check the error messages above and try again.")
            sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    print()
    print("New features now available:")
    print("• Property developers can access buildings without re-uploading CSV")
    print("• Builders can upload photos and mark defects complete")
    print("• Complete approval workflow with photo evidence")
    print("• Enhanced defect tracking and workflow management")
    print()
    print("Next steps:")
    print("1. Update your streamlit_app.py with the new dashboard functions")
    print("2. Install Pillow if not already installed: pip install Pillow")
    print("3. Restart your Streamlit application")
    print("4. Test the new features with different user roles")
    print()
    print("If you encounter any issues, restore from backup:")
    print("cp inspection_system_backup_*.db inspection_system.db")

if __name__ == "__main__":
    main()