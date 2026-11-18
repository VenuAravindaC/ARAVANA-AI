"""
ARVANA Multi-Tenant AI Lead Management Backend
Built with FastAPI, Meta WhatsApp Cloud API, Google Gemini 1.5 Flash, and Supabase.
"""

import os
import logging
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, Request, Query, Response, HTTPException, status
from fastapi.responses import PlainTextResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from lib import whatsapp, ai, db, notifications, bookings, followups
from lib.debouncer import debouncer

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("arvana.main")

load_dotenv()

app = FastAPI(
    title="ARVANA AI Automation Agency Backend",
    description="Multi-tenant WhatsApp lead qualification, CRM engine & Meta Cloud API webhooks.",
    version="1.0.0"
)

# Enable CORS for future dashboard access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

VERIFY_TOKEN = os.getenv("META_VERIFY_TOKEN", "arvana_secret_webhook_verify_token_2026")


@app.get("/", summary="Health Check")
@app.get("/health", summary="Health Check Alias")
async def health_check():
    """Health check endpoint to verify backend status."""
    return {
        "status": "online",
        "service": "ARVANA AI Lead Management System",
        "version": "1.0.0",
        "docs_url": "/docs"
    }


# =====================================================================
# META WHATSAPP CLOUD API WEBHOOKS
# =====================================================================

@app.get("/webhook", summary="Meta Webhook Verification")
async def verify_webhook(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token")
):
    """
    Handles Meta's Webhook verification challenge (GET request).
    Meta checks this endpoint once when you register the webhook URL.
    """
    logger.info(f"Verification request: mode={hub_mode}, token={hub_verify_token}")

    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        logger.info("Webhook verification SUCCESSFUL!")
        # Return hub.challenge as plain text integer
        return PlainTextResponse(content=hub_challenge, status_code=200)

    logger.warning("Webhook verification FAILED: Invalid verify token.")
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Verification token mismatch")


@app.post("/webhook", summary="Meta Webhook Event Receiver")
async def receive_webhook(request: Request):
    """
    Receives incoming WhatsApp events from Meta Cloud API (POST request).
    Parses customer messages, passes them to AI, saves to database, and replies.
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"status": "invalid_json"}, status_code=400)

    # 1. Verify this is a WhatsApp event
    if body.get("object") != "whatsapp_business_account":
        return JSONResponse({"status": "ignored"}, status_code=200)

    entries = body.get("entry", [])
    for entry in entries:
        for change in entry.get("changes", []):
            val = change.get("value", {})
            metadata = val.get("metadata", {})
            phone_number_id = metadata.get("phone_number_id")

            # Check if this change includes incoming messages (not just status deliveries)
            messages = val.get("messages", [])
            for msg in messages:
                if msg.get("type") == "text":
                    customer_phone = msg.get("from")
                    message_text = msg.get("text", {}).get("body", "")

                    logger.info(f"Received WhatsApp from {customer_phone} to phone_id {phone_number_id}: {message_text}")

                    # IMMEDIATE STOP RULE: Cancel any scheduled follow-up sequence when customer replies
                    if customer_phone:
                        followups.cancel_pending_followup_for_customer(customer_phone)

                    # MESSAGE DEBOUNCING / BUFFERING (10s timer):
                    # Buffer rapid-fire messages from the same user so the AI generates
                    # a single cohesive reply to the entire thought.
                    async def _debounced_handler(phone: str, combined_text: str, meta: dict):
                        await process_incoming_message(
                            phone_number_id=meta.get("phone_number_id"),
                            customer_phone=phone,
                            message_text=combined_text
                        )

                    await debouncer.add_message(
                        key=customer_phone,
                        message_text=message_text,
                        handler=_debounced_handler,
                        metadata={"phone_number_id": phone_number_id}
                    )

    # Meta expects instant 200 OK to acknowledge receipt
    return JSONResponse({"status": "received"}, status_code=200)


# =====================================================================
# CORE LEAD PROCESSING PIPELINE
# =====================================================================

def is_booking_enabled_for_client(client: dict) -> bool:
    """Checks whether the booking agent is turned ON or OFF for this client."""
    if not client:
        return True
    if "booking_enabled" in client and client["booking_enabled"] is not None:
        return bool(client["booking_enabled"])
    bk = client.get("business_knowledge") or {}
    if isinstance(bk, dict) and "booking_enabled" in bk:
        return bool(bk["booking_enabled"])
    return True


async def process_incoming_message(
    phone_number_id: Optional[str] = None,
    customer_phone: str = None,
    message_text: str = None,
    client_id: Optional[str] = None,
    is_simulation: bool = False
) -> dict:
    """
    Central processing engine:
    1. Looks up client configuration (multi-tenancy)
    2. Checks active status (kill switch)
    3. FEATURE 3: Checks if bot is paused (human handoff mode)
    4. Loads conversation memory
    5. Generates contextual AI response with FEATURE 4 guardrails
    6. Sends WhatsApp reply (bypassed if is_simulation=True)
    7. Extracts structured lead criteria and saves to CRM
    8. FEATURE 5: Sends HOT lead alert to broker's WhatsApp
    9. FEATURE 2: Detects site visit booking requests (if booking agent enabled)
    """
    # 1. Fetch client config
    if client_id:
        client = await db.get_client_by_id(client_id)
    elif phone_number_id:
        client = await db.get_client_by_phone_id(phone_number_id)
    else:
        client = None

    if not client:
        logger.error(f"Client not found for client_id={client_id}, phone_id={phone_number_id}")
        return {
            "error": "Client not found",
            "status": "client_not_found",
            "reply": "Service currently unavailable. Please contact support.",
            "lead_data": {"classification": "NEW", "ai_summary": "Client not found."}
        }

    client_id = client["id"]
    phone_number_id = client.get("phone_number_id") or phone_number_id

    # 2. Check client status (Kill Switch) - in simulation mode we still allow prompt testing
    client_status = client.get("status", "ACTIVE")
    if client_status in ["PAUSED", "SUSPENDED", "INACTIVE"] and not is_simulation:
        logger.warning(f"Client {client.get('business_name')} status is '{client_status}'. Automatic AI reply suppressed.")
        return {"status": "service_paused", "client": client.get("business_name")}

    # 3. Get or create conversation
    conversation = await db.get_or_create_conversation(client_id, customer_phone)
    conv_id = conversation["id"]

    # IMMEDIATE STOP RULE: Cancel any scheduled follow-up sequence when customer sends a message
    if customer_phone:
        followups.cancel_pending_followup_for_customer(customer_phone)

    # FEATURE 3: Check if bot is paused (human handoff mode)
    if not conversation.get("bot_active", True):
        logger.info(f"Bot is PAUSED for conversation {conv_id}. Human is handling this chat.")
        if customer_phone:
            followups.cancel_pending_followup_for_customer(customer_phone)
        # Save the message but don't respond
        await db.save_message(conv_id, "customer", message_text)
        return {"status": "bot_paused", "conversation_id": conv_id, "message": "Human is handling this conversation"}

    # 4. Save incoming customer message
    await db.save_message(conv_id, "customer", message_text)

    # 5. Load recent conversation memory & milestone profile (preserves lead facts across 30-50+ turns)
    history = await db.get_conversation_history(conv_id, limit=10)
    milestone_memory = await db.get_conversation_milestones(conv_id)

    # FEATURE 2: Check booking agent toggle & booking request
    booking_agent_active = is_booking_enabled_for_client(client)
    message_lower = message_text.lower()
    booking_keywords = ["book", "visit", "appointment", "schedule", "viewing", "see the property", "when can"]
    is_booking_request = booking_agent_active and any(keyword in message_lower for keyword in booking_keywords)

    # Load available slots if this is about booking and booking agent is ON
    available_slots_text = None
    if is_booking_request:
        slots = await bookings.get_available_slots(client_id, days_ahead=7)
        available_slots_text = bookings.format_available_slots_for_ai(slots)
        logger.info(f"Booking request detected. Available slots: {len(slots)}")
    elif not booking_agent_active and any(keyword in message_lower for keyword in booking_keywords):
        logger.info(f"Booking keywords detected, but Booking Agent is TURNED OFF for {client.get('business_name')}.")

    # 6. Generate AI response using client's prompt & knowledge (FEATURE 4: With guardrails & milestone memory)
    ai_reply = ai.generate_reply(
        messages=history,
        system_prompt=client.get("system_prompt"),
        business_knowledge=client.get("business_knowledge"),
        available_slots=available_slots_text,
        booking_enabled=booking_agent_active,
        milestone_memory=milestone_memory
    )

    # 7. Send WhatsApp reply back to customer (Skip if in local simulation mode)
    if not is_simulation:
        await whatsapp.send_whatsapp_text(
            to_phone=customer_phone,
            text=ai_reply,
            phone_number_id=phone_number_id,
            access_token=client.get("access_token")
        )

    # 8. Save AI reply to conversation memory
    await db.save_message(conv_id, "ai", ai_reply)

    # 9. Extract structured lead qualification & score using client-specific schema AND classification rules
    updated_history = history + [{"role": "assistant", "content": ai_reply}]
    lead_data = ai.extract_lead_data(
        messages=updated_history,
        extraction_schema=client.get("extraction_schema"),
        classification_rules=client.get("classification_rules")
    )

    # Add customer phone to lead data for notifications
    lead_data["customer_phone"] = customer_phone

    # 10. Update lead in CRM
    await db.upsert_lead(client_id, conv_id, customer_phone, lead_data)

    # FEATURE 5: Send HOT lead alert to broker's WhatsApp (Skip if in local simulation mode)
    broker_phone = client.get("broker_whatsapp") or client.get("notification_phone")
    if not is_simulation and broker_phone and lead_data.get("classification") == "HOT":
        await notifications.send_hot_lead_alert(
            broker_phone=broker_phone,
            lead_data=lead_data,
            client_config={"phone_number_id": phone_number_id, "access_token": client.get("access_token")}
        )

    # FEATURE 2: Extract and confirm booking if booking agent is ON and customer provided date/time
    booking_extraction_result = {"booked": False}
    if is_booking_request:
        booking_extraction_result = await extract_booking_details(updated_history, client_id, customer_phone, lead_data.get("name", "Customer"))

        # IMMEDIATE STOP RULE: Stop follow-ups immediately when an appointment is booked
        if booking_extraction_result.get("booked") and customer_phone:
            followups.cancel_pending_followup_for_customer(customer_phone)

        if not is_simulation and booking_extraction_result.get("booked") and broker_phone:
            booking_data = booking_extraction_result.get("booking", {})
            await notifications.send_site_visit_booking_confirmation(
                broker_phone=broker_phone,
                customer_phone=customer_phone,
                booking_details={
                    "date": booking_data.get("date"),
                    "time": booking_data.get("time"),
                    "customer_name": lead_data.get("name", "Customer"),
                    "location": booking_data.get("property_info", "Property visit")
                },
                client_config={"phone_number_id": phone_number_id, "access_token": client.get("access_token")}
            )

    return {
        "client": client.get("business_name"),
        "customer_phone": customer_phone,
        "reply": ai_reply,
        "lead_data": lead_data,
        "booking_data": booking_extraction_result,
        "bot_active": conversation.get("bot_active", True),
        "booking_enabled": booking_agent_active
    }


async def extract_booking_details(messages: list, client_id: str, customer_phone: str, customer_name: str) -> dict:
    """
    FEATURE 2: Extracts booking date/time from conversation and books the slot.
    """
    import re
    from datetime import datetime, timedelta

    # Use AI to extract booking details
    conversation_text = "\n".join([f"{m['role']}: {m['content']}" for m in messages[-5:]])

    extraction_prompt = f"""Analyze this conversation and extract booking details:

{conversation_text}

Extract as JSON:
{{
  "has_booking_details": true/false,
  "date": "YYYY-MM-DD" or null,
  "time": "HH:MM AM/PM" or null,
  "is_reschedule": true/false
}}

Only set has_booking_details to true if the customer provided BOTH a specific date AND time.
Set is_reschedule to true if the customer is asking to change, shift, or reschedule an existing appointment.
"""

    try:
        booking_info = ai.extract_lead_data([{"role": "user", "content": extraction_prompt}])

        if booking_info.get("has_booking_details") and booking_info.get("date") and booking_info.get("time"):
            reschedule_intent = any(w in conversation_text.lower() for w in ["reschedule", "change", "shift", "another time", "different time", "cancel and"])
            is_reschedule = bool(booking_info.get("is_reschedule")) or reschedule_intent

            # Attempt to book or reschedule the slot
            result = await bookings.book_slot(
                client_id=client_id,
                customer_phone=customer_phone,
                customer_name=customer_name,
                date=booking_info["date"],
                time=booking_info["time"],
                reschedule=is_reschedule
            )
            return result
    except Exception as e:
        logger.error(f"Booking extraction error: {e}")

    return {"booked": False}


# =====================================================================
# LOCAL TESTING & SIMULATION ENDPOINTS (Zero-Dependency)
# =====================================================================

class TestMessageRequest(BaseModel):
    client_id: Optional[str] = None
    customer_phone: Optional[str] = None
    sender_phone: Optional[str] = None
    phone_number_id: Optional[str] = "default_arvana_id"
    message: Optional[str] = None
    message_text: Optional[str] = None
    debounce: Optional[bool] = False
    debounce_delay: Optional[float] = None


@app.post("/test-message", summary="Simulate WhatsApp Message (Local Testing)")
async def test_message(req: TestMessageRequest):
    """
    Test endpoint to simulate an incoming WhatsApp message without needing Meta credentials.
    Runs the full AI qualification, memory, and lead scoring pipeline.
    Supports debouncing simulation if req.debounce is True.
    """
    phone = req.customer_phone or req.sender_phone or "919876543210"
    msg_text = req.message_text or req.message or "Hi! I am looking for lead automation for my real estate agency. Budget is around 20k."

    # Immediate stop rule: user reply cancels pending follow-ups
    followups.cancel_pending_followup_for_customer(phone)

    if req.debounce:
        async def _test_debounced_handler(p: str, combined: str, meta: dict):
            return await process_incoming_message(
                phone_number_id=meta.get("phone_number_id"),
                customer_phone=p,
                message_text=combined,
                client_id=meta.get("client_id"),
                is_simulation=True
            )

        await debouncer.add_message(
            key=phone,
            message_text=msg_text,
            handler=_test_debounced_handler,
            metadata={"phone_number_id": req.phone_number_id, "client_id": req.client_id},
            delay=req.debounce_delay
        )
        return {
            "status": "buffering",
            "debounced": True,
            "customer_phone": phone,
            "buffered_messages": debouncer.get_buffered_messages(phone)
        }

    result = await process_incoming_message(
        phone_number_id=req.phone_number_id,
        customer_phone=phone,
        message_text=msg_text,
        client_id=req.client_id,
        is_simulation=True
    )
    return {
        "status": "success",
        "simulation": True,
        "ai_response": result.get("reply"),
        "lead_extracted": result.get("lead_data"),
        "booking_data": result.get("booking_data"),
        "result": result
    }


@app.post("/test-message/flush", summary="Manually Flush Debounced Messages for Customer")
async def flush_debounced_test_messages(customer_phone: str = "919876543210"):
    """Manually flushes the debounce buffer for testing without waiting for timer."""
    res = await debouncer.flush(customer_phone)
    return {"status": "flushed", "result": res}


@app.get("/leads", summary="View All CRM Leads")
async def view_leads(client_id: Optional[str] = None):
    """
    Returns all qualified leads captured by the system.
    """
    leads = await db.get_all_leads(client_id)
    return {
        "count": len(leads),
        "leads": leads
    }


class LeadStatusUpdate(BaseModel):
    classification: Optional[str] = None  # "HOT", "WARM", "COLD", "NEW"
    status: Optional[str] = None          # "NEW", "CONTACTED", "WON", "LOST"


@app.patch("/leads/{lead_id}", summary="Update Lead Classification or Status")
async def update_lead_status_endpoint(lead_id: str, req: LeadStatusUpdate):
    """
    Updates a lead's qualification classification or deal status (e.g. WON / LOST).
    """
    updated = await db.update_lead_status(lead_id, classification=req.classification, status=req.status)
    if not updated:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"status": "success", "lead": updated}


@app.get("/leads/followups-due", summary="Get Leads Due for Follow-Up")
async def get_followups_due(client_id: Optional[str] = None, intra_24h: bool = False):
    """
    Returns leads that require follow-up based on inactivity:
    - If intra_24h=True: evaluates 10m, 1h, 5h, 10h, 24h cadence within Meta's free service window.
    - If intra_24h=False: evaluates standard cold lead cadence (>24h, >48h, >7d).
    Enriches each lead with stage, hours inactive, and pre-calculated follow-up recommendation.
    """
    all_leads = await db.get_all_leads(client_id)
    clients_cache = {}
    due_leads = []
    now = datetime.now(timezone.utc)

    for lead in all_leads:
        cid = lead.get("client_id")
        if cid and cid not in clients_cache:
            clients_cache[cid] = await db.get_client_by_id(cid)
        client = clients_cache.get(cid)

        # Inactivity evaluation
        raw_time = lead.get("last_message_at") or lead.get("last_interaction") or lead.get("updated_at")
        last_dt = None
        if raw_time:
            try:
                clean_iso = str(raw_time).replace("Z", "+00:00")
                last_dt = datetime.fromisoformat(clean_iso)
            except Exception:
                pass

        if not last_dt:
            if lead.get("classification") == "COLD":
                last_dt = now - timedelta(hours=25)
            else:
                continue

        stage_info = followups.determine_followup_stage(last_dt, now, intra_24h=intra_24h)
        if stage_info or lead.get("classification") == "COLD":
            if not stage_info:
                stage_info = {
                    "stage": 1,
                    "name": "24h Nudge",
                    "hours_inactive": 24.0,
                    "goal": "Friendly warm check-in asking if they had a chance to review property options"
                }

            due_leads.append({
                **lead,
                "followup_stage": stage_info.get("stage_number", stage_info["stage"]),
                "followup_stage_name": stage_info["name"],
                "hours_inactive": round(stage_info.get("hours_inactive", 0.0), 1),
                "followup_goal": stage_info.get("goal", "Follow-up check-in"),
                "followups_enabled_for_client": followups.is_followups_enabled_for_client(client) if client else True
            })

    return {"due_count": len(due_leads), "leads": due_leads}


@app.post("/leads/{lead_id}/generate-followup", summary="Generate AI Follow-Up Message & 1-Click WhatsApp Link")
async def generate_lead_followup(lead_id: str, intra_24h: bool = False):
    """
    Generates a personalized, stage-aware follow-up draft for a lead with a pre-filled 1-Click wa.me link.
    Supports intra_24h context-aware mode (10m, 1h, 5h, 10h, 24h within Meta's free window).
    """
    lead = await db.get_lead_by_id(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    client = None
    if lead.get("client_id"):
        client = await db.get_client_by_id(lead["client_id"])

    history = []
    if lead.get("conversation_id"):
        history = await db.get_conversation_history(lead["conversation_id"])

    bk = client.get("business_knowledge") if client else {}
    result = followups.generate_followup_message(
        lead=lead,
        conversation_history=history,
        business_knowledge=bk,
        intra_24h=intra_24h
    )
    return {"status": "success", "followup": result}


@app.post("/leads/{lead_id}/cancel-followup", summary="Cancel Pending Follow-up Sequence for Lead")
async def cancel_lead_followup(lead_id: str):
    """
    IMMEDIATE STOP RULE:
    Cancels any active or scheduled follow-up sequence for a lead (e.g. upon human takeover or broker request).
    """
    lead = await db.get_lead_by_id(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    phone = lead.get("customer_phone")
    cancelled = False
    if phone:
        cancelled = followups.cancel_pending_followup_for_customer(phone)
    return {"status": "cancelled", "lead_id": lead_id, "customer_phone": phone, "was_pending": cancelled}


@app.post("/admin/cron/run-followups", summary="Cron Endpoint to Process Cold Lead Follow-Ups")
async def cron_run_followups():
    """
    Batch evaluates cold/inactive leads across all active clients with follow_ups_enabled.
    Generates follow-up drafts for the CRM queue.
    """
    clients = await db.get_all_clients()
    processed_clients = 0
    generated_drafts = []

    for client in clients:
        if not followups.is_followups_enabled_for_client(client):
            continue

        processed_clients += 1
        client_id = client.get("id")
        leads = await db.get_all_leads(client_id)
        for lead in leads:
            if lead.get("classification") == "COLD":
                draft = followups.generate_followup_message(
                    lead,
                    business_knowledge=client.get("business_knowledge")
                )
                generated_drafts.append(draft)

    return {
        "status": "success",
        "active_followup_clients": processed_clients,
        "drafts_generated": len(generated_drafts),
        "drafts": generated_drafts
    }


# =====================================================================
# CONVERSATIONS & CHAT TRANSCRIPT ENDPOINTS
# =====================================================================

@app.get("/conversations", summary="Get Conversations for Client")
async def list_conversations(client_id: str):
    """
    Returns all customer conversations for a specific client with bot pause status.
    """
    convs = await db.get_conversations_by_client(client_id)
    return {"client_id": client_id, "conversations": convs, "count": len(convs)}


@app.get("/conversation/{conversation_id}/messages", summary="Get Conversation Message History")
async def get_conversation_messages(conversation_id: str):
    """
    Returns full message history for a conversation transcript viewer.
    """
    messages = await db.get_messages_by_conversation(conversation_id)
    return {"conversation_id": conversation_id, "messages": messages, "count": len(messages)}


# =====================================================================
# AGENCY ADMIN CONTROL PANEL ENDPOINTS
# =====================================================================

class AgencyAuthRequest(BaseModel):
    password: str


@app.post("/admin/auth/verify", summary="Verify Agency Master Password")
async def verify_agency_password(req: AgencyAuthRequest):
    """
    Protects the Standalone ARVANA Agency Admin panel from unauthorized access.
    Checks against master agency password.
    """
    master_pass = os.getenv("AGENCY_ADMIN_PASSWORD", "arvana_admin_2026")
    if req.password != master_pass:
        raise HTTPException(status_code=401, detail="Invalid agency master password")
    return {
        "authenticated": True,
        "token": "arvana_agency_master_session",
        "message": "Welcome to ARVANA Agency Command Center"
    }


class ClientCreate(BaseModel):
    business_name: str
    phone_number_id: str
    access_token: Optional[str] = None
    waba_id: Optional[str] = None
    broker_whatsapp: Optional[str] = None
    system_prompt: Optional[str] = None
    business_knowledge: Optional[Any] = None
    classification_rules: Optional[str] = None
    booking_enabled: Optional[bool] = True
    follow_ups_enabled: Optional[bool] = False
    instagram_bridge_enabled: Optional[bool] = False
    status: Optional[str] = "ACTIVE"


class ClientUpdate(BaseModel):
    business_name: Optional[str] = None
    phone_number_id: Optional[str] = None
    access_token: Optional[str] = None
    broker_whatsapp: Optional[str] = None
    system_prompt: Optional[str] = None
    business_knowledge: Optional[Any] = None
    classification_rules: Optional[str] = None
    booking_enabled: Optional[bool] = None
    follow_ups_enabled: Optional[bool] = None
    instagram_bridge_enabled: Optional[bool] = None
    status: Optional[str] = None


@app.get("/admin/clients", summary="List All Onboarded Clients (Agency Admin)")
async def admin_list_clients():
    """
    Admin endpoint: Returns all onboarded clients with lead stats and active status.
    """
    clients = await db.get_all_clients()
    all_leads = await db.get_all_leads()

    enriched = []
    for client in clients:
        cid = client.get("id")
        client_leads = [l for l in all_leads if l.get("client_id") == cid]
        hot_leads = [l for l in client_leads if l.get("classification") == "HOT"]
        enriched.append({
            **client,
            "total_leads": len(client_leads),
            "hot_leads": len(hot_leads)
        })
    return {"clients": enriched, "count": len(enriched)}


@app.get("/admin/clients/{client_id}", summary="Get Client Settings (Agency Admin)")
async def admin_get_client(client_id: str):
    client = await db.get_client_by_id(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return {"client": client}


@app.post("/admin/clients", summary="Onboard New Client (Agency Admin)")
async def admin_create_client(req: ClientCreate):
    data = req.model_dump(exclude_none=True)
    bk = data.get("business_knowledge") or {}
    if not isinstance(bk, dict):
        bk = {}
    if "booking_enabled" in data:
        bk["booking_enabled"] = data["booking_enabled"]
    if "follow_ups_enabled" in data:
        bk["follow_ups_enabled"] = data["follow_ups_enabled"]
    if "instagram_bridge_enabled" in data:
        bk["instagram_bridge_enabled"] = data["instagram_bridge_enabled"]
    data["business_knowledge"] = bk

    created = await db.create_client(data)
    return {"status": "success", "client": created}


@app.put("/admin/clients/{client_id}", summary="Update Client Configuration (Agency Admin)")
async def admin_update_client(client_id: str, req: ClientUpdate):
    data = req.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields provided for update")

    # Mirror feature flags into business_knowledge if updated
    client = await db.get_client_by_id(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    bk = data.get("business_knowledge") or client.get("business_knowledge") or {}
    if not isinstance(bk, dict):
        bk = {}
    if "booking_enabled" in data:
        bk["booking_enabled"] = data["booking_enabled"]
    if "follow_ups_enabled" in data:
        bk["follow_ups_enabled"] = data["follow_ups_enabled"]
    if "instagram_bridge_enabled" in data:
        bk["instagram_bridge_enabled"] = data["instagram_bridge_enabled"]
    data["business_knowledge"] = bk

    updated = await db.update_client(client_id, data)
    return {"status": "success", "client": updated}


@app.delete("/admin/clients/{client_id}", summary="Delete Client (Agency Admin)")
async def admin_delete_client(client_id: str):
    """
    Deletes a client profile and frees its allocated resources.
    """
    success = await db.delete_client(client_id)
    if not success:
        raise HTTPException(status_code=404, detail="Client not found or could not be deleted")
    return {"status": "success", "client_id": client_id}


@app.post("/admin/clients/{client_id}/toggle-status", summary="Toggle Client Service Kill-Switch")
async def admin_toggle_client_status(client_id: str):
    client = await db.get_client_by_id(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    current_status = client.get("status", "ACTIVE")
    new_status = "SUSPENDED" if current_status == "ACTIVE" else "ACTIVE"
    updated = await db.update_client(client_id, {"status": new_status})
    return {
        "status": "success",
        "client_id": client_id,
        "business_name": client.get("business_name"),
        "previous_status": current_status,
        "new_status": new_status
    }


@app.post("/admin/clients/{client_id}/toggle-booking", summary="Toggle Booking Agent ON/OFF (Admin)")
@app.post("/clients/{client_id}/toggle-booking", summary="Toggle Booking Agent ON/OFF (Client)")
async def toggle_client_booking(client_id: str):
    """
    Toggles the AI booking agent ON/OFF for a client.
    When OFF, the AI focuses solely on lead qualification without offering site visit scheduling.
    """
    client = await db.get_client_by_id(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    current_enabled = is_booking_enabled_for_client(client)
    new_enabled = not current_enabled

    # Safe persistence in business_knowledge JSONB to prevent column absence errors
    bk = client.get("business_knowledge") or {}
    if not isinstance(bk, dict):
        bk = {}
    bk["booking_enabled"] = new_enabled

    update_payload = {
        "booking_enabled": new_enabled,
        "business_knowledge": bk
    }

    try:
        updated = await db.update_client(client_id, update_payload)
    except Exception:
        updated = await db.update_client(client_id, {"business_knowledge": bk})

    return {
        "status": "success",
        "client_id": client_id,
        "business_name": client.get("business_name"),
        "booking_enabled": new_enabled
    }


@app.post("/admin/clients/{client_id}/toggle-followups", summary="Toggle Cold Lead Follow-Ups Add-on (Admin Upsell)")
async def toggle_client_followups(client_id: str):
    """
    Toggles the Cold Lead Follow-Up Engine ON/OFF for a client.
    ARVANA monetizes this as a high-margin lead reactivation retainer.
    """
    client = await db.get_client_by_id(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    current_enabled = followups.is_followups_enabled_for_client(client)
    new_enabled = not current_enabled

    bk = client.get("business_knowledge") or {}
    if not isinstance(bk, dict):
        bk = {}
    bk["follow_ups_enabled"] = new_enabled

    update_payload = {
        "follow_ups_enabled": new_enabled,
        "business_knowledge": bk
    }

    try:
        updated = await db.update_client(client_id, update_payload)
    except Exception:
        updated = await db.update_client(client_id, {"business_knowledge": bk})

    return {
        "status": "success",
        "client_id": client_id,
        "business_name": client.get("business_name"),
        "follow_ups_enabled": new_enabled
    }


@app.post("/admin/clients/{client_id}/toggle-instagram-bridge", summary="Toggle Instagram-to-WhatsApp Bridge (Admin Upsell)")
async def toggle_client_instagram_bridge(client_id: str):
    """
    Toggles the Instagram-to-WhatsApp Bridge configuration for a client.
    """
    client = await db.get_client_by_id(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    bk = client.get("business_knowledge") or {}
    if not isinstance(bk, dict):
        bk = {}
    current_enabled = bool(bk.get("instagram_bridge_enabled", False))
    new_enabled = not current_enabled
    bk["instagram_bridge_enabled"] = new_enabled

    updated = await db.update_client(client_id, {"business_knowledge": bk})
    return {
        "status": "success",
        "client_id": client_id,
        "business_name": client.get("business_name"),
        "instagram_bridge_enabled": new_enabled
    }


# =====================================================================
# TESTING & SIMULATION ENDPOINTS
# =====================================================================

@app.get("/test-alert-preview", summary="Preview HOT Lead Alert Message")
async def preview_hot_lead_alert():
    """
    Shows you exactly what the broker receives on WhatsApp when a HOT lead comes in.
    No WhatsApp credentials needed!
    """
    sample_lead = {
        "customer_phone": "+91 98765 43210",
        "name": "Rajesh Kumar",
        "budget_range": "₹80 Lakhs - ₹1 Crore",
        "timeline": "Immediate (within 7 days)",
        "classification": "HOT",
        "ai_summary": "Looking for ready-to-move 3BHK in Whitefield. Loan pre-approved from HDFC. Wants to schedule site visit this Saturday at 11 AM."
    }

    alert_text = f"""🔥 *HOT LEAD ALERT* 🔥

Name: {sample_lead['name']}
Phone: {sample_lead['customer_phone']}
Budget: {sample_lead['budget_range']}
Timeline: {sample_lead['timeline']}

Summary:
{sample_lead['ai_summary']}

ACTION REQUIRED: This lead is ready to convert. Call them NOW!"""

    return {
        "simulated_lead": sample_lead,
        "whatsapp_message_preview": alert_text,
        "note": "This is the exact message that gets sent to the broker's WhatsApp in production."
    }


# =====================================================================
# FEATURE 3: LIVE TWO-WAY WHATSAPP CHAT & HUMAN HANDOFF
# =====================================================================

class DirectWhatsAppMessage(BaseModel):
    client_id: str
    customer_phone: str
    message: str
    conversation_id: Optional[str] = None
    auto_pause_bot: Optional[bool] = True


@app.post("/whatsapp/send", summary="Send Direct WhatsApp Message (In-CRM Live Chat)")
async def send_direct_whatsapp_message(req: DirectWhatsAppMessage):
    """
    Enables brokers to reply directly to leads from within the CRM live chat drawer.
    Dispatches outbound message via Meta WhatsApp Cloud API (or mock mode),
    records the message in conversation history with sender='agent',
    and automatically pauses the AI bot so human and bot don't collide.
    """
    client = await db.get_client_by_id(req.client_id)
    phone_id = client.get("phone_number_id") if client else None
    token = client.get("access_token") if client else None

    # Resolve or create conversation
    conv_id = req.conversation_id
    if not conv_id:
        conv = await db.get_or_create_conversation(req.client_id, req.customer_phone)
        conv_id = conv.get("id")

    # Send outbound WhatsApp
    delivery = await whatsapp.send_whatsapp_text(
        to_phone=req.customer_phone,
        text=req.message,
        phone_number_id=phone_id,
        access_token=token
    )

    # Save to message history as human agent
    saved_msg = await db.save_message(
        conversation_id=conv_id,
        sender="agent",
        content=req.message
    )

    # Automatically pause the bot if requested for seamless human takeover
    bot_status = "active"
    if req.auto_pause_bot and conv_id:
        await db.pause_bot_for_conversation(conv_id)
        bot_status = "paused_for_human_takeover"

    # IMMEDIATE STOP RULE: Cancel any scheduled follow-up sequence when human intervenes
    if req.customer_phone:
        followups.cancel_pending_followup_for_customer(req.customer_phone)

    return {
        "status": "success",
        "delivery": delivery,
        "message": saved_msg,
        "conversation_id": conv_id,
        "bot_status": bot_status
    }


@app.post("/conversation/{conversation_id}/pause", summary="Pause Bot (Human Takeover)")
@app.post("/conversations/{conversation_id}/pause", summary="Pause Bot (Alias)")
async def pause_bot(conversation_id: str):
    """
    FEATURE 3: Pauses the bot for a specific conversation.
    When the broker replies from their phone or CRM, call this endpoint to make the bot go quiet.
    IMMEDIATE STOP RULE: Also immediately halts any automated follow-up sequences.
    """
    conv = await db.get_conversation_by_id(conversation_id)
    if conv and conv.get("customer_phone"):
        followups.cancel_pending_followup_for_customer(conv["customer_phone"])

    result = await db.pause_bot_for_conversation(conversation_id)
    return result


@app.post("/conversation/{conversation_id}/resume", summary="Resume Bot")
@app.post("/conversations/{conversation_id}/resume", summary="Resume Bot (Alias)")
async def resume_bot(conversation_id: str):
    """
    FEATURE 3: Resumes the bot for a specific conversation.
    Bot will start responding again after human handoff is complete.
    """
    result = await db.resume_bot_for_conversation(conversation_id)
    return result


@app.post("/conversation/{conversation_id}/toggle-bot", summary="Toggle Bot Active/Paused")
@app.post("/conversations/{conversation_id}/toggle-bot", summary="Toggle Bot Active/Paused (Alias)")
async def toggle_bot(conversation_id: str):
    """
    Toggles the AI bot on or off for a conversation.
    Allows broker to toggle between AI handling and manual human response.
    IMMEDIATE STOP RULE: When pausing the bot, immediately cancels pending follow-ups.
    """
    conv = await db.get_conversation_by_id(conversation_id)
    current_active = conv.get("bot_active", True) if conv else True
    if current_active:
        await db.pause_bot_for_conversation(conversation_id)
        new_active = False
        if conv and conv.get("customer_phone"):
            followups.cancel_pending_followup_for_customer(conv["customer_phone"])
    else:
        await db.resume_bot_for_conversation(conversation_id)
        new_active = True

    return {
        "status": "success",
        "conversation_id": conversation_id,
        "bot_active": new_active
    }


# =====================================================================
# FEATURE 2: CALENDAR & BOOKING MANAGEMENT ENDPOINTS
# =====================================================================

@app.get("/calendar/availability", summary="Get Available Time Slots")
async def get_availability(
    client_id: str,
    date: Optional[str] = None,
    days_ahead: int = 7
):
    """
    FEATURE 2: Returns available booking slots for a client.
    Used by CRM dashboard to show calendar view.
    """
    slots = await bookings.get_available_slots(client_id, date, days_ahead)
    return {
        "client_id": client_id,
        "slots": slots,
        "count": len(slots)
    }


@app.get("/calendar/bookings", summary="Get All Bookings")
async def get_bookings(
    client_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """
    FEATURE 2: Returns all bookings for CRM calendar view.
    """
    bookings_list = await bookings.get_client_bookings(client_id, start_date, end_date)
    return {
        "client_id": client_id,
        "bookings": bookings_list,
        "count": len(bookings_list)
    }


class BookingRequest(BaseModel):
    client_id: str
    customer_phone: str
    customer_name: str
    date: str  # YYYY-MM-DD
    time: str  # HH:MM AM/PM
    property_info: Optional[str] = None
    reschedule: Optional[bool] = False


@app.post("/calendar/book", summary="Manually Book a Slot")
async def manual_book(req: BookingRequest):
    """
    FEATURE 2: Allows broker to manually book a slot from CRM with anti-spam limits.
    """
    result = await bookings.book_slot(
        client_id=req.client_id,
        customer_phone=req.customer_phone,
        customer_name=req.customer_name,
        date=req.date,
        time=req.time,
        property_info=req.property_info,
        reschedule=bool(req.reschedule)
    )
    return result


@app.delete("/calendar/bookings/{booking_id}", summary="Cancel a Booking")
async def cancel_booking_endpoint(booking_id: str):
    """
    FEATURE 2: Cancels a booking and frees up the slot.
    """
    result = await bookings.cancel_booking(booking_id)
    return result


class AvailabilityUpdate(BaseModel):
    client_id: str
    date: str  # YYYY-MM-DD
    time: str  # HH:MM AM/PM
    status: str  # "AVAILABLE" | "BLOCKED" | "UNAVAILABLE"


@app.post("/calendar/availability/update", summary="Update Broker Availability")
async def update_availability_endpoint(req: AvailabilityUpdate):
    """
    FEATURE 2: Allows broker to update their availability calendar.
    Broker can block times, add custom slots, or mark unavailable.
    """
    result = await bookings.update_availability(
        client_id=req.client_id,
        date=req.date,
        time=req.time,
        status=req.status
    )
    return result


class AddSlotRequest(BaseModel):
    client_id: str
    date: str  # YYYY-MM-DD or DD/MM/YY
    time: Optional[str] = None  # e.g., "01:00 PM - 02:00 PM"
    start_time: Optional[str] = None  # e.g. "01:00 PM"
    end_time: Optional[str] = None    # e.g. "02:00 PM"


@app.post("/calendar/availability/add-slot", summary="Add Custom Broker Availability Slot")
async def add_slot_endpoint(req: AddSlotRequest):
    """
    Allows a client or broker to add custom availability slots (e.g. 2026-11-20 1:00 PM - 2:00 PM).
    """
    date_val = req.date.strip()
    # Normalize DD/MM/YYYY or DD/MM/YY to YYYY-MM-DD
    if "/" in date_val:
        parts = date_val.split("/")
        if len(parts) == 3:
            day, month, year = parts[0], parts[1], parts[2]
            if len(year) == 2:
                year = "20" + year
            date_val = f"{year.zfill(4)}-{month.zfill(2)}-{day.zfill(2)}"

    time_label = req.time
    if not time_label:
        if req.start_time and req.end_time:
            time_label = f"{req.start_time} - {req.end_time}"
        elif req.start_time:
            time_label = req.start_time
        else:
            time_label = "01:00 PM - 02:00 PM"

    result = await bookings.update_availability(
        client_id=req.client_id,
        date=date_val,
        time=time_label,
        status="AVAILABLE"
    )
    return {
        "status": "success",
        "date": date_val,
        "time": time_label,
        "client_id": req.client_id,
        "result": result
    }


# =====================================================================
# STATIC ASSETS & DASHBOARD MOUNTS
# =====================================================================

@app.get("/admin", include_in_schema=False)
async def admin_redirect():
    """Redirects /admin to the Standalone Agency Admin Dashboard."""
    return RedirectResponse(url="/agency-admin/")


_crm_dir = os.path.join(os.path.dirname(__file__), "crm-design-preview")
if os.path.isdir(_crm_dir):
    app.mount("/crm", StaticFiles(directory=_crm_dir, html=True), name="crm")

_admin_dir = os.path.join(os.path.dirname(__file__), "agency-admin")
if os.path.isdir(_admin_dir):
    app.mount("/agency-admin", StaticFiles(directory=_admin_dir, html=True), name="agency-admin")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
