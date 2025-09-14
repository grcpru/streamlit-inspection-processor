# database_setup.py
# Complete guide to set up SQLite database for your inspection system

import sqlite3
import os
import hashlib
from datetime import datetime
import json

def create_database(db_path="inspection_system.db"):
    """
    Step-by-step database creation
    This will create the SQLite database file in your project directory
    """
    
    print(f"Creating database at: {os.path.abspath(db_path)}")
    
    # Step 1: Connect to SQLite (creates file if doesn't exist)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("✅ Database connection established")
    
    # Step 2: Create Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            email TEXT,
            role TEXT NOT NULL CHECK (role IN ('admin', 'property_developer', 'project_manager', 'inspector', 'builder')),
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            created_by TEXT
        )
    ''')
    print("✅ Users table created")
    
    # Step 3: Create Portfolios table
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
    print("✅ Portfolios table created")
    
    # Step 4: Create Projects table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            portfolio_id TEXT,
            name TEXT NOT NULL,
            description TEXT,
            manager_username TEXT,
            status TEXT DEFAULT 'active' CHECK (status IN ('active', 'completed', 'on_hold', 'cancelled')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (portfolio_id) REFERENCES portfolios(id),
            FOREIGN KEY (manager_username) REFERENCES users(username)
        )
    ''')
    print("✅ Projects table created")
    
    # Step 5: Create Buildings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS buildings (
            id TEXT PRIMARY KEY,
            project_id TEXT,
            name TEXT NOT NULL,
            address TEXT,
            total_units INTEGER,
            building_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    ''')
    print("✅ Buildings table created")
    
    # Step 6: Create User Permissions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_permissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            resource_type TEXT CHECK (resource_type IN ('portfolio', 'project', 'building')),
            resource_id TEXT,
            permission_level TEXT CHECK (permission_level IN ('read', 'write', 'admin')),
            granted_by TEXT,
            granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (username) REFERENCES users(username),
            FOREIGN KEY (granted_by) REFERENCES users(username),
            UNIQUE(username, resource_type, resource_id)
        )
    ''')
    print("✅ User permissions table created")
    
    # Step 7: Create Inspections table (for storing processed data)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inspections (
            id TEXT PRIMARY KEY,
            building_id TEXT,
            inspection_date DATE,
            uploaded_by TEXT,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'active' CHECK (status IN ('uploaded', 'processed', 'active', 'archived')),
            is_latest BOOLEAN DEFAULT 1,
            total_defects INTEGER DEFAULT 0,
            defect_rate REAL DEFAULT 0.0,
            metrics_json TEXT, -- Store metrics as JSON
            raw_data_path TEXT, -- Path to original CSV file
            FOREIGN KEY (building_id) REFERENCES buildings(id),
            FOREIGN KEY (uploaded_by) REFERENCES users(username)
        )
    ''')
    print("✅ Inspections table created")
    
    # Step 8: Create Defects table (for defect lifecycle management)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS defects (
            id TEXT PRIMARY KEY,
            inspection_id TEXT,
            unit_number TEXT,
            room TEXT,
            component TEXT,
            trade TEXT,
            urgency TEXT CHECK (urgency IN ('Normal', 'High Priority', 'Urgent')),
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            planned_completion DATE,
            
            -- Workflow Status
            status TEXT DEFAULT 'open' CHECK (status IN ('open', 'assigned', 'in_progress', 'completed', 'approved', 'rejected')),
            assigned_builder TEXT,
            
            -- Completion Tracking
            completed_by TEXT,
            completed_at TIMESTAMP,
            completion_notes TEXT,
            completion_photos TEXT, -- JSON array of photo paths
            
            -- Approval Tracking
            approved_by TEXT,
            approved_at TIMESTAMP,
            approval_notes TEXT,
            
            FOREIGN KEY (inspection_id) REFERENCES inspections(id),
            FOREIGN KEY (assigned_builder) REFERENCES users(username),
            FOREIGN KEY (completed_by) REFERENCES users(username),
            FOREIGN KEY (approved_by) REFERENCES users(username)
        )
    ''')
    print("✅ Defects table created")
    
    # Step 9: Create Audit Log table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            action TEXT,
            resource_type TEXT,
            resource_id TEXT,
            details TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ip_address TEXT
        )
    ''')
    print("✅ Audit log table created")
    
    # Step 10: Create indexes for better performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_defects_status ON defects(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_defects_urgency ON defects(urgency)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_defects_unit ON defects(unit_number)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_inspections_building ON inspections(building_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_inspections_latest ON inspections(is_latest)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_permissions_user ON user_permissions(username)')
    print("✅ Database indexes created")
    
    # Commit all changes
    conn.commit()
    conn.close()
    
    print(f"✅ Database setup complete! File created at: {os.path.abspath(db_path)}")
    return True

def hash_password(password):
    """Hash password with salt - same method as your current system"""
    salt = "inspection_app_salt_2024"
    return hashlib.sha256((password + salt).encode()).hexdigest()

def create_default_users(db_path="inspection_system.db"):
    """
    Create default users for testing
    This includes all role types you'll need
    """
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    default_users = [
        {
            "username": "admin",
            "password": "admin123",
            "full_name": "System Administrator",
            "email": "admin@company.com",
            "role": "admin"
        },
        {
            "username": "developer1",
            "password": "dev123",
            "full_name": "John Developer",
            "email": "john@developercompany.com",
            "role": "property_developer"
        },
        {
            "username": "manager1",
            "password": "mgr123",
            "full_name": "Sarah Manager",
            "email": "sarah@company.com",
            "role": "project_manager"
        },
        {
            "username": "inspector1",
            "password": "ins123",
            "full_name": "Mike Inspector",
            "email": "mike@company.com",
            "role": "inspector"
        },
        {
            "username": "builder1",
            "password": "build123",
            "full_name": "Tom Builder",
            "email": "tom@buildercompany.com",
            "role": "builder"
        }
    ]
    
    created_count = 0
    
    for user in default_users:
        try:
            password_hash = hash_password(user["password"])
            
            cursor.execute('''
                INSERT INTO users (username, password_hash, full_name, email, role, created_by)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user["username"], password_hash, user["full_name"], 
                  user["email"], user["role"], "system"))
            
            created_count += 1
            print(f"✅ Created user: {user['username']} ({user['role']})")
            
        except sqlite3.IntegrityError:
            print(f"⚠️  User {user['username']} already exists, skipping")
    
    conn.commit()
    conn.close()
    
    print(f"✅ {created_count} default users created")
    return created_count

def create_sample_portfolio_structure(db_path="inspection_system.db"):
    """
    Create sample portfolio/project/building structure for testing
    """
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Create sample portfolio
        cursor.execute('''
            INSERT INTO portfolios (id, name, description, owner_username)
            VALUES (?, ?, ?, ?)
        ''', ("portfolio_001", "Downtown Development Portfolio", 
              "Premium residential and commercial developments", "developer1"))
        
        # Create sample projects
        projects = [
            ("project_001", "portfolio_001", "Skyline Towers", 
             "Luxury apartment complex with 200 units", "manager1"),
            ("project_002", "portfolio_001", "Heritage Square", 
             "Historic building conversion to modern apartments", "manager1")
        ]
        
        for project in projects:
            cursor.execute('''
                INSERT INTO projects (id, portfolio_id, name, description, manager_username)
                VALUES (?, ?, ?, ?, ?)
            ''', project)
        
        # Create sample buildings
        buildings = [
            ("building_001", "project_001", "Tower A", "123 Main Street, Melbourne VIC 3000", 100, "Apartment"),
            ("building_002", "project_001", "Tower B", "125 Main Street, Melbourne VIC 3000", 100, "Apartment"),
            ("building_003", "project_002", "Heritage North Wing", "45 Heritage Street, Melbourne VIC 3000", 50, "Apartment")
        ]
        
        for building in buildings:
            cursor.execute('''
                INSERT INTO buildings (id, project_id, name, address, total_units, building_type)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', building)
        
        # Grant permissions
        permissions = [
            ("manager1", "project", "project_001", "admin", "admin"),
            ("manager1", "project", "project_002", "admin", "admin"),
            ("inspector1", "building", "building_001", "write", "manager1"),
            ("inspector1", "building", "building_002", "write", "manager1"),
            ("builder1", "building", "building_001", "read", "manager1"),
            ("builder1", "building", "building_002", "read", "manager1")
        ]
        
        for perm in permissions:
            cursor.execute('''
                INSERT INTO user_permissions (username, resource_type, resource_id, permission_level, granted_by)
                VALUES (?, ?, ?, ?, ?)
            ''', perm)
        
        conn.commit()
        print("✅ Sample portfolio structure created")
        print("   - 1 Portfolio: Downtown Development Portfolio")
        print("   - 2 Projects: Skyline Towers, Heritage Square")
        print("   - 3 Buildings: Tower A, Tower B, Heritage North Wing")
        print("   - User permissions assigned")
        
    except sqlite3.IntegrityError as e:
        print(f"⚠️  Sample data already exists: {e}")
    
    conn.close()

def verify_database_setup(db_path="inspection_system.db"):
    """
    Verify that the database was created correctly
    """
    
    if not os.path.exists(db_path):
        print(f"❌ Database file not found: {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    expected_tables = ['users', 'portfolios', 'projects', 'buildings', 
                      'user_permissions', 'inspections', 'defects', 'audit_log']
    
    missing_tables = [table for table in expected_tables if table not in tables]
    
    if missing_tables:
        print(f"❌ Missing tables: {missing_tables}")
        conn.close()
        return False
    
    # Check users exist
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]
    
    # Check sample data
    cursor.execute("SELECT COUNT(*) FROM portfolios")
    portfolio_count = cursor.fetchone()[0]
    
    conn.close()
    
    print("✅ Database verification complete:")
    print(f"   - All {len(expected_tables)} tables created")
    print(f"   - {user_count} users in system")
    print(f"   - {portfolio_count} portfolios in system")
    print(f"   - Database size: {os.path.getsize(db_path)} bytes")
    
    return True

def main():
    """
    Main setup function - run this to create your complete database
    """
    
    print("=== SQLite Database Setup for Inspection System ===")
    print()
    
    db_path = "inspection_system.db"
    
    # Step 1: Create database and tables
    print("Step 1: Creating database structure...")
    create_database(db_path)
    print()
    
    # Step 2: Create default users
    print("Step 2: Creating default users...")
    create_default_users(db_path)
    print()
    
    # Step 3: Create sample data
    print("Step 3: Creating sample portfolio structure...")
    create_sample_portfolio_structure(db_path)
    print()
    
    # Step 4: Verify setup
    print("Step 4: Verifying database setup...")
    success = verify_database_setup(db_path)
    print()
    
    if success:
        print("🎉 Database setup completed successfully!")
        print()
        print("Default Login Credentials:")
        print("Admin: admin / admin123")
        print("Developer: developer1 / dev123")
        print("Manager: manager1 / mgr123")
        print("Inspector: inspector1 / ins123")
        print("Builder: builder1 / build123")
        print()
        print(f"Database file created: {os.path.abspath(db_path)}")
        print("You can now use this database with your Streamlit app!")
    else:
        print("❌ Database setup failed. Please check the errors above.")

if __name__ == "__main__":
    main()