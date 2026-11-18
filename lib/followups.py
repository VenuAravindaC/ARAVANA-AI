"""
ARVANA Follow-Up Engine
Handles cold lead reactivation, inactivity tracking (24h / 48h / 7d),
and generates high-converting 1-Click WhatsApp re-engagement drafts.
"""

import os
import json
import logging
import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List, Any
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("arvana.followups")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Check Gemini availability
client_configured = False
if GEMINI_API_KEY and GEMINI_API_KEY != "your_gemini_api_key_here":
    try:
        from google import genai
        from google.genai import types
        client_configured = True
    except Exception as e:
        logger.warning(f"Followups engine: google-genai unavailable: {e}")


def is_followups_enabled_for_client(client: dict) -> bool:
    """
    Checks whether the automated Cold Lead Follow-Up Engine is enabled for this client.
    Agency upsell feature: toggled exclusively by ARVANA admin.
    """
    if not client:
        return False
    if "follow_ups_enabled" in client and client["follow_ups_enabled"] is not None:
        return bool(client["follow_ups_enabled"])
    bk = client.get("business_knowledge") or {}
    if isinstance(bk, dict) and "follow_ups_enabled" in bk:
        return bool(bk["follow_ups_enabled"])
    return False


def determine_followup_stage(
    last_interaction: datetime,
    current_time: Optional[datetime] = None
) -> Optional[Dict[str, Any]]:
    """
    Evaluates customer inactivity and determines which follow-up cadence stage applies:
    - Stage 1: > 24 hours (24h Nudge - friendly check-in)
    - Stage 2: > 48 hours (48h Value Hook - inventory / price update)
    - Stage 3: > 168 hours (Day 7 Soft Close - gentle closeout)
    - Less than 24h: None (not due yet)
    """
    now = current_time or datetime.now(timezone.utc)
    if last_interaction.tzinfo is None:
        last_interaction = last_interaction.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    hours_inactive = (now - last_interaction).total_seconds() / 3600.0

    if hours_inactive < 24:
        return None

    if hours_inactive >= 168:
        return {
            "stage": 3,
            "name": "Day 7 Soft Close",
            "hours_inactive": hours_inactive,
            "goal": "Gentle closeout asking whether to keep their search active or pause updates"
        }
    elif hours_inactive >= 48:
        return {
            "stage": 2,
            "name": "48h Value Hook",
            "hours_inactive": hours_inactive,
            "goal": "Share a high-value update, new inventory opening, or price adjustment"
        }
    else:
        return {
            "stage": 1,
            "name": "24h Nudge",
            "hours_inactive": hours_inactive,
            "goal": "Friendly warm check-in asking if they had a chance to review property options"
        }


def _clean_phone_number(phone: str) -> str:
    """Strips spaces, plus signs, hyphens, and brackets from phone number."""
    if not phone:
        return ""
    return "".join(c for c in str(phone) if c.isdigit())


def generate_followup_message(
    lead: dict,
    conversation_history: Optional[List[dict]] = None,
    business_knowledge: Optional[dict] = None
) -> Dict[str, Any]:
    """
    Generates a personalized, high-converting follow-up message tailored to the lead's
    extracted criteria, requirements, and inactivity stage.
    Returns the message text and a pre-filled 1-Click WhatsApp link.
    """
    customer_name = lead.get("name") or "there"
    requirements = lead.get("specific_requirements") or lead.get("inquiry_type") or "your inquiry"
    budget = lead.get("budget")

    # Determine inactivity timestamp
    raw_time = lead.get("last_message_at") or lead.get("last_interaction") or lead.get("updated_at")
    if raw_time:
        if isinstance(raw_time, str):
            try:
                # Support ISO formats with or without Z
                clean_iso = raw_time.replace("Z", "+00:00")
                last_time = datetime.fromisoformat(clean_iso)
            except Exception:
                last_time = datetime.now(timezone.utc) - timedelta(hours=25)
        elif isinstance(raw_time, datetime):
            last_time = raw_time
        else:
            last_time = datetime.now(timezone.utc) - timedelta(hours=25)
    else:
        last_time = datetime.now(timezone.utc) - timedelta(hours=25)

    stage_info = determine_followup_stage(last_time)
    if not stage_info:
        # Default to stage 1 if invoked manually
        stage_info = {
            "stage": 1,
            "name": "24h Nudge",
            "hours_inactive": 24.0,
            "goal": "Friendly warm check-in"
        }

    stage_num = stage_info["stage"]
    generated_text = ""

    # Attempt AI generation if Gemini is configured
    if client_configured:
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(
                api_key=GEMINI_API_KEY,
                http_options=types.HttpOptions(timeout=10000)
            )

            prompt = (
                f"You are a top real estate advisor writing a warm, natural 1-2 sentence WhatsApp follow-up.\n"
                f"Lead Name: {customer_name}\n"
                f"Requirements: {requirements}\n"
                f"Budget: {budget or 'Not specified'}\n"
                f"Follow-up Goal (Stage {stage_num}): {stage_info['goal']}\n"
                "Rules:\n"
                "- Maximum 2 sentences.\n"
                "- Friendly, respectful, not pushy.\n"
                "- Do NOT invent false discounts or properties.\n"
                "- End with a short, easy question to prompt a reply.\n"
                "Output ONLY the message text."
            )

            response = client.models.generate_content(
                model="gemini-3.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.7)
            )
            if response.text and response.text.strip():
                generated_text = response.text.strip().strip('"')
        except Exception as e:
            logger.warning(f"Gemini follow-up generation failed, using high-trust template: {e}")

    # Fallback to high-converting tailored templates if AI generation didn't run
    if not generated_text:
        if stage_num == 1:
            generated_text = (
                f"Hi {customer_name}! Just following up to see if you had a chance to review the {requirements} details we discussed. "
                "Would you like me to share a few curated options?"
            )
        elif stage_num == 2:
            generated_text = (
                f"Hi {customer_name}, a couple of verified options matching your interest in {requirements} just became available. "
                "Shall I send over the pricing and floor plans?"
            )
        else: # Stage 3
            generated_text = (
                f"Hi {customer_name}, wanted to quickly check in—should I keep your search for {requirements} active, "
                "or would you prefer we pause updates for now?"
            )

    clean_phone = _clean_phone_number(lead.get("customer_phone") or "")
    encoded_text = urllib.parse.quote(generated_text)
    whatsapp_url = f"https://wa.me/{clean_phone}?text={encoded_text}" if clean_phone else ""

    return {
        "lead_id": lead.get("id"),
        "customer_name": customer_name,
        "customer_phone": lead.get("customer_phone"),
        "stage": stage_info["stage"],
        "stage_name": stage_info["name"],
        "hours_inactive": round(stage_info["hours_inactive"], 1),
        "message": generated_text,
        "whatsapp_url": whatsapp_url
    }
