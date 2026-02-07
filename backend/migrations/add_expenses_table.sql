-- Migration: Add expenses table
-- Date: 2025-02
-- Description: Creates the expenses table for tracking business expenditures

CREATE TABLE IF NOT EXISTS expenses (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    date VARCHAR(10) NOT NULL,
    cost FLOAT NOT NULL DEFAULT 0,
    reason TEXT,
    created_by VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Create index for date-based queries
CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(date);

-- Create index for filtering by creator
CREATE INDEX IF NOT EXISTS idx_expenses_created_by ON expenses(created_by);
