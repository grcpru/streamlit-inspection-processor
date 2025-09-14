# database_test.py
# Simple test to verify your database is working

import sqlite3
import os

def test_database_connection():
    """Test basic database operations"""
    
    db_path = "inspection_system.db"
    
    if not os.path.exists(db_path):
        print("Database file not found! Run database_setup.py first.")
        return False
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Test 1: Check users table
        cursor.execute("SELECT username, role FROM users")
        users = cursor.fetchall()
        print(f"Found {len(users)} users in database:")
        for user in users:
            print(f"  - {user[0]} ({user[1]})")
        
        # Test 2: Check portfolios
        cursor.execute("SELECT name FROM portfolios")
        portfolios = cursor.fetchall()
        print(f"\nFound {len(portfolios)} portfolios:")
        for portfolio in portfolios:
            print(f"  - {portfolio[0]}")
        
        # Test 3: Check buildings
        cursor.execute("SELECT name, address FROM buildings")
        buildings = cursor.fetchall()
        print(f"\nFound {len(buildings)} buildings:")
        for building in buildings:
            print(f"  - {building[0]} at {building[1]}")
        
        # Test 4: Test authentication
        cursor.execute("SELECT username FROM users WHERE username = 'admin'")
        admin_user = cursor.fetchone()
        if admin_user:
            print(f"\nAdmin user found: {admin_user[0]}")
        
        conn.close()
        print("\nDatabase connection test successful!")
        return True
        
    except Exception as e:
        print(f"Database test failed: {e}")
        return False

def test_login_credentials():
    """Test that default login credentials work"""
    
    from database_setup import hash_password
    
    db_path = "inspection_system.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Test admin login
    admin_password_hash = hash_password("admin123")
    cursor.execute("""
        SELECT username, role FROM users 
        WHERE username = 'admin' AND password_hash = ?
    """, (admin_password_hash,))
    
    result = cursor.fetchone()
    if result:
        print(f"Admin login test successful: {result[0]} ({result[1]})")
    else:
        print("Admin login test failed!")
    
    conn.close()

if __name__ == "__main__":
    print("=== Database Connection Test ===")
    success = test_database_connection()
    
    if success:
        print("\n=== Login Credentials Test ===")
        test_login_credentials()