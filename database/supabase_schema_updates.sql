-- ARVANA Database Schema Updates
-- Fix 2: Add missing columns to Supabase tables

-- 1. Add bot_active column to conversations table (Feature 3: Human Handoff)
ALTER TABLE conversations
ADD COLUMN IF NOT EXISTS bot_active BOOLEAN DEFAULT TRUE;

-- 2. Add classification_rules column to clients table (Customizable HOT/WARM/COLD criteria)
ALTER TABLE clients
ADD COLUMN IF NOT EXISTS classification_rules TEXT;

-- 3. Create bookings table (Feature 2: Calendar/Booking System)
CREATE TABLE IF NOT EXISTS bookings (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
  conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
  customer_phone TEXT NOT NULL,
  customer_name TEXT,
  date DATE NOT NULL,
  time TEXT NOT NULL,
  property_info TEXT,
  status TEXT DEFAULT 'CONFIRMED' CHECK (status IN ('CONFIRMED', 'CANCELLED', 'COMPLETED')),
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Prevent double-booking: only one CONFIRMED booking per client per date/time
CREATE UNIQUE INDEX IF NOT EXISTS idx_booking_no_double
ON bookings(client_id, date, time)
WHERE status = 'CONFIRMED';

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_bookings_client_date
ON bookings(client_id, date);

-- 4. Create availability table (Broker custom availability)
CREATE TABLE IF NOT EXISTS availability (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
  date DATE NOT NULL,
  time TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('AVAILABLE', 'BLOCKED', 'UNAVAILABLE')),
  updated_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(client_id, date, time)
);

-- Index for faster availability checks
CREATE INDEX IF NOT EXISTS idx_availability_client_date
ON availability(client_id, date);

-- 5. Add broker_whatsapp column to clients table (For HOT lead alerts)
ALTER TABLE clients
ADD COLUMN IF NOT EXISTS broker_whatsapp TEXT;

-- 6. Add notification_phone column as alternative (backward compatibility)
ALTER TABLE clients
ADD COLUMN IF NOT EXISTS notification_phone TEXT;

-- Done!
COMMENT ON COLUMN conversations.bot_active IS 'Feature 3: When FALSE, bot is paused and human is handling the conversation';
COMMENT ON COLUMN clients.classification_rules IS 'Custom HOT/WARM/COLD criteria per industry';
COMMENT ON COLUMN clients.broker_whatsapp IS 'Phone number to receive HOT lead alerts';
COMMENT ON TABLE bookings IS 'Feature 2: Site visit bookings with calendar integration';
COMMENT ON TABLE availability IS 'Broker custom availability schedule';
