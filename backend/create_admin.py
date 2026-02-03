"""
Create Default Admin User Script
Run this script to create the default admin user in PostgreSQL

Usage:
    cd C:\Apps\Smartcharge2026\backend
    .\venv\Scripts\activate
    python create_admin.py
"""

import asyncio
import bcrypt
import uuid
from datetime import datetime, timezone
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

# Get database URL from environment
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql+asyncpg://postgres:postgres@localhost:5432/evcharging')

# Convert SQLAlchemy URL to asyncpg format
# From: postgresql+asyncpg://user:pass@host:port/db
# To: postgresql://user:pass@host:port/db
PG_URL = DATABASE_URL.replace('postgresql+asyncpg://', 'postgresql://')

async def create_admin():
    print("Connecting to database...")
    
    try:
        conn = await asyncpg.connect(PG_URL)
        print("Connected successfully!")
        
        # Check if users table exists
        table_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'users'
            );
        """)
        
        if not table_exists:
            print("Creating users table...")
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id VARCHAR PRIMARY KEY,
                    email VARCHAR UNIQUE NOT NULL,
                    name VARCHAR NOT NULL,
                    password_hash VARCHAR NOT NULL,
                    role VARCHAR DEFAULT 'user',
                    pricing_group_id VARCHAR,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            """)
            print("Users table created!")
        
        # Check if admin user exists
        admin = await conn.fetchrow(
            "SELECT * FROM users WHERE email = $1",
            "admin@evcharge.com"
        )
        
        if admin:
            print(f"Admin user already exists: {admin['email']}")
            print("Resetting password to 'admin123'...")
            
            # Reset password
            password_hash = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            await conn.execute(
                "UPDATE users SET password_hash = $1 WHERE email = $2",
                password_hash, "admin@evcharge.com"
            )
            print("Password reset successfully!")
        else:
            print("Creating admin user...")
            
            # Create password hash
            password_hash = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            # Insert admin user
            await conn.execute("""
                INSERT INTO users (id, email, name, password_hash, role, created_at)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, 
                str(uuid.uuid4()),
                "admin@evcharge.com",
                "Admin User",
                password_hash,
                "admin",
                datetime.now(timezone.utc)
            )
            print("Admin user created successfully!")
        
        await conn.close()
        
        print("\n" + "="*50)
        print("Login Credentials:")
        print("  Email: admin@evcharge.com")
        print("  Password: admin123")
        print("="*50)
        
    except Exception as e:
        print(f"Error: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(create_admin())
