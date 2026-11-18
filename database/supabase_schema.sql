-- =====================================================================
-- ARVANA AI Multi-Tenant Lead Automation Database Schema
-- Run this script in your Supabase SQL Editor (https://supabase.com/dashboard)
-- =====================================================================

-- 1. Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. Clients Table (ARVANA + Future Paying Clients)
CREATE TABLE IF NOT EXISTS clients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    business_name TEXT NOT NULL,
    phone_number_id TEXT UNIQUE NOT NULL,
    waba_id TEXT,
    access_token TEXT,
    status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'SUSPENDED', 'TRIAL', 'CANCELLED')),
    system_prompt TEXT,
    business_knowledge JSONB,
    extraction_schema TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Conversations Table (Grouped by customer phone & client)
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    customer_phone TEXT NOT NULL,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    last_message_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(client_id, customer_phone)
);

-- 4. Messages Table (Conversation Memory for AI)
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    sender TEXT NOT NULL CHECK (sender IN ('customer', 'ai')),
    content TEXT NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Leads Table (CRM Lead Tracking)
CREATE TABLE IF NOT EXISTS leads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
    customer_phone TEXT NOT NULL,
    name TEXT,
    industry TEXT,
    service TEXT,
    monthly_lead_volume TEXT,
    budget_range TEXT,
    timeline TEXT,
    classification TEXT NOT NULL DEFAULT 'NEW' CHECK (classification IN ('NEW', 'HOT', 'WARM', 'COLD')),
    status TEXT NOT NULL DEFAULT 'NEW' CHECK (status IN ('NEW', 'CONTACTED', 'WON', 'LOST')),
    ai_summary TEXT,
    custom_data JSONB DEFAULT '{}'::jsonb,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(client_id, customer_phone)
);

-- 6. Indexes for Blazing-Fast Performance
CREATE INDEX IF NOT EXISTS idx_clients_phone_id ON clients(phone_number_id);
CREATE INDEX IF NOT EXISTS idx_conversations_lookup ON conversations(client_id, customer_phone);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_leads_client_class ON leads(client_id, classification);

-- 7. Insert Initial Seed Record for ARVANA (Client #1)
INSERT INTO clients (business_name, phone_number_id, status, system_prompt)
VALUES (
    'ARVANA',
    'default_arvana_id',
    'ACTIVE',
    'You are ARVANA''s AI lead qualification assistant on WhatsApp. Greet warmly, qualify business automation needs, and capture budget & timeline.'
)
ON CONFLICT (phone_number_id) DO NOTHING;
