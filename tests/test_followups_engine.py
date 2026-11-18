import pytest
from datetime import datetime, timedelta, timezone
from lib.followups import (
    determine_followup_stage,
    generate_followup_message,
    is_followups_enabled_for_client
)

def test_followup_stage_determination():
    """Verify follow-up stages based on inactivity window."""
    now = datetime.now(timezone.utc)

    # 12 hours inactive - Not due yet
    recent = now - timedelta(hours=12)
    assert determine_followup_stage(recent, now) is None

    # 26 hours inactive - Stage 1 (24h Nudge)
    stg1_time = now - timedelta(hours=26)
    stg1 = determine_followup_stage(stg1_time, now)
    assert stg1 is not None
    assert stg1["stage"] == 1
    assert "24h" in stg1["name"]

    # 50 hours inactive - Stage 2 (48h Value Hook)
    stg2_time = now - timedelta(hours=50)
    stg2 = determine_followup_stage(stg2_time, now)
    assert stg2 is not None
    assert stg2["stage"] == 2
    assert "48h" in stg2["name"]

    # 8 days inactive - Stage 3 (Day 7 Soft Close)
    stg3_time = now - timedelta(days=8)
    stg3 = determine_followup_stage(stg3_time, now)
    assert stg3 is not None
    assert stg3["stage"] == 3
    assert "Day 7" in stg3["name"]

def test_generate_followup_message_structure():
    """Verify generated follow-up contains tailored copy and valid wa.me 1-click link."""
    lead = {
        "id": "lead-123",
        "customer_phone": "919876543210",
        "name": "Siddharth",
        "specific_requirements": "3BHK in Whitefield",
        "budget": "90L",
        "classification": "COLD",
        "last_interaction": (datetime.now(timezone.utc) - timedelta(hours=28)).isoformat()
    }

    result = generate_followup_message(lead)
    assert result["lead_id"] == "lead-123"
    assert result["customer_phone"] == "919876543210"
    assert "Siddharth" in result["message"] or "Whitefield" in result["message"] or "touch" in result["message"].lower()
    assert result["whatsapp_url"].startswith("https://wa.me/919876543210?text=")
    assert result["stage"] == 1

def test_is_followups_enabled_flag():
    """Verify agency upsell feature flag detection."""
    assert is_followups_enabled_for_client({"follow_ups_enabled": True}) is True
    assert is_followups_enabled_for_client({"follow_ups_enabled": False}) is False
    assert is_followups_enabled_for_client({"business_knowledge": {"follow_ups_enabled": True}}) is True
    assert is_followups_enabled_for_client({}) is False
