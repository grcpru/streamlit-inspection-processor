# Step 1: Update complete_database_setup.py to store ALL inspection results

#!/usr/bin/env python3
"""
Updated Database Setup - Now stores ALL inspection results (OK and Not OK)
"""

import sqlite3
import hashlib
from datetime import datetime

def create_complete_database_v2(db_path="inspection_system.db"):
    """Create updated database schema that stores all inspection results"""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON")
    
    print("Creating updated database schema for complete inspection storage...")
    
    # Existing tables (keep as-is)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('admin', 'property_developer', 'project_manager', 'inspector', 'builder')),
            is_active BOOLEAN DEFAULT 1,
            created_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS portfolios (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            owner_username TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (owner_username) REFERENCES users(username)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            portfolio_id TEXT,
            name TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'active' CHECK (status IN ('active', 'completed', 'cancelled')),
            manager_username TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (portfolio_id) REFERENCES portfolios(id),
            FOREIGN KEY (manager_username) REFERENCES users(username)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS buildings (
            id TEXT PRIMARY KEY,
            project_id TEXT,
            name TEXT NOT NULL,
            address TEXT,
            total_units INTEGER DEFAULT 0,
            building_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_permissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            resource_type TEXT CHECK (resource_type IN ('project', 'building', 'portfolio')),
            resource_id TEXT,
            permission_level TEXT CHECK (permission_level IN ('read', 'write', 'admin')),
            granted_by TEXT,
            granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (username) REFERENCES users(username),
            FOREIGN KEY (granted_by) REFERENCES users(username),
            UNIQUE(username, resource_type, resource_id)
        )
    ''')
    
    # Updated processed inspections table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS processed_inspections (
            id TEXT PRIMARY KEY,
            building_name TEXT NOT NULL,
            address TEXT,
            inspection_date DATE,
            uploaded_by TEXT,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            metrics_json TEXT,
            building_id TEXT,
            total_components_inspected INTEGER DEFAULT 0,
            FOREIGN KEY (uploaded_by) REFERENCES users(username),
            FOREIGN KEY (building_id) REFERENCES buildings(id)
        )
    ''')
    
    # UPDATED: New complete inspection results table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inspection_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inspection_id TEXT,
            unit_number TEXT,
            unit_type TEXT,
            room TEXT,
            component TEXT,
            trade TEXT,
            status_class TEXT CHECK (status_class IN ('OK', 'Not OK', 'Blank', 'N/A')),
            urgency TEXT CHECK (urgency IN ('Normal', 'High Priority', 'Urgent')),
            planned_completion DATE,
            defect_status TEXT DEFAULT 'open' CHECK (defect_status IN ('open', 'assigned', 'in_progress', 'completed', 'approved', 'rejected')),
            assigned_to TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (inspection_id) REFERENCES processed_inspections(id),
            FOREIGN KEY (assigned_to) REFERENCES users(username)
        )
    ''')
    
    # Keep existing defects table for backward compatibility (will be deprecated)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inspection_defects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inspection_id TEXT,
            unit_number TEXT,
            unit_type TEXT,
            room TEXT,
            component TEXT,
            trade TEXT,
            urgency TEXT CHECK (urgency IN ('Normal', 'High Priority', 'Urgent')),
            planned_completion DATE,
            status TEXT DEFAULT 'open' CHECK (status IN ('open', 'assigned', 'in_progress', 'completed', 'approved', 'rejected')),
            assigned_to TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (inspection_id) REFERENCES processed_inspections(id),
            FOREIGN KEY (assigned_to) REFERENCES users(username)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trade_mappings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room TEXT,
            component TEXT,
            trade TEXT,
            created_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (created_by) REFERENCES users(username),
            UNIQUE(room, component)
        )
    ''')
    
    # Create indexes for performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_results_inspection ON inspection_results(inspection_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_results_unit ON inspection_results(unit_number)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_results_status ON inspection_results(status_class)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_results_defect_status ON inspection_results(defect_status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_results_urgency ON inspection_results(urgency)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_inspections_building ON processed_inspections(building_id)')
    
    print("Database schema updated successfully!")
    
    # Insert default data (same as before)
    print("Creating default data...")
    
    def hash_password(password):
        salt = "inspection_app_salt_2024"
        return hashlib.sha256((password + salt).encode()).hexdigest()
    
    cursor.execute('''
        INSERT OR IGNORE INTO portfolios (id, name, description, owner_username)
        VALUES ('portfolio_001', 'Default Portfolio', 'Default development portfolio', 'admin')
    ''')
    
    cursor.execute('''
        INSERT OR IGNORE INTO projects (id, portfolio_id, name, description, manager_username)
        VALUES ('project_default', 'portfolio_001', 'Default Project', 'Default inspection project', 'admin')
    ''')
    
    cursor.execute('''
        INSERT OR IGNORE INTO buildings (id, project_id, name, address, total_units, building_type)
        VALUES ('building_default', 'project_default', 'Argyle Square', 'Melbourne, VIC', 100, 'Apartment')
    ''')
    
    # Ensure users exist
    cursor.execute('SELECT username FROM users WHERE username = ?', ('admin',))
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO users (username, password_hash, full_name, email, role, created_by)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('admin', hash_password('admin123'), 'System Administrator', 'admin@company.com', 'admin', 'system'))
    
    test_users = [
        ('developer1', 'dev123', 'Property Developer One', 'developer1@company.com', 'property_developer'),
        ('manager1', 'mgr123', 'Project Manager One', 'manager1@company.com', 'project_manager'),
        ('inspector', 'inspector123', 'Site Inspector', 'inspector@company.com', 'inspector'),
        ('builder1', 'build123', 'Builder One', 'builder1@company.com', 'builder')
    ]
    
    for username, password, full_name, email, role in test_users:
        cursor.execute('SELECT username FROM users WHERE username = ?', (username,))
        if not cursor.fetchone():
            cursor.execute('''
                INSERT INTO users (username, password_hash, full_name, email, role, created_by)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (username, hash_password(password), full_name, email, role, 'admin'))
    
    default_permissions = [
        ('developer1', 'portfolio', 'portfolio_001', 'read'),
        ('manager1', 'project', 'project_default', 'write'),
        ('inspector', 'building', 'building_default', 'write'),
        ('builder1', 'building', 'building_default', 'read')
    ]
    
    for username, resource_type, resource_id, permission_level in default_permissions:
        cursor.execute('''
            INSERT OR IGNORE INTO user_permissions (username, resource_type, resource_id, permission_level, granted_by)
            VALUES (?, ?, ?, ?, ?)
        ''', (username, resource_type, resource_id, permission_level, 'admin'))
    
    conn.commit()
    conn.close()
    
    print("Updated database setup completed successfully!")
    print("New feature: Complete inspection results storage (OK and Not OK)")

if __name__ == "__main__":
    create_complete_database_v2()
    print("\nDatabase updated to store complete inspection results!")