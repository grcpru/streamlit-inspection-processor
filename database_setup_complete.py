#!/usr/bin/env python3
"""
Complete Database Setup for Inspection System
Run this once to create the database with all required tables and default users
"""

import sqlite3
import hashlib
import json
import os
from datetime import datetime

def hash_password(password):
    """Hash password with salt"""
    salt = "inspection_app_salt_2024"
    return hashlib.sha256((password + salt).encode()).hexdigest()

def create_inspection_database(db_path="inspection_system.db"):
    """Create complete database schema"""
    
    # Remove existing database if it exists (for fresh start)
    if os.path.exists(db_path):
        backup_name = f"inspection_system_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        os.rename(db_path, backup_name)
        print(f"Existing database backed up as: {backup_name}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create complete schema
    cursor.executescript('''
        -- Users table
        CREATE TABLE users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            email TEXT,
            role TEXT NOT NULL CHECK (role IN ('admin', 'property_developer', 'project_manager', 'inspector', 'builder')),
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            created_by TEXT
        );
        
        -- Processed inspections table
        CREATE TABLE processed_inspections (
            id TEXT PRIMARY KEY,
            building_name TEXT NOT NULL,
            address TEXT,
            inspection_date DATE,
            uploaded_by TEXT,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            metrics_json TEXT,
            FOREIGN KEY (uploaded_by) REFERENCES users(username)
        );
        
        -- Individual defects table
        CREATE TABLE inspection_defects (
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (inspection_id) REFERENCES processed_inspections(id)
        );
        
        -- Trade mappings table
        CREATE TABLE trade_mappings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room TEXT,
            component TEXT,
            trade TEXT,
            created_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (created_by) REFERENCES users(username),
            UNIQUE(room, component)
        );
        
        -- Performance indexes
        CREATE INDEX idx_defects_inspection ON inspection_defects(inspection_id);
        CREATE INDEX idx_defects_unit ON inspection_defects(unit_number);
        CREATE INDEX idx_defects_status ON inspection_defects(status);
        CREATE INDEX idx_defects_urgency ON inspection_defects(urgency);
        CREATE INDEX idx_inspections_active ON processed_inspections(is_active);
        CREATE INDEX idx_inspections_building ON processed_inspections(building_name);
        CREATE INDEX idx_users_role ON users(role);
        CREATE INDEX idx_mappings_active ON trade_mappings(is_active);
    ''')
    
    conn.commit()
    print("Database schema created successfully")
    
    # Create default users
    default_users = [
        ("admin", "admin123", "System Administrator", "admin@company.com", "admin"),
        ("developer1", "dev123", "John Developer", "john@developercompany.com", "property_developer"),
        ("manager1", "mgr123", "Sarah Manager", "sarah@company.com", "project_manager"),
        ("inspector", "inspector123", "Site Inspector", "inspector@company.com", "inspector"),
        ("builder1", "build123", "Tom Builder", "tom@buildercompany.com", "builder")
    ]
    
    for username, password, name, email, role in default_users:
        password_hash = hash_password(password)
        cursor.execute('''
            INSERT INTO users (username, password_hash, full_name, email, role, created_by)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (username, password_hash, name, email, role, "system"))
    
    conn.commit()
    print(f"Created {len(default_users)} default users")
    
    # Create default trade mapping
    default_mappings = [
        ("Apartment Entry Door", "Door Handle", "Doors"),
        ("Apartment Entry Door", "Door Locks and Keys", "Doors"),
        ("Apartment Entry Door", "Paint", "Painting"),
        ("Balcony", "Balustrade", "Carpentry & Joinery"),
        ("Balcony", "Drainage Point", "Plumbing"),
        ("Bathroom", "Bathtub (if applicable)", "Plumbing"),
        ("Bathroom", "Ceiling", "Painting"),
        ("Bathroom", "Exhaust Fan", "Electrical"),
        ("Bathroom", "Tiles", "Flooring - Tiles"),
        ("Kitchen Area", "Cabinets", "Carpentry & Joinery"),
        ("Kitchen Area", "Kitchen Sink", "Plumbing"),
        ("Kitchen Area", "Stovetop and Oven", "Appliances"),
        ("Bedroom", "Carpets", "Flooring - Carpets"),
        ("Bedroom", "Windows", "Windows"),
        ("Bedroom", "Light Fixtures", "Electrical")
    ]
    
    for room, component, trade in default_mappings:
        cursor.execute('''
            INSERT INTO trade_mappings (room, component, trade, created_by)
            VALUES (?, ?, ?, ?)
        ''', (room, component, trade, "system"))
    
    conn.commit()
    print(f"Created {len(default_mappings)} default trade mappings")
    
    conn.close()
    print(f"Database setup complete: {os.path.abspath(db_path)}")

def verify_database(db_path="inspection_system.db"):
    """Verify database setup"""
    if not os.path.exists(db_path):
        print(f"ERROR: Database file not found: {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    expected_tables = ['users', 'processed_inspections', 'inspection_defects', 'trade_mappings']
    
    missing_tables = [t for t in expected_tables if t not in tables]
    if missing_tables:
        print(f"ERROR: Missing tables: {missing_tables}")
        return False
    
    # Check users
    cursor.execute("SELECT username, role FROM users ORDER BY role, username")
    users = cursor.fetchall()
    
    # Check mappings
    cursor.execute("SELECT COUNT(*) FROM trade_mappings WHERE is_active = 1")
    mapping_count = cursor.fetchone()[0]
    
    conn.close()
    
    print("\nDatabase Verification Complete:")
    print(f"Tables: {len(tables)} (all required tables present)")
    print(f"Users: {len(users)}")
    print(f"Trade Mappings: {mapping_count}")
    print("\nAvailable Users:")
    for username, role in users:
        print(f"  {role:20} | {username}")
    
    return True

def show_login_credentials():
    """Display login credentials"""
    print("\n" + "="*50)
    print("LOGIN CREDENTIALS")
    print("="*50)
    print("Admin:             admin / admin123")
    print("Property Developer: developer1 / dev123")
    print("Project Manager:   manager1 / mgr123")
    print("Inspector:         inspector / inspector123")
    print("Builder:           builder1 / build123")
    print("="*50)

def main():
    """Main setup function"""
    print("Setting up Complete Inspection System Database...")
    print()
    
    # Create database
    create_inspection_database()
    print()
    
    # Verify setup
    if verify_database():
        print("\nSUCCESS: Database setup completed successfully!")
        show_login_credentials()
    else:
        print("\nERROR: Database setup failed!")

if __name__ == "__main__":
    main()