-- Insert a TEST client for development/testing
-- Run this in Supabase SQL Editor
-- DELETE THIS CLIENT before going live with real client onboarding

INSERT INTO clients (
  id,
  business_name,
  phone_number_id,
  access_token,
  system_prompt,
  business_knowledge,
  broker_whatsapp,
  classification_rules,
  status
) VALUES (
  '00000000-0000-0000-0000-000000000001',
  'TEST Real Estate Agency',
  'test_phone_number_id_123',
  'test_access_token_replace_later',
  'You are a helpful real estate assistant. Keep responses under 3 sentences. Ask ONE question at a time. If you don''t know something, say "Let me connect you with our team."',
  '{"location": "Bangalore", "property_types": ["3BHK", "2BHK", "Villa"], "price_range": "50L-2Cr", "areas": ["Whitefield", "Indiranagar", "Koramangala"]}',
  '919999999999',
  '- HOT: Clear budget + urgent timeline (within 7 days) OR loan approved OR says "ready to buy" OR wants immediate site visit
- WARM: Interested in specific property type, has budget but timeline flexible
- COLD: Just browsing, no budget mentioned, or unresponsive
- NEW: Initial inquiry, not enough information yet',
  'ACTIVE'
)
ON CONFLICT (id) DO UPDATE SET
  business_name = EXCLUDED.business_name,
  phone_number_id = EXCLUDED.phone_number_id,
  system_prompt = EXCLUDED.system_prompt,
  business_knowledge = EXCLUDED.business_knowledge,
  broker_whatsapp = EXCLUDED.broker_whatsapp,
  classification_rules = EXCLUDED.classification_rules,
  status = EXCLUDED.status;

-- Verify it was inserted
SELECT id, business_name, phone_number_id, broker_whatsapp, status
FROM clients
WHERE id = '00000000-0000-0000-0000-000000000001';
