"""
Create Default Admin User and Database Tables
Run this script to initialize the database for SmartCharge

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
PG_URL = DATABASE_URL.replace('postgresql+asyncpg://', 'postgresql://')

async def create_tables(conn):
    """Create all required database tables"""
    print("Creating database tables...")
    
    # Users table
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id VARCHAR PRIMARY KEY,
            email VARCHAR UNIQUE NOT NULL,
            name VARCHAR NOT NULL,
            password_hash VARCHAR NOT NULL,
            role VARCHAR DEFAULT 'user',
            pricing_group_id VARCHAR,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)
    
    # Transactions table
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id VARCHAR PRIMARY KEY,
            tx_id VARCHAR,
            station VARCHAR,
            connector VARCHAR,
            connector_type VARCHAR,
            account VARCHAR,
            start_time VARCHAR,
            end_time VARCHAR,
            meter_value FLOAT DEFAULT 0,
            charging_duration VARCHAR,
            cost FLOAT DEFAULT 0,
            payment_status VARCHAR DEFAULT 'PENDING',
            payment_type VARCHAR,
            payment_date VARCHAR,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)
    
    # Chargers table
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS chargers (
            id VARCHAR PRIMARY KEY,
            charger_id VARCHAR UNIQUE NOT NULL,
            name VARCHAR NOT NULL,
            location VARCHAR,
            status VARCHAR DEFAULT 'Available',
            connectors JSONB DEFAULT '[]',
            last_heartbeat TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)
    
    # Pricing rules table
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS pricing_rules (
            id VARCHAR PRIMARY KEY,
            account VARCHAR,
            connector VARCHAR,
            connector_type VARCHAR,
            price_per_kwh FLOAT NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)
    
    # Pricing groups table
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS pricing_groups (
            id VARCHAR PRIMARY KEY,
            name VARCHAR UNIQUE NOT NULL,
            description TEXT,
            connector_pricing JSONB DEFAULT '{}',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE
        )
    """)
    
    # RFID cards table
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS rfid_cards (
            id VARCHAR PRIMARY KEY,
            card_number VARCHAR UNIQUE NOT NULL,
            user_id VARCHAR NOT NULL,
            balance FLOAT DEFAULT 0,
            status VARCHAR DEFAULT 'active',
            low_balance_threshold FLOAT DEFAULT 10000,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)
    
    # RFID history table
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS rfid_history (
            id VARCHAR PRIMARY KEY,
            card_id VARCHAR NOT NULL,
            timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            type VARCHAR,
            amount FLOAT,
            description TEXT,
            balance_before FLOAT,
            balance_after FLOAT
        )
    """)
    
    # App config table
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS app_config (
            id VARCHAR PRIMARY KEY,
            config_type VARCHAR UNIQUE NOT NULL,
            config_data JSONB DEFAULT '{}',
            updated_at TIMESTAMP WITH TIME ZONE
        )
    """)
    
    print("All tables created successfully!")

async def create_admin():
    print("="*50)
    print("SmartCharge Database Setup")
    print("="*50)
    print()
    print(f"Connecting to: {PG_URL[:50]}...")
    
    try:
        conn = await asyncpg.connect(PG_URL, timeout=10)
        print("Connected successfully!")
        print()
        
        # Create all tables
        await create_tables(conn)
        print()
        
        # Check if admin user exists
        admin = await conn.fetchrow(
            "SELECT * FROM users WHERE email = $1",
            "admin@evcharge.com"
        )
        
        # Create password hash
        password_hash = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        if admin:
            print(f"Admin user exists: {admin['email']}")
            print("Resetting password to 'admin123'...")
            await conn.execute(
                "UPDATE users SET password_hash = $1 WHERE email = $2",
                password_hash, "admin@evcharge.com"
            )
            print("Password reset!")
        else:
            print("Creating admin user...")
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
            print("Admin user created!")
        
        await conn.close()
        
        print()
        print("="*50)
        print("SUCCESS! Login Credentials:")
        print("  Email:    admin@evcharge.com")
        print("  Password: admin123")
        print("="*50)
        
    except Exception as e:
        print()
        print("="*50)
        print(f"ERROR: {e}")
        print("="*50)
        print()
        print("Please check:")
        print("  1. PostgreSQL is running")
        print("  2. Database 'evcharging' exists")
        print("  3. DATABASE_URL in .env is correct")
        raise

if __name__ == "__main__":
    asyncio.run(create_admin())
