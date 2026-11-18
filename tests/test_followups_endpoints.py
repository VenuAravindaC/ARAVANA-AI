import pytest
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timedelta, timezone
from main import app
from lib import db, followups

@pytest.fixture(autouse=True)
def setup_storage(monkeypatch):
    """Ensure in-memory storage for clean test isolation."""
    monkeypatch.setattr("lib.db.supabase_client", None)
    monkeypatch.setattr("lib.followups.client_configured", False)
    db._mock_leads.clear()
    db._mock_clients.clear()
    db._mock_conversations.clear()
    db._mock_messages.clear()
    yield
    db._mock_leads.clear()
    db._mock_clients.clear()
    db._mock_conversations.clear()
    db._mock_messages.clear()

@pytest.mark.asyncio
async def test_get_followups_due_filters_inactive_leads():
    """Verify GET /leads/followups-due identifies leads inactive > 24 hours."""
    client_id = "test-client-1"
    db._mock_clients[client_id] = {
        "id": client_id,
        "business_name": "Skyline Realty",
        "follow_ups_enabled": True
    }

    now = datetime.now(timezone.utc)

    # Lead 1: Active 2 hours ago (not due)
    await db.upsert_lead(
        client_id=client_id,
        conversation_id="conv-1",
        customer_phone="919111111111",
        lead_data={
            "id": "lead-active",
            "name": "Active Customer",
            "classification": "WARM",
            "last_interaction": (now - timedelta(hours=2)).isoformat()
        }
    )

    # Lead 2: Inactive 28 hours ago (due for Stage 1 Nudge)
    await db.upsert_lead(
        client_id=client_id,
        conversation_id="conv-2",
        customer_phone="919222222222",
        lead_data={
            "id": "lead-inactive-28h",
            "name": "Inactive Customer",
            "classification": "COLD",
            "last_interaction": (now - timedelta(hours=28)).isoformat(),
            "specific_requirements": "3BHK in Indiranagar"
        }
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/leads/followups-due")
        assert res.status_code == 200
        data = res.json()
        assert data["due_count"] >= 1
        due_ids = [l["id"] for l in data["leads"]]
        assert "lead-inactive-28h" in due_ids
        assert "lead-active" not in due_ids

        due_lead = next(l for l in data["leads"] if l["id"] == "lead-inactive-28h")
        assert due_lead["followup_stage"] == 1
        assert "24h" in due_lead["followup_stage_name"]

@pytest.mark.asyncio
async def test_generate_lead_followup_endpoint():
    """Verify POST /leads/{lead_id}/generate-followup creates a personalized draft with 1-click wa.me."""
    client_id = "test-client-2"
    lead_id = "lead-sid-99"

    await db.upsert_lead(
        client_id=client_id,
        conversation_id="conv-sid",
        customer_phone="919876543210",
        lead_data={
            "id": lead_id,
            "name": "Siddharth",
            "classification": "COLD",
            "service_needed": "2BHK Apartment",
            "last_interaction": (datetime.now(timezone.utc) - timedelta(hours=30)).isoformat()
        }
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post(f"/leads/{lead_id}/generate-followup")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        followup = data["followup"]
        assert followup["customer_phone"] == "919876543210"
        assert "Siddharth" in followup["message"]
        assert followup["whatsapp_url"].startswith("https://wa.me/919876543210?text=")

@pytest.mark.asyncio
async def test_cron_run_followups():
    """Verify POST /admin/cron/run-followups processes cold leads for enabled clients."""
    client_id = "test-client-3"
    db._mock_clients[client_id] = {
        "id": client_id,
        "business_name": "Urban Nest",
        "follow_ups_enabled": True
    }

    await db.upsert_lead(
        client_id=client_id,
        conversation_id="conv-cold-1",
        customer_phone="919876500000",
        lead_data={
            "id": "lead-cold-1",
            "name": "Kavita",
            "classification": "COLD",
            "last_interaction": (datetime.now(timezone.utc) - timedelta(hours=49)).isoformat()
        }
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post("/admin/cron/run-followups")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert data["active_followup_clients"] >= 1
        assert data["drafts_generated"] >= 1
