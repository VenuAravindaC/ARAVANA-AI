"""
ARVANA Database Layer - Supabase PostgreSQL
Manages multi-tenant clients, conversation history, message memory,
and qualified lead tracking.
Includes an in-memory fallback for immediate zero-config local testing.
"""

import os
import uuid
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
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
                "customer_phone": customer_phone,
                "bot_active": True  # Feature 3: Bot is active by default
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
            "started_at": datetime.now(timezone.utc).isoformat(),
            "bot_active": True  # Feature 3: Bot is active by default
        }
    return _mock_conversations[key]


async def save_message(conversation_id: str, sender: str, content: str) -> dict:
    """Appends a message to the conversation history."""
    msg = {
        "id": str(uuid.uuid4()),
        "conversation_id": conversation_id,
        "sender": sender,  # 'customer' or 'ai'
        "content": content,
        "timestamp": datetime.now(timezone.utc).isoformat()
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
    key = f"{client_id}:{customer_phone}"
    lead_id = lead_data.get("id")
    if not lead_id:
        if key in _mock_leads and "id" in _mock_leads[key]:
            lead_id = _mock_leads[key]["id"]
        else:
            lead_id = str(uuid.uuid4())

    record = {
        "id": lead_id,
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
        "updated_at": datetime.now(timezone.utc).isoformat()
    }

    if supabase_client:
        try:
            res = supabase_client.table("leads").upsert(record, on_conflict="client_id,customer_phone").execute()
            if res.data:
                return res.data[0]
        except Exception as e:
            logger.error(f"Error upserting lead into Supabase: {e}")

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


async def pause_bot_for_conversation(conversation_id: str) -> dict:
    """Feature 3: Pauses the bot for a conversation (human handoff)."""
    if supabase_client:
        try:
            res = supabase_client.table("conversations")\
                .update({"bot_active": False})\
                .eq("id", conversation_id)\
                .execute()
            return {"status": "bot_paused", "conversation_id": conversation_id}
        except Exception as e:
            logger.error(f"Error pausing bot: {e}")

    # In-memory fallback
    for key, conv in _mock_conversations.items():
        if conv["id"] == conversation_id:
            conv["bot_active"] = False
            return {"status": "bot_paused", "conversation_id": conversation_id}

    return {"status": "conversation_not_found"}


async def resume_bot_for_conversation(conversation_id: str) -> dict:
    """Feature 3: Resumes the bot for a conversation."""
    if supabase_client:
        try:
            res = supabase_client.table("conversations")\
                .update({"bot_active": True})\
                .eq("id", conversation_id)\
                .execute()
            return {"status": "bot_resumed", "conversation_id": conversation_id}
        except Exception as e:
            logger.error(f"Error resuming bot: {e}")

    # In-memory fallback
    for key, conv in _mock_conversations.items():
        if conv["id"] == conversation_id:
            conv["bot_active"] = True
            return {"status": "bot_resumed", "conversation_id": conversation_id}

    return {"status": "conversation_not_found"}


# =====================================================================
# AGENCY ADMIN & EXTENDED CRM DATABASE OPERATIONS
# =====================================================================

async def get_all_clients() -> List[Dict[str, Any]]:
    """Retrieves all registered clients for the Agency Admin panel."""
    if supabase_client:
        try:
            res = supabase_client.table("clients").select("*").order("created_at", desc=False).execute()
            return res.data or []
        except Exception as e:
            logger.error(f"Error fetching all clients: {e}")
    return list(_mock_clients.values())


async def get_client_by_id(client_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a client by its UUID."""
    if supabase_client:
        try:
            res = supabase_client.table("clients").select("*").eq("id", client_id).execute()
            if res.data:
                return res.data[0]
        except Exception as e:
            logger.error(f"Error fetching client by id {client_id}: {e}")
    for client in _mock_clients.values():
        if client.get("id") == client_id:
            return client
    return None


async def create_client(client_data: Dict[str, Any]) -> Dict[str, Any]:
    """Creates a new client record in Supabase."""
    if "id" not in client_data or not client_data["id"]:
        client_data["id"] = str(uuid.uuid4())
    client_data["created_at"] = datetime.now(timezone.utc).isoformat()
    client_data["updated_at"] = datetime.now(timezone.utc).isoformat()

    if supabase_client:
        try:
            res = supabase_client.table("clients").insert(client_data).execute()
            if res.data:
                return res.data[0]
        except Exception as e:
            logger.error(f"Error creating client in Supabase: {e}")
            raise e

    _mock_clients[client_data["id"]] = client_data
    return client_data


async def update_client(client_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Updates client settings, prompts, classification rules, or status."""
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

    if supabase_client:
        try:
            res = supabase_client.table("clients").update(update_data).eq("id", client_id).execute()
            if res.data:
                return res.data[0]
        except Exception as e:
            logger.error(f"Error updating client {client_id} in Supabase: {e}")
            raise e

    for client in _mock_clients.values():
        if client.get("id") == client_id:
            client.update(update_data)
            return client
    return None


async def delete_client(client_id: str) -> bool:
    """Deletes a client record from Supabase or mock database."""
    if supabase_client:
        try:
            supabase_client.table("clients").delete().eq("id", client_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error deleting client {client_id} in Supabase: {e}")
            return False

    keys_to_del = [k for k, c in _mock_clients.items() if c.get("id") == client_id or k == client_id]
    if keys_to_del:
        for k in keys_to_del:
            del _mock_clients[k]
        return True
    return False


async def get_conversations_by_client(client_id: str) -> List[Dict[str, Any]]:
    """Retrieves all conversations for a client, ordered by latest activity."""
    if supabase_client:
        try:
            res = supabase_client.table("conversations")\
                .select("*")\
                .eq("client_id", client_id)\
                .order("last_message_at", desc=True)\
                .execute()
            return res.data or []
        except Exception as e:
            logger.error(f"Error fetching conversations for client {client_id}: {e}")
    filtered = [c for c in _mock_conversations.values() if c.get("client_id") == client_id]
    return sorted(filtered, key=lambda x: x.get("started_at", ""), reverse=True)


async def get_messages_by_conversation(conversation_id: str) -> List[Dict[str, Any]]:
    """Retrieves all message history for a conversation in chronological order."""
    if supabase_client:
        try:
            res = supabase_client.table("messages")\
                .select("*")\
                .eq("conversation_id", conversation_id)\
                .order("timestamp", desc=False)\
                .execute()
            return res.data or []
        except Exception as e:
            logger.error(f"Error fetching messages for conversation {conversation_id}: {e}")
    filtered = [m for m in _mock_messages if m.get("conversation_id") == conversation_id]
    return sorted(filtered, key=lambda x: x.get("timestamp", ""))


async def update_lead_status(lead_id: str, classification: Optional[str] = None, status: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Updates a lead's qualification classification (HOT/WARM/COLD) and/or deal status (NEW/WON/LOST)."""
    updates = {"updated_at": datetime.now(timezone.utc).isoformat()}
    if classification:
        updates["classification"] = classification
    if status:
        updates["status"] = status

    if supabase_client:
        try:
            res = supabase_client.table("leads").update(updates).eq("id", lead_id).execute()
            if res.data:
                return res.data[0]
        except Exception as e:
            logger.error(f"Error updating lead {lead_id} in Supabase: {e}")
            raise e

    for lead in _mock_leads.values():
        if lead.get("id") == lead_id:
            lead.update(updates)
            return lead
    return None


async def get_lead_by_id(lead_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a single lead by its UUID."""
    if supabase_client:
        try:
            res = supabase_client.table("leads").select("*").eq("id", lead_id).execute()
            if res.data:
                return res.data[0]
        except Exception as e:
            logger.error(f"Error fetching lead {lead_id} from Supabase: {e}")

    for lead in _mock_leads.values():
        if lead.get("id") == lead_id:
            return lead
    return None


async def get_conversation_by_id(conversation_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a conversation by its UUID."""
    if supabase_client:
        try:
            res = supabase_client.table("conversations").select("*").eq("id", conversation_id).execute()
            if res.data:
                return res.data[0]
        except Exception as e:
            logger.error(f"Error fetching conversation {conversation_id} from Supabase: {e}")

    for conv in _mock_conversations.values():
        if conv.get("id") == conversation_id:
            return conv
    return None

