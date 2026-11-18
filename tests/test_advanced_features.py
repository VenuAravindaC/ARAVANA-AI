import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient, ASGITransport

from main import app
from lib.debouncer import MessageDebouncer
from lib import db, ai, followups


@pytest.fixture(autouse=True)
def setup_storage(monkeypatch):
    """Clean storage and follow-up tracking for test isolation."""
    monkeypatch.setattr("lib.db.supabase_client", None)
    monkeypatch.setattr("lib.ai.client_configured", False)
    db._mock_clients.clear()
    db._mock_conversations.clear()
    db._mock_messages.clear()
    db._mock_leads.clear()
    followups.clear_all_followup_records()
    yield
    db._mock_clients.clear()
    db._mock_conversations.clear()
    db._mock_messages.clear()
    db._mock_leads.clear()
    followups.clear_all_followup_records()


# =====================================================================
# 1. MESSAGE DEBOUNCER & BUFFERING TESTS
# =====================================================================

@pytest.mark.asyncio
async def test_message_debouncer_accumulation_and_flush():
    """Verify rapid-fire fragmented messages buffer and combine into a single cohesive message."""
    debouncer = MessageDebouncer(default_delay=10.0)
    received_calls = []

    async def mock_handler(phone: str, text: str, meta: dict):
        received_calls.append({"phone": phone, "text": text, "meta": meta})

    phone = "919988776655"
    # Rapid-fire messages within debounce window
    await debouncer.add_message(phone, "Hi", mock_handler, {"meta_key": "val1"})
    await debouncer.add_message(phone, "Looking for 3BHK", mock_handler, {"meta_key": "val2"})
    await debouncer.add_message(phone, "in Whitefield under 1.2 Cr", mock_handler, {"meta_key": "val3"})

    assert debouncer.has_pending(phone) is True
    assert debouncer.get_buffered_messages(phone) == ["Hi", "Looking for 3BHK", "in Whitefield under 1.2 Cr"]

    # Manual or timer flush
    res = await debouncer.flush(phone)
    assert debouncer.has_pending(phone) is False
    assert len(received_calls) == 1
    assert received_calls[0]["phone"] == phone
    assert received_calls[0]["text"] == "Hi\nLooking for 3BHK\nin Whitefield under 1.2 Cr"
    assert received_calls[0]["meta"] == {"meta_key": "val3"}


@pytest.mark.asyncio
async def test_message_debouncer_cancellation():
    """Verify debouncer cancel removes pending tasks and buffers cleanly."""
    debouncer = MessageDebouncer(default_delay=10.0)
    phone = "919988776644"

    async def mock_handler(phone: str, text: str, meta: dict):
        pass

    await debouncer.add_message(phone, "First part", mock_handler)
    assert debouncer.has_pending(phone) is True

    debouncer.cancel(phone)
    assert debouncer.has_pending(phone) is False
    assert debouncer.get_buffered_messages(phone) == []

    # Flushing an empty or cancelled buffer returns None
    result = await debouncer.flush(phone)
    assert result is None


# =====================================================================
# 2. FULL HISTORY CONTEXT & MILESTONE MEMORY TESTS
# =====================================================================

@pytest.mark.asyncio
async def test_milestone_memory_persistence_and_formatting():
    """Verify milestone memory retains extracted lead profile across turns without amnesia."""
    client_id = "test-milestone-client"
    customer_phone = "919876543210"

    conv = await db.get_or_create_conversation(client_id, customer_phone)
    conv_id = conv["id"]

    # Update milestone facts
    milestones = {
        "name": "Ananya Sharma",
        "requirements": "Luxury 4BHK Penthouse",
        "budget": "₹3.5 Crores",
        "location": "Indiranagar, Bangalore",
        "timeline": "Immediate (within 15 days)",
        "pain_points": "Needs 2 covered car parking slots",
        "classification": "HOT"
    }
    updated = await db.update_conversation_milestones(conv_id, milestones)
    assert updated["name"] == "Ananya Sharma"
    assert updated["budget"] == "₹3.5 Crores"

    # Retrieve milestones
    fetched = await db.get_conversation_milestones(conv_id)
    assert fetched["requirements"] == "Luxury 4BHK Penthouse"
    assert fetched["location"] == "Indiranagar, Bangalore"

    # Format into AI milestone context block
    formatted_context = ai.format_milestone_memory(fetched)
    assert "ESTABLISHED CONVERSATION MILESTONES & ACTIVE LEAD PROFILE" in formatted_context
    assert "• Name: Ananya Sharma" in formatted_context
    assert "• Requirement/Service: Luxury 4BHK Penthouse" in formatted_context
    assert "• Budget: ₹3.5 Crores" in formatted_context
    assert "• Location/Area: Indiranagar, Bangalore" in formatted_context
    assert "• Timeline: Immediate (within 15 days)" in formatted_context
    assert "• Key Pain Points / Preferences: Needs 2 covered car parking slots" in formatted_context

    # Verify injected into system prompt
    prompt = ai.build_system_prompt(
        system_prompt="You are a luxury real estate advisor.",
        milestone_memory=fetched
    )
    assert "ESTABLISHED CONVERSATION MILESTONES & ACTIVE LEAD PROFILE" in prompt
    assert "Ananya Sharma" in prompt
    assert "Indiranagar, Bangalore" in prompt


# =====================================================================
# 3. 'FEEL HEARD' SUMMARY CONFIRMATION RULE TESTS
# =====================================================================

def test_feel_heard_summary_confirmation_directive():
    """Verify system prompt includes 'Feel Heard' summary confirmation rule before booking."""
    prompt = ai.build_system_prompt(system_prompt="You are a client advisor.")
    assert "FEEL HEARD" in prompt
    assert "Just to make sure I've noted down everything accurately:" in prompt
    assert "• Requirement:" in prompt
    assert "• Budget:" in prompt
    assert "• Location:" in prompt
    assert "• Timeline:" in prompt
    assert "Does this capture what you're looking for?" in prompt


# =====================================================================
# 4. INTRA-24H CONTEXT-AWARE FOLLOW-UP CADENCE TESTS
# =====================================================================

def test_determine_intra_24h_followup_stages():
    """Verify intra-24h stage cadence (10m, 1h, 5h, 10h, 24h within Meta window)."""
    now = datetime.now(timezone.utc)

    # Inactive 5 minutes: Not due yet (<10 min)
    t5 = now - timedelta(minutes=5)
    assert followups.determine_intra_24h_followup_stage(t5, now) is None

    # Inactive 15 minutes: Stage 1 (10m Micro-Nudge)
    t15 = now - timedelta(minutes=15)
    stg1 = followups.determine_intra_24h_followup_stage(t15, now)
    assert stg1 is not None
    assert stg1["stage"] == "10m"
    assert stg1["stage_number"] == 1

    # Inactive 75 minutes: Stage 2 (1h Check-in)
    t75 = now - timedelta(minutes=75)
    stg2 = followups.determine_intra_24h_followup_stage(t75, now)
    assert stg2 is not None
    assert stg2["stage"] == "1h"
    assert stg2["stage_number"] == 2

    # Inactive 320 minutes (5.3h): Stage 3 (5h Context Follow-up)
    t320 = now - timedelta(minutes=320)
    stg3 = followups.determine_intra_24h_followup_stage(t320, now)
    assert stg3 is not None
    assert stg3["stage"] == "5h"
    assert stg3["stage_number"] == 3

    # Inactive 650 minutes (10.8h): Stage 4 (10h Mid-day Touchpoint)
    t650 = now - timedelta(minutes=650)
    stg4 = followups.determine_intra_24h_followup_stage(t650, now)
    assert stg4 is not None
    assert stg4["stage"] == "10h"
    assert stg4["stage_number"] == 4

    # Inactive 1500 minutes (25h): Stage 5 (24h Window Closeout)
    t1500 = now - timedelta(minutes=1500)
    stg5 = followups.determine_intra_24h_followup_stage(t1500, now)
    assert stg5 is not None
    assert stg5["stage"] == "24h"
    assert stg5["stage_number"] == 5


def test_context_aware_followup_qualification_pending():
    """Verify follow-up asks the next missing qualifying question if qualification is pending."""
    lead = {
        "id": "lead-pending-1",
        "customer_phone": "919876543210",
        "name": "Kavita",
        "specific_requirements": "3BHK Apartment",
        "budget": "80L - 1 Cr",
        "timeline": None,  # Timeline is missing!
        "classification": "NEW",
        "bot_active": True,
        "booked": False,
        "last_interaction": (datetime.now(timezone.utc) - timedelta(minutes=45)).isoformat()
    }

    eval_res = followups.evaluate_lead_qualification_status(lead)
    assert eval_res["is_qualified"] is False
    assert eval_res["next_missing_field"] == "timeline"

    followup = followups.generate_followup_message(lead, intra_24h=True)
    assert followup["status"] == "ready"
    assert "timeframe" in followup["message"].lower() or "when" in followup["message"].lower() or "timeline" in followup["message"].lower()


def test_context_aware_followup_qualified_pivot_to_booking():
    """Verify follow-up pivots directly to demo/visit nudge if lead is qualified but no booking."""
    lead = {
        "id": "lead-qualified-1",
        "customer_phone": "919876543210",
        "name": "Vikram",
        "specific_requirements": "Villa in Sarjapur",
        "budget": "2.5 Cr",
        "timeline": "Next month",
        "classification": "HOT",
        "bot_active": True,
        "booked": False,
        "last_interaction": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    }

    eval_res = followups.evaluate_lead_qualification_status(lead)
    assert eval_res["is_qualified"] is True
    assert eval_res["is_booked"] is False

    followup = followups.generate_followup_message(lead, intra_24h=True)
    assert followup["status"] == "ready"
    # Should pivot to booking / site visit / demo
    msg_lower = followup["message"].lower()
    assert "site visit" in msg_lower or "demo" in msg_lower or "times" in msg_lower or "slot" in msg_lower


# =====================================================================
# 5. IMMEDIATE STOP & HUMAN TAKEOVER RULES TESTS
# =====================================================================

def test_immediate_stop_on_human_takeover():
    """Verify follow-up is suppressed immediately when bot_active is False (human takeover)."""
    lead = {
        "id": "lead-human-takeover",
        "customer_phone": "919876543210",
        "name": "Aditya",
        "specific_requirements": "Commercial Space",
        "bot_active": False,  # Human agent took over!
        "booked": False
    }

    followup = followups.generate_followup_message(lead)
    assert followup["status"] == "stopped"
    assert followup["reason"] == "human_takeover"
    assert followup["message"] is None


def test_immediate_stop_on_appointment_booked():
    """Verify follow-up stops immediately when customer has already booked an appointment."""
    lead = {
        "id": "lead-already-booked",
        "customer_phone": "919876543210",
        "name": "Deepa",
        "specific_requirements": "2BHK",
        "bot_active": True,
        "booked": True  # Already booked!
    }

    followup = followups.generate_followup_message(lead)
    assert followup["status"] == "stopped"
    assert followup["reason"] == "already_booked"
    assert followup["message"] is None


@pytest.mark.asyncio
async def test_immediate_stop_registry_and_cancel_endpoints():
    """Verify registry tracking, cancellation on reply, and cancellation via API."""
    phone = "919876543210"
    followups.register_pending_followup(phone, {"stage": "10m", "message": "Nudge"})
    assert followups.get_pending_followup_for_customer(phone) is not None

    # Cancel explicitly
    cancelled = followups.cancel_pending_followup_for_customer(phone)
    assert cancelled is True
    assert followups.get_pending_followup_for_customer(phone) is None

    # Register again
    followups.register_pending_followup(phone, {"stage": "1h", "message": "1h Nudge"})

    # Setup mock lead for API endpoint test
    lead_id = "lead-test-cancel"
    db._mock_leads["test-client:" + phone] = {
        "id": lead_id,
        "client_id": "test-client",
        "customer_phone": phone,
        "name": "Test User"
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post(f"/leads/{lead_id}/cancel-followup")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "cancelled"
        assert data["was_pending"] is True
        assert followups.get_pending_followup_for_customer(phone) is None
