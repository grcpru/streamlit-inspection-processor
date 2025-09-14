import sqlite3

def setup_default_portfolios():
    """Set up default portfolios for the system"""
    conn = sqlite3.connect("inspection_system.db")
    cursor = conn.cursor()
    
    # Create portfolios table if not exists
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS portfolios (
            id TEXT PRIMARY KEY,
            name TEXT,
            description TEXT,
            owner_username TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (owner_username) REFERENCES users(username)
        )
    ''')
    
    # Insert default portfolio
    cursor.execute('''
        INSERT OR IGNORE INTO portfolios (id, name, description, owner_username)
        VALUES (?, ?, ?, ?)
    ''', ("portfolio_001", "Main Development Portfolio", "Primary development portfolio", "developer1"))
    
    conn.commit()
    conn.close()
    print("Default portfolios created")

if __name__ == "__main__":
    setup_default_portfolios()