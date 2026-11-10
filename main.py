"""
ARVANA Multi-Tenant AI Lead Management Backend
Built with FastAPI, Meta WhatsApp Cloud API, Google Gemini 1.5 Flash, and Supabase.
"""

import os
import logging
from typing import Optional
from fastapi import FastAPI, Request, Query, Response, HTTPException, status
from fastapi.responses import PlainTextResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from lib import whatsapp, ai, db

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
                    await process_incoming_message(phone_number_id, customer_phone, message_text)

    # Meta expects instant 200 OK to acknowledge receipt
    return JSONResponse({"status": "received"}, status_code=200)


# =====================================================================
# CORE LEAD PROCESSING PIPELINE
# =====================================================================

async def process_incoming_message(phone_number_id: str, customer_phone: str, message_text: str) -> dict:
    """
    Central processing engine:
    1. Looks up client configuration (multi-tenancy)
    2. Checks active status (kill switch)
    3. Loads conversation memory
    4. Generates contextual AI response with guardrails
    5. Sends WhatsApp reply
    6. Extracts structured lead criteria and saves to CRM
    """
    # 1. Fetch client config
    client = await db.get_client_by_phone_id(phone_number_id)
    client_id = client["id"]

    # 2. Check client status (Kill Switch)
    if client.get("status") == "SUSPENDED":
        logger.warning(f"Client {client.get('business_name')} is SUSPENDED. Message ignored.")
        return {"status": "suspended"}

    # 3. Get or create conversation
    conversation = await db.get_or_create_conversation(client_id, customer_phone)
    conv_id = conversation["id"]

    # 4. Save incoming customer message
    await db.save_message(conv_id, "customer", message_text)

    # 5. Load recent conversation memory
    history = await db.get_conversation_history(conv_id, limit=10)

    # 6. Generate AI response using client's prompt & knowledge
    ai_reply = ai.generate_reply(
        messages=history,
        system_prompt=client.get("system_prompt"),
        business_knowledge=client.get("business_knowledge")
    )

    # 7. Send WhatsApp reply back to customer
    await whatsapp.send_whatsapp_text(
        to_phone=customer_phone,
        text=ai_reply,
        phone_number_id=phone_number_id,
        access_token=client.get("access_token")
    )

    # 8. Save AI reply to conversation memory
    await db.save_message(conv_id, "ai", ai_reply)

    # 9. Extract structured lead qualification & score using client-specific schema
    updated_history = history + [{"role": "assistant", "content": ai_reply}]
    lead_data = ai.extract_lead_data(
        messages=updated_history,
        extraction_schema=client.get("extraction_schema")
    )

    # 10. Update lead in CRM
    await db.upsert_lead(client_id, conv_id, customer_phone, lead_data)

    return {
        "client": client.get("business_name"),
        "customer_phone": customer_phone,
        "reply": ai_reply,
        "lead_data": lead_data
    }


# =====================================================================
# LOCAL TESTING & SIMULATION ENDPOINTS (Zero-Dependency)
# =====================================================================

class TestMessageRequest(BaseModel):
    customer_phone: str = "919876543210"
    message: str = "Hi! I am looking for lead automation for my real estate agency. Budget is around 20k."
    phone_number_id: Optional[str] = "default_arvana_id"


@app.post("/test-message", summary="Simulate WhatsApp Message (Local Testing)")
async def test_message(req: TestMessageRequest):
    """
    Test endpoint to simulate an incoming WhatsApp message without needing Meta credentials.
    Runs the full AI qualification, memory, and lead scoring pipeline.
    """
    result = await process_incoming_message(
        phone_number_id=req.phone_number_id,
        customer_phone=req.customer_phone,
        message_text=req.message
    )
    return {
        "status": "success",
        "simulation": True,
        "result": result
    }


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
