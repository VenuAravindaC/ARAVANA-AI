import pytest
import os
from httpx import AsyncClient, ASGITransport
from main import app
from lib import db

@pytest.fixture(autouse=True)
def setup_storage(monkeypatch):
    """Ensure clean in-memory storage for test isolation."""
    monkeypatch.setattr("lib.db.supabase_client", None)
    db._mock_clients.clear()
    yield
    db._mock_clients.clear()

@pytest.mark.asyncio
async def test_agency_auth_verify_success():
    """Valid master password allows agency owner to enter the standalone admin dashboard."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post("/admin/auth/verify", json={"password": "arvana_admin_2026"})
        assert res.status_code == 200
        data = res.json()
        assert data["authenticated"] is True
        assert "token" in data

@pytest.mark.asyncio
async def test_agency_auth_verify_rejection():
    """Invalid master password returns HTTP 401 Unauthorized."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post("/admin/auth/verify", json={"password": "wrong_password"})
        assert res.status_code == 401

@pytest.mark.asyncio
async def test_admin_upsell_feature_toggles():
    """Verify Agency Admin exclusive toggles for Booking Bot, Follow-ups, and Instagram Bridge."""
    client_id = "test-agency-client-1"
    db._mock_clients[client_id] = {
        "id": client_id,
        "business_name": "Prestige Homes",
        "booking_enabled": True,
        "follow_ups_enabled": False,
        "business_knowledge": {}
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Toggle Booking Bot OFF (Agency upsell control)
        res_booking = await ac.post(f"/admin/clients/{client_id}/toggle-booking")
        assert res_booking.status_code == 200
        assert res_booking.json()["booking_enabled"] is False

        # 2. Toggle Cold Lead Follow-Ups ON (Agency upsell control)
        res_followup = await ac.post(f"/admin/clients/{client_id}/toggle-followups")
        assert res_followup.status_code == 200
        assert res_followup.json()["follow_ups_enabled"] is True

        # 3. Toggle Instagram Bridge ON
        res_ig = await ac.post(f"/admin/clients/{client_id}/toggle-instagram-bridge")
        assert res_ig.status_code == 200
        assert res_ig.json()["instagram_bridge_enabled"] is True

@pytest.mark.asyncio
async def test_admin_client_onboarding():
    """Verify onboarding wizard creates complete client record with all agency flags."""
    onboarding_payload = {
        "business_name": "Sobha Developers",
        "phone_number_id": "meta-phone-12345",
        "access_token": "meta-token-xyz",
        "broker_whatsapp": "919999999999",
        "system_prompt": "You are Sobha Realty's AI assistant.",
        "business_knowledge": {
            "properties": ["Sobha Dream Acres", "Sobha City"],
            "price_range": "₹85L - ₹2.5Cr"
        },
        "classification_rules": "HOT: Budget > 1Cr and ready to visit within 7 days",
        "booking_enabled": True,
        "follow_ups_enabled": True,
        "instagram_bridge_enabled": True,
        "status": "ACTIVE"
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post("/admin/clients", json=onboarding_payload)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        client = data["client"]
        assert client["business_name"] == "Sobha Developers"
        assert client["business_knowledge"]["booking_enabled"] is True
        assert client["business_knowledge"]["follow_ups_enabled"] is True
        assert client["business_knowledge"]["instagram_bridge_enabled"] is True

        # Delete client
        created_id = client["id"]
        res_del = await ac.delete(f"/admin/clients/{created_id}")
        assert res_del.status_code == 200
        assert res_del.json()["status"] == "success"

        # Verify client is no longer retrieved
        res_get = await ac.get(f"/admin/clients/{created_id}")
        assert res_get.status_code == 404
