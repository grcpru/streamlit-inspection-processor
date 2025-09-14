#!/usr/bin/env python3
"""
Database Migration Script v2 - Fix Schema Inconsistencies
Run this to update existing databases with proper relationships
"""

import sqlite3
import os
from datetime import datetime

def backup_database(db_path="inspection_system.db"):
    """Create backup before migration"""
    if os.path.exists(db_path):
        backup_name = f"inspection_system_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        import shutil
        shutil.copy2(db_path, backup_name)
        print(f"✅ Database backed up to: {backup_name}")
        return backup_name
    return None

def migrate_database(db_path="inspection_system.db"):
    """Apply migration fixes"""
    
    backup_file = backup_database(db_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("🔄 Starting database migration...")
    
    try:
        # 1. Add building_id column if it doesn't exist
        cursor.execute("PRAGMA table_info(processed_inspections)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'building_id' not in columns:
            print("📝 Adding building_id column...")
            cursor.execute('ALTER TABLE processed_inspections ADD COLUMN building_id TEXT')
        
        # 2. Create default building if none exists
        cursor.execute('SELECT COUNT(*) FROM buildings')
        if cursor.fetchone()[0] == 0:
            print("🏢 Creating default building...")
            cursor.execute('''
                INSERT INTO buildings (id, project_id, name, address, total_units, building_type)
                VALUES ('building_default', 'project_default', 'Default Building', 'Default Address', 0, 'Apartment')
            ''')
        
        # 3. Update existing inspections to link to default building
        cursor.execute('SELECT COUNT(*) FROM processed_inspections WHERE building_id IS NULL')
        null_building_count = cursor.fetchone()[0]
        
        if null_building_count > 0:
            print(f"🔗 Linking {null_building_count} inspections to default building...")
            cursor.execute('''
                UPDATE processed_inspections 
                SET building_id = 'building_default' 
                WHERE building_id IS NULL
            ''')
        
        # 4. Add missing indexes
        indexes_to_create = [
            'CREATE INDEX IF NOT EXISTS idx_inspections_building_id ON processed_inspections(building_id)',
            'CREATE INDEX IF NOT EXISTS idx_defects_urgency ON inspection_defects(urgency)',
            'CREATE INDEX IF NOT EXISTS idx_permissions_user_resource ON user_permissions(username, resource_type)'
        ]
        
        for index_sql in indexes_to_create:
            cursor.execute(index_sql)
        
        # 5. Verify foreign key constraints work
        cursor.execute('PRAGMA foreign_key_check')
        fk_violations = cursor.fetchall()
        
        if fk_violations:
            print(f"⚠️  Found {len(fk_violations)} foreign key violations:")
            for violation in fk_violations:
                print(f"   {violation}")
        else:
            print("✅ All foreign key constraints valid")
        
        conn.commit()
        print("✅ Migration completed successfully!")
        
        # Verify migration
        verify_migration(cursor)
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {str(e)}")
        if backup_file:
            print(f"💾 Restore from backup: {backup_file}")
        raise
    
    finally:
        conn.close()

def verify_migration(cursor):
    """Verify migration was successful"""
    print("\n🔍 Verifying migration...")
    
    # Check tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [t[0] for t in cursor.fetchall()]
    
    expected_tables = ['buildings', 'processed_inspections', 'inspection_defects', 
                      'users', 'projects', 'portfolios', 'user_permissions', 'trade_mappings']
    
    missing_tables = [t for t in expected_tables if t not in tables]
    if missing_tables:
        print(f"❌ Missing tables: {missing_tables}")
    else:
        print("✅ All required tables present")
    
    # Check critical relationships
    cursor.execute('''
        SELECT COUNT(*) FROM processed_inspections pi
        LEFT JOIN buildings b ON pi.building_id = b.id
        WHERE b.id IS NULL
    ''')
    orphaned_inspections = cursor.fetchone()[0]
    
    if orphaned_inspections > 0:
        print(f"⚠️  {orphaned_inspections} inspections not linked to buildings")
    else:
        print("✅ All inspections properly linked to buildings")
    
    # Check data integrity
    cursor.execute('SELECT COUNT(*) FROM users WHERE is_active = 1')
    active_users = cursor.fetchone()[0]
    print(f"📊 Active users: {active_users}")
    
    cursor.execute('SELECT COUNT(*) FROM processed_inspections WHERE is_active = 1')
    active_inspections = cursor.fetchone()[0]
    print(f"📊 Active inspections: {active_inspections}")

if __name__ == "__main__":
    print("🚀 Database Migration Tool v2")
    print("="*50)
    
    db_path = input("Database path (press Enter for default 'inspection_system.db'): ").strip()
    if not db_path:
        db_path = "inspection_system.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        exit(1)
    
    confirm = input(f"Migrate database '{db_path}'? (y/N): ").lower()
    if confirm != 'y':
        print("Migration cancelled")
        exit(0)
    
    try:
        migrate_database(db_path)
        print("\n✅ Migration completed! You can now run your application.")
    except Exception as e:
        print(f"\n❌ Migration failed: {str(e)}")
        exit(1)