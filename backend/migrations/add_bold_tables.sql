-- SQL Migration: Add BOLD.CO payment tables
-- Run this in your PostgreSQL database after deploying the new code

-- Create bold_payments table
CREATE TABLE IF NOT EXISTS bold_payments (
    id VARCHAR PRIMARY KEY,
    reference_code VARCHAR UNIQUE NOT NULL,
    payment_link_id VARCHAR,
    rfid_card_id VARCHAR,
    card_number VARCHAR,
    user_id VARCHAR,
    amount FLOAT,
    buyer_name VARCHAR,
    buyer_email VARCHAR,
    buyer_phone VARCHAR,
    status VARCHAR DEFAULT 'ACTIVE',
    bold_response JSON DEFAULT '{}',
    bold_transaction_id VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Create index on reference_code
CREATE INDEX IF NOT EXISTS idx_bold_payments_reference_code ON bold_payments(reference_code);

-- Create index on payment_link_id
CREATE INDEX IF NOT EXISTS idx_bold_payments_payment_link_id ON bold_payments(payment_link_id);

-- Create bold_webhook_logs table
CREATE TABLE IF NOT EXISTS bold_webhook_logs (
    id VARCHAR PRIMARY KEY,
    reference_code VARCHAR,
    webhook_data JSON DEFAULT '{}',
    received_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create index on reference_code
CREATE INDEX IF NOT EXISTS idx_bold_webhook_logs_reference_code ON bold_webhook_logs(reference_code);

-- Note: The existing settings table will be used for BOLD.CO settings
-- with type='bold' and api_key stored in the api_key column
