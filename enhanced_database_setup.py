"""
Enhanced Database Setup with User-Building Assignments and Audit Tables
Run this script to add the missing permission-related tables
"""
import sqlite3
import hashlib
from datetime import datetime


def hash_password(password: str) -> str:
    """Hash password with salt"""
    salt = "inspection_app_salt_2024"
    return hashlib.sha256((password + salt).encode()).hexdigest()


def setup_enhanced_database():
    """Set up enhanced database schema with permissions and assignments"""
    
    conn = sqlite3.connect("inspection_system.db")
    cursor = conn.cursor()
    
    print("Setting up enhanced database schema...")
    
    # 1. Create user-building assignments table
    print("Creating user_building_assignments table...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_building_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            building_name TEXT NOT NULL,
            assigned_by TEXT NOT NULL,
            assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (username) REFERENCES users(username),
            UNIQUE(username, building_name)
        )
    ''')
    
    # 2. Create audit log table
    print("Creating audit_log table...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            action TEXT NOT NULL,
            resource TEXT,
            success BOOLEAN NOT NULL,
            ip_address TEXT,
            user_agent TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            details TEXT
        )
    ''')
    
    # 3. Create user sessions table for better session management
    print("Creating user_sessions table...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            session_id TEXT NOT NULL UNIQUE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_activity DATETIME DEFAULT CURRENT_TIMESTAMP,
            expires_at DATETIME NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            ip_address TEXT,
            user_agent TEXT,
            FOREIGN KEY (username) REFERENCES users(username)
        )
    ''')
    
    # 4. Create permission overrides table (for future flexibility)
    print("Creating user_permission_overrides table...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_permission_overrides (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            permission TEXT NOT NULL,
            granted BOOLEAN NOT NULL,
            granted_by TEXT NOT NULL,
            granted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            expires_at DATETIME,
            reason TEXT,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (username) REFERENCES users(username),
            UNIQUE(username, permission)
        )
    ''')
    
    # 5. Add missing indexes for performance
    print("Creating performance indexes...")
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_audit_username ON audit_log(username)",
        "CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp)",
        "CREATE INDEX IF NOT EXISTS idx_assignments_username ON user_building_assignments(username)",
        "CREATE INDEX IF NOT EXISTS idx_assignments_building ON user_building_assignments(building_name)",
        "CREATE INDEX IF NOT EXISTS idx_sessions_username ON user_sessions(username)",
        "CREATE INDEX IF NOT EXISTS idx_sessions_active ON user_sessions(is_active)"
    ]
    
    for index_sql in indexes:
        cursor.execute(index_sql)
    
    # 6. Insert sample building assignments for demo users
    print("Creating sample building assignments...")
    sample_assignments = [
        ('manager1', 'Demo Building A', 'admin'),
        ('manager1', 'Demo Building B', 'admin'),
        ('developer1', 'Demo Building A', 'admin'),
        ('developer1', 'Demo Building B', 'admin'),
        ('developer1', 'Demo Building C', 'admin'),
        ('inspector', 'Demo Building A', 'admin'),
        ('builder1', 'Demo Building A', 'admin'),
        ('builder1', 'Demo Building B', 'admin'),
    ]
    
    for username, building_name, assigned_by in sample_assignments:
        cursor.execute('''
            INSERT OR IGNORE INTO user_building_assignments 
            (username, building_name, assigned_by)
            VALUES (?, ?, ?)
        ''', (username, building_name, assigned_by))
    
    # 7. Create sample buildings in processed_inspections if they don't exist
    print("Creating sample building data...")
    sample_buildings = [
        ('Demo Building A', 'Melbourne, VIC', 'admin', '2024-01-15'),
        ('Demo Building B', 'Sydney, NSW', 'manager1', '2024-02-10'),
        ('Demo Building C', 'Brisbane, QLD', 'inspector', '2024-03-05')
    ]
    
    for building_name, address, processed_by, inspection_date in sample_buildings:
        # Check if building exists
        cursor.execute('''
            SELECT id FROM processed_inspections 
            WHERE building_name = ? AND is_active = 1
        ''', (building_name,))
        
        if not cursor.fetchone():
            # Create sample inspection record
            sample_metrics = f'''{{
                "building_name": "{building_name}",
                "address": "{address}",
                "inspection_date": "{inspection_date}",
                "total_units": 50,
                "total_defects": 25,
                "ready_units": 35,
                "urgent_defects": 2
            }}'''
            
            cursor.execute('''
                INSERT INTO processed_inspections 
                (building_name, address, inspection_date, processed_by, metrics_json, is_active)
                VALUES (?, ?, ?, ?, ?, 1)
            ''', (building_name, address, inspection_date, processed_by, sample_metrics))
    
    # 8. Add initial audit log entry
    cursor.execute('''
        INSERT INTO audit_log (username, action, success, details)
        VALUES ('system', 'Database enhanced setup completed', 1, 'Added permission tables and sample data')
    ''')
    
    conn.commit()
    conn.close()
    
    print("\n✅ Enhanced database setup completed!")
    print("\nNew tables created:")
    print("- user_building_assignments (for role-based building access)")
    print("- audit_log (for security and compliance)")
    print("- user_sessions (for improved session management)")  
    print("- user_permission_overrides (for flexible permissions)")
    print("\nSample assignments created for demo users.")
    print("Run the application now to test the enhanced permissions!")


if __name__ == "__main__":
    setup_enhanced_database()