"""
ARVANA Database Layer - Supabase PostgreSQL
Manages multi-tenant clients, conversation history, message memory,
and qualified lead tracking.
Includes an in-memory fallback for immediate zero-config local testing.
"""

import os
import uuid
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("arvana.db")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

supabase_client = None
if SUPABASE_URL and SUPABASE_KEY and SUPABASE_URL != "your_supabase_project_url":
    try:
        from supabase import create_client, Client
        supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("Connected to live Supabase database.")
    except Exception as e:
        logger.warning(f"Could not connect to Supabase: {e}")

# In-memory mock database for local development without credentials
_mock_clients = {
    "default": {
        "id": "00000000-0000-0000-0000-000000000001",
        "business_name": "ARVANA",
        "phone_number_id": os.getenv("META_PHONE_NUMBER_ID") or "default_arvana_id",
        "access_token": None,
        "status": "ACTIVE",
        "system_prompt": None,
        "business_knowledge": None,
        "extraction_schema": None
    }
}
_mock_conversations = {}
_mock_messages = []
_mock_leads = {}


async def get_client_by_phone_id(phone_number_id: str) -> dict:
    """Retrieves client settings and prompt by Meta Phone Number ID."""
    if supabase_client:
        try:
            res = supabase_client.table("clients").select("*").eq("phone_number_id", phone_number_id).execute()
            if res.data:
                return res.data[0]
        except Exception as e:
            logger.error(f"Error fetching client from Supabase: {e}")

    # Fallback to ARVANA default client
    client = _mock_clients.get(phone_number_id) or _mock_clients["default"]
    return client


async def get_or_create_conversation(client_id: str, customer_phone: str) -> dict:
    """Finds or creates an active conversation for a customer phone number."""
    if supabase_client:
        try:
            res = supabase_client.table("conversations")\
                .select("*")\
                .eq("client_id", client_id)\
                .eq("customer_phone", customer_phone)\
                .execute()
            if res.data:
                return res.data[0]

            new_conv = {
                "client_id": client_id,
                "customer_phone": customer_phone
            }
            insert_res = supabase_client.table("conversations").insert(new_conv).execute()
            return insert_res.data[0]
        except Exception as e:
            logger.error(f"Supabase conversation error: {e}")

    # In-memory fallback
    key = f"{client_id}:{customer_phone}"
    if key not in _mock_conversations:
        _mock_conversations[key] = {
            "id": str(uuid.uuid4()),
            "client_id": client_id,
            "customer_phone": customer_phone,
            "started_at": datetime.utcnow().isoformat()
        }
    return _mock_conversations[key]


async def save_message(conversation_id: str, sender: str, content: str) -> dict:
    """Appends a message to the conversation history."""
    msg = {
        "id": str(uuid.uuid4()),
        "conversation_id": conversation_id,
        "sender": sender,  # 'customer' or 'ai'
        "content": content,
        "timestamp": datetime.utcnow().isoformat()
    }

    if supabase_client:
        try:
            supabase_client.table("messages").insert(msg).execute()
        except Exception as e:
            logger.error(f"Error saving message to Supabase: {e}")

    _mock_messages.append(msg)
    return msg


async def get_conversation_history(conversation_id: str, limit: int = 10) -> list:
    """Returns conversation history formatted for Gemini AI."""
    if supabase_client:
        try:
            res = supabase_client.table("messages")\
                .select("*")\
                .eq("conversation_id", conversation_id)\
                .order("timestamp", desc=False)\
                .limit(limit)\
                .execute()
            if res.data:
                return [
                    {"role": "user" if m["sender"] == "customer" else "assistant", "content": m["content"]}
                    for m in res.data
                ]
        except Exception as e:
            logger.error(f"Error loading message history from Supabase: {e}")

    # In-memory history
    filtered = [m for m in _mock_messages if m["conversation_id"] == conversation_id]
    return [
        {"role": "user" if m["sender"] == "customer" else "assistant", "content": m["content"]}
        for m in filtered[-limit:]
    ]


async def upsert_lead(client_id: str, conversation_id: str, customer_phone: str, lead_data: dict) -> dict:
    """Creates or updates a qualified lead entry for the CRM dashboard."""
    record = {
        "client_id": client_id,
        "conversation_id": conversation_id,
        "customer_phone": customer_phone,
        "name": lead_data.get("name") or lead_data.get("customer_name"),
        "industry": lead_data.get("business_type") or lead_data.get("industry"),
        "service": lead_data.get("service_needed") or lead_data.get("inquiry_type") or lead_data.get("service") or lead_data.get("property_type"),
        "budget_range": lead_data.get("budget_range") or lead_data.get("budget"),
        "timeline": lead_data.get("timeline"),
        "classification": lead_data.get("classification", "NEW"),
        "ai_summary": lead_data.get("ai_summary"),
        "custom_data": lead_data,
        "updated_at": datetime.utcnow().isoformat()
    }

    if supabase_client:
        try:
            res = supabase_client.table("leads").upsert(record, on_conflict="client_id,customer_phone").execute()
            if res.data:
                return res.data[0]
        except Exception as e:
            logger.error(f"Error upserting lead into Supabase: {e}")

    key = f"{client_id}:{customer_phone}"
    _mock_leads[key] = record
    return record


async def get_all_leads(client_id: str = None) -> list:
    """Retrieves all qualified leads (filtered by client if provided)."""
    if supabase_client:
        try:
            query = supabase_client.table("leads").select("*").order("updated_at", desc=True)
            if client_id:
                query = query.eq("client_id", client_id)
            res = query.execute()
            return res.data or []
        except Exception as e:
            logger.error(f"Error fetching leads from Supabase: {e}")

    return list(_mock_leads.values())
