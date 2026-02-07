"""
Database Migration Script - Add RFID columns to users table
Run this script once to update your database schema.
"""
import psycopg2
import bcrypt

# Database connection settings - update if different
DB_CONFIG = {
    "dbname": "evcharging",
    "user": "evuser",
    "password": "evpass",
    "host": "localhost",
    "port": 5432
}

def run_migration():
    print("Connecting to database...")
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True
        cur = conn.cursor()
        print("✓ Connected to database")
        
        # Step 1: Add RFID columns if they don't exist
        print("\nStep 1: Adding RFID columns to users table...")
        
        columns_to_add = [
            ("rfid_card_number", "VARCHAR"),
            ("rfid_balance", "FLOAT DEFAULT 0"),
            ("rfid_status", "VARCHAR DEFAULT 'active'")
        ]
        
        for col_name, col_type in columns_to_add:
            try:
                cur.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
                print(f"  ✓ Added column: {col_name}")
            except psycopg2.errors.DuplicateColumn:
                print(f"  - Column {col_name} already exists")
                conn.rollback()
        
        # Step 2: Check current users
        print("\nStep 2: Checking current users...")
        cur.execute("SELECT id, email, name, role FROM users")
        users = cur.fetchall()
        print(f"  Found {len(users)} users:")
        for user in users:
            print(f"    - {user[2]} ({user[1]}) - Role: {user[3]}")
        
        # Step 3: Create or reset admin user
        print("\nStep 3: Creating/resetting admin user...")
        password = "admin123"
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        cur.execute("SELECT id FROM users WHERE email = 'admin@evcharge.com'")
        existing = cur.fetchone()
        
        if existing:
            cur.execute("""
                UPDATE users 
                SET password_hash = %s, name = 'Administrator', role = 'admin'
                WHERE email = 'admin@evcharge.com'
            """, (password_hash,))
            print("  ✓ Admin password reset")
        else:
            cur.execute("""
                INSERT INTO users (id, email, name, password_hash, role, rfid_balance, rfid_status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, ('admin-001', 'admin@evcharge.com', 'Administrator', password_hash, 'admin', 0, 'active'))
            print("  ✓ Admin user created")
        
        # Step 4: Verify table structure
        print("\nStep 4: Verifying table structure...")
        cur.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'users'
            ORDER BY ordinal_position
        """)
        columns = cur.fetchall()
        print("  Users table columns:")
        for col in columns:
            print(f"    - {col[0]}: {col[1]}")
        
        cur.close()
        conn.close()
        
        print("\n" + "="*50)
        print("MIGRATION COMPLETE!")
        print("="*50)
        print("\nYou can now login with:")
        print("  Email: admin@evcharge.com")
        print("  Password: admin123")
        print("\nRestart MASTER SERVER.bat and try logging in.")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        print("\nMake sure PostgreSQL is running and credentials are correct.")
        raise

if __name__ == "__main__":
    run_migration()
