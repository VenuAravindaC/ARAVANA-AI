"""
ARVANA Follow-Up Engine
Handles cold lead reactivation, intra-24h context-aware follow-up cadence
(10m, 1h, 5h, 10h, 24h within Meta's free service window), adaptive questioning,
and immediate cancellation upon user reply or human agent takeover.
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

# Registry of pending follow-up tracking (keyed by customer phone)
_pending_followup_records: Dict[str, dict] = {}


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


def register_pending_followup(customer_phone: str, followup_data: dict) -> None:
    """Registers an active or scheduled follow-up sequence for a customer."""
    clean_phone = _clean_phone_number(customer_phone)
    _pending_followup_records[clean_phone] = followup_data


def cancel_pending_followup_for_customer(customer_phone: str) -> bool:
    """
    IMMEDIATE STOP RULE:
    Cancels any active or scheduled follow-up sequence immediately when:
    1. The customer replies to any message
    2. A human agent takes over or pauses the bot
    3. The customer completes a booking/demo
    """
    clean_phone = _clean_phone_number(customer_phone)
    if clean_phone in _pending_followup_records:
        del _pending_followup_records[clean_phone]
        logger.info(f"Follow-up sequence cancelled immediately for {clean_phone} (immediate stop triggered).")
        return True
    return False


def get_pending_followup_for_customer(customer_phone: str) -> Optional[dict]:
    """Retrieves active follow-up state for a customer."""
    clean_phone = _clean_phone_number(customer_phone)
    return _pending_followup_records.get(clean_phone)


def clear_all_followup_records() -> None:
    """Cleans up in-memory registry (useful for test isolation)."""
    _pending_followup_records.clear()


def determine_intra_24h_followup_stage(
    last_interaction: datetime,
    current_time: Optional[datetime] = None
) -> Optional[Dict[str, Any]]:
    """
    Evaluates customer inactivity within Meta's free 24-hour service window.
    Cadence:
    - 10m: >= 10 minutes (Micro-Nudge)
    - 1h:  >= 60 minutes (1-Hour Check-in)
    - 5h:  >= 300 minutes (5-Hour Context Follow-up)
    - 10h: >= 600 minutes (10-Hour Mid-day Touchpoint)
    - 24h: >= 1440 minutes (24-Hour Window Closeout)
    """
    now = current_time or datetime.now(timezone.utc)
    if last_interaction.tzinfo is None:
        last_interaction = last_interaction.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    minutes_inactive = (now - last_interaction).total_seconds() / 60.0
    if minutes_inactive < 10:
        return None

    if minutes_inactive >= 1440:
        return {
            "stage": "24h",
            "stage_number": 5,
            "name": "24-Hour Window Closeout",
            "minutes_inactive": minutes_inactive,
            "hours_inactive": round(minutes_inactive / 60.0, 1),
            "goal": "24h service window closeout and priority re-engagement"
        }
    elif minutes_inactive >= 600:
        return {
            "stage": "10h",
            "stage_number": 4,
            "name": "10-Hour Mid-day Touchpoint",
            "minutes_inactive": minutes_inactive,
            "hours_inactive": round(minutes_inactive / 60.0, 1),
            "goal": "Mid-day follow-up to reconnect before evening"
        }
    elif minutes_inactive >= 300:
        return {
            "stage": "5h",
            "stage_number": 3,
            "name": "5-Hour Context Follow-up",
            "minutes_inactive": minutes_inactive,
            "hours_inactive": round(minutes_inactive / 60.0, 1),
            "goal": "Contextual check-in addressing remaining inquiry points"
        }
    elif minutes_inactive >= 60:
        return {
            "stage": "1h",
            "stage_number": 2,
            "name": "1-Hour Check-in",
            "minutes_inactive": minutes_inactive,
            "hours_inactive": round(minutes_inactive / 60.0, 1),
            "goal": "Gentle 1-hour follow-up while lead is still warm"
        }
    else:
        return {
            "stage": "10m",
            "stage_number": 1,
            "name": "10-Minute Micro-Nudge",
            "minutes_inactive": minutes_inactive,
            "hours_inactive": round(minutes_inactive / 60.0, 1),
            "goal": "Quick micro-nudge right after initial hesitation"
        }


def determine_followup_stage(
    last_interaction: datetime,
    current_time: Optional[datetime] = None,
    intra_24h: bool = False
) -> Optional[Dict[str, Any]]:
    """
    Evaluates customer inactivity and determines which follow-up cadence stage applies:
    - If intra_24h is True: delegates to determine_intra_24h_followup_stage (10m, 1h, 5h, 10h, 24h).
    - If intra_24h is False (default): preserves standard daily cold lead cadence:
      * Stage 1: > 24 hours (24h Nudge - friendly check-in)
      * Stage 2: > 48 hours (48h Value Hook - inventory / price update)
      * Stage 3: > 168 hours (Day 7 Soft Close - gentle closeout)
      * Less than 24h: None (not due yet)
    """
    if intra_24h:
        return determine_intra_24h_followup_stage(last_interaction, current_time)

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


def evaluate_lead_qualification_status(lead: dict) -> Dict[str, Any]:
    """
    Evaluates lead qualification status and determines what is missing.
    - If Qualification is Pending: identifies the next missing qualifying question.
    - If Qualified but No Demo/Visit Booked: identifies readiness for demo/visit nudge.
    - If Booked: marks booking as completed.
    """
    requirements = lead.get("specific_requirements") or lead.get("service") or lead.get("inquiry_type")
    budget = lead.get("budget") or lead.get("budget_range")
    timeline = lead.get("timeline")
    location = lead.get("location") or lead.get("preferred_location")

    # Booking status check
    is_booked = (
        bool(lead.get("booking_status") in ["CONFIRMED", "BOOKED"])
        or bool(lead.get("booked") is True)
        or bool(lead.get("site_visit_booked") is True)
    )

    # Human takeover check
    bot_active = lead.get("bot_active", True)

    missing_fields = []
    if not requirements or requirements in ["General Inquiry", "your inquiry"]:
        missing_fields.append("requirements")
    if not budget or "Pending" in str(budget):
        missing_fields.append("budget")
    if not timeline or timeline in ["Exploring"]:
        missing_fields.append("timeline")

    classification = str(lead.get("classification") or "NEW").upper()
    is_qualified = (len(missing_fields) == 0) and (
        classification in ["HOT", "WARM"] or (bool(requirements) and bool(budget))
    )

    next_missing = missing_fields[0] if missing_fields else None

    return {
        "is_qualified": is_qualified,
        "is_booked": is_booked,
        "bot_active": bot_active,
        "missing_fields": missing_fields,
        "next_missing_field": next_missing,
        "requirements": requirements,
        "budget": budget,
        "timeline": timeline,
        "location": location
    }


def _clean_phone_number(phone: str) -> str:
    """Strips spaces, plus signs, hyphens, and brackets from phone number."""
    if not phone:
        return ""
    return "".join(c for c in str(phone) if c.isdigit())


def generate_followup_message(
    lead: dict,
    conversation_history: Optional[List[dict]] = None,
    business_knowledge: Optional[dict] = None,
    intra_24h: bool = False
) -> Dict[str, Any]:
    """
    Generates a personalized, high-converting follow-up message tailored to the lead's
    extracted criteria, requirements, and inactivity stage.

    Includes Context-Aware rules:
    1. Human Takeover Rule: If bot_active=False, follow-up is suppressed immediately.
    2. Booking Completed Rule: If lead already booked, follow-up is suppressed immediately.
    3. Qualification Pending: Asks the next missing qualifying question.
    4. Qualified but No Demo/Visit: Pivots directly to demo call or site visit nudge.
    """
    customer_phone = lead.get("customer_phone") or ""
    customer_name = lead.get("name") or "there"

    # Rule 1: Check human takeover
    if lead.get("bot_active") is False:
        logger.info(f"Follow-up suppressed for {customer_phone}: human agent is handling this conversation.")
        return {
            "lead_id": lead.get("id"),
            "customer_phone": customer_phone,
            "status": "stopped",
            "reason": "human_takeover",
            "message": None,
            "whatsapp_url": ""
        }

    # Rule 2: Evaluate qualification & booking status
    qual_eval = evaluate_lead_qualification_status(lead)
    if qual_eval["is_booked"]:
        logger.info(f"Follow-up suppressed for {customer_phone}: lead has already booked an appointment.")
        return {
            "lead_id": lead.get("id"),
            "customer_phone": customer_phone,
            "status": "stopped",
            "reason": "already_booked",
            "message": None,
            "whatsapp_url": ""
        }

    requirements = qual_eval["requirements"] or "your inquiry"
    budget = qual_eval["budget"]

    # Determine inactivity timestamp
    raw_time = lead.get("last_message_at") or lead.get("last_interaction") or lead.get("updated_at")
    if raw_time:
        if isinstance(raw_time, str):
            try:
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

    stage_info = determine_followup_stage(last_time, intra_24h=intra_24h)
    if not stage_info:
        # Default fallback stage
        stage_info = {
            "stage": 1,
            "name": "24h Nudge",
            "hours_inactive": 24.0,
            "goal": "Friendly warm check-in"
        }

    stage_val = stage_info["stage"]
    generated_text = ""

    # Rule 3 & 4: Context-Aware Message Adaptation
    is_qualified = qual_eval["is_qualified"]
    next_missing = qual_eval["next_missing_field"]

    if client_configured:
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(
                api_key=GEMINI_API_KEY,
                http_options=types.HttpOptions(timeout=10000)
            )

            if not is_qualified and next_missing:
                # Qualification is pending -> Ask next missing qualifying question
                prompt = (
                    f"You are a friendly customer advisor writing a 1-sentence WhatsApp follow-up.\n"
                    f"Lead Name: {customer_name}\n"
                    f"Known Details: Requirements={requirements}, Budget={budget or 'Unknown'}\n"
                    f"Missing Info Needed: {next_missing}\n"
                    "Goal: Pick up where the customer stopped and ask the next missing qualifying question.\n"
                    "Rules: 1 friendly sentence, easy to answer, not pushy.\n"
                    "Output ONLY the text."
                )
            elif is_qualified:
                # Qualified but no demo/visit booked -> Pivot to demo or visit nudge
                prompt = (
                    f"You are a top advisor writing a 1-sentence WhatsApp follow-up.\n"
                    f"Lead Name: {customer_name}\n"
                    f"Requirements: {requirements}\n"
                    "Goal: Pivot directly to inviting the customer to book a demo slot or site visit.\n"
                    "Rules: 1 friendly sentence offering available times.\n"
                    "Output ONLY the text."
                )
            else:
                prompt = (
                    f"You are a top advisor writing a warm 1-2 sentence WhatsApp follow-up.\n"
                    f"Lead Name: {customer_name}\n"
                    f"Requirements: {requirements}\n"
                    f"Stage Goal: {stage_info.get('goal', 'Warm check-in')}\n"
                    "Rules: Maximum 2 sentences. Friendly, respectful, not pushy.\n"
                    "Output ONLY the text."
                )

            response = client.models.generate_content(
                model="gemini-3.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.7)
            )
            if response.text and response.text.strip():
                generated_text = response.text.strip().strip('"')
        except Exception as e:
            logger.warning(f"Gemini follow-up generation failed, using context-aware template: {e}")

    # Fallback context-aware templates
    if not generated_text:
        if not is_qualified and next_missing:
            if next_missing == "timeline":
                generated_text = f"Quick question before I put together the options for you, {customer_name} — what timeframe were you looking to move in?"
            elif next_missing == "budget":
                generated_text = f"Quick question, {customer_name} — what budget range did you have in mind so I can filter the best units for you?"
            else:
                generated_text = f"Hi {customer_name}! Quick question before I prepare the details — what type of property or service are you looking for?"
        elif is_qualified:
            generated_text = f"Quick question {customer_name}, did you have a chance to grab a site visit or demo slot yet, or would you like me to send over a few convenient times?"
        else:
            # Stage-based templates
            if stage_val == 1 or stage_val == "10m" or stage_val == "1h":
                generated_text = (
                    f"Hi {customer_name}! Just following up to see if you had a chance to review the {requirements} details we discussed. "
                    "Would you like me to share a few curated options?"
                )
            elif stage_val == 2 or stage_val == "5h" or stage_val == "10h":
                generated_text = (
                    f"Hi {customer_name}, a couple of verified options matching your interest in {requirements} just became available. "
                    "Shall I send over the pricing and floor plans?"
                )
            else:
                generated_text = (
                    f"Hi {customer_name}, wanted to quickly check in—should I keep your search for {requirements} active, "
                    "or would you prefer we pause updates for now?"
                )

    clean_phone = _clean_phone_number(customer_phone)
    encoded_text = urllib.parse.quote(generated_text)
    whatsapp_url = f"https://wa.me/{clean_phone}?text={encoded_text}" if clean_phone else ""

    result = {
        "status": "ready",
        "lead_id": lead.get("id"),
        "customer_name": customer_name,
        "customer_phone": customer_phone,
        "stage": stage_info.get("stage_number", stage_info["stage"]),
        "stage_name": stage_info["name"],
        "hours_inactive": round(stage_info.get("hours_inactive", 0.0), 1),
        "is_qualified": is_qualified,
        "message": generated_text,
        "whatsapp_url": whatsapp_url
    }

    # Register in pending tracker
    if clean_phone:
        register_pending_followup(clean_phone, result)

    return result
