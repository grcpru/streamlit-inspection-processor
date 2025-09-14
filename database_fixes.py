# database_fixes.py
# Run this script to fix the missing project manager and add data persistence

import sqlite3
import hashlib
import json
from datetime import datetime

def hash_password(password):
    """Hash password with salt"""
    salt = "inspection_app_salt_2024"
    return hashlib.sha256((password + salt).encode()).hexdigest()

def add_project_manager_account(db_path="inspection_system.db"):
    """Add missing project manager account"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Add project manager account
    project_manager_data = (
        "manager1",
        hash_password("mgr123"),
        "Project Manager",
        "manager@company.com",
        "project_manager",
        "system"
    )
    
    try:
        cursor.execute('''
            INSERT INTO users (username, password_hash, full_name, email, role, created_by)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', project_manager_data)
        
        conn.commit()
        print("✅ Project Manager account added: manager1 / mgr123")
    except sqlite3.IntegrityError:
        print("ℹ️ Project Manager account already exists")
    
    conn.close()

def create_data_persistence_tables(db_path="inspection_system.db"):
    """Create tables for storing processed inspection data"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Table for storing processed inspections
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS processed_inspections (
            id TEXT PRIMARY KEY,
            building_name TEXT,
            address TEXT,
            inspection_date DATE,
            uploaded_by TEXT,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            metrics_json TEXT,
            FOREIGN KEY (uploaded_by) REFERENCES users(username)
        )
    ''')
    
    # Table for storing individual defects
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inspection_defects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inspection_id TEXT,
            unit_number TEXT,
            unit_type TEXT,
            room TEXT,
            component TEXT,
            trade TEXT,
            urgency TEXT,
            planned_completion DATE,
            status TEXT DEFAULT 'open',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (inspection_id) REFERENCES processed_inspections(id)
        )
    ''')
    
    # Table for storing trade mappings
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
    
    # Create indexes for better performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_defects_inspection ON inspection_defects(inspection_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_defects_unit ON inspection_defects(unit_number)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_defects_status ON inspection_defects(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_inspections_active ON processed_inspections(is_active)')
    
    conn.commit()
    conn.close()
    
    print("✅ Data persistence tables created")

def migrate_existing_data():
    """Migrate any existing session data to database (optional)"""
    print("ℹ️ Data migration from session state should be done within the Streamlit app")

def show_all_users(db_path="inspection_system.db"):
    """Display all users in the database"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('SELECT username, full_name, role FROM users ORDER BY role, username')
    users = cursor.fetchall()
    
    print("\n📋 All Users in Database:")
    print("-" * 50)
    for username, full_name, role in users:
        print(f"{role.upper():20} | {username:15} | {full_name}")
    
    conn.close()

def main():
    """Run all fixes"""
    print("🔧 Applying Database Fixes...")
    print()
    
    # Fix 1: Add project manager account
    print("1. Adding Project Manager account...")
    add_project_manager_account()
    print()
    
    # Fix 2: Create data persistence tables
    print("2. Creating data persistence tables...")
    create_data_persistence_tables()
    print()
    
    # Show all users
    print("3. Showing all users...")
    show_all_users()
    print()
    
    print("✅ Database fixes complete!")
    print()
    print("🔑 Available Login Credentials:")
    print("Admin: admin / admin123")
    print("Developer: developer1 / dev123") 
    print("Manager: manager1 / mgr123")  # NEW
    print("Inspector: inspector / inspector123")
    print("Builder: builder1 / build123")

if __name__ == "__main__":
    main()