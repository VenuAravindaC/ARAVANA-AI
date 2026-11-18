import pytest
from httpx import AsyncClient, ASGITransport
from main import app
from lib import db

@pytest.fixture(autouse=True)
def setup_storage(monkeypatch):
    """Ensure clean in-memory storage for test isolation."""
    monkeypatch.setattr("lib.db.supabase_client", None)
    monkeypatch.setattr("lib.ai.client_configured", False)
    db._mock_clients.clear()
    db._mock_conversations.clear()
    db._mock_messages.clear()
    yield
    db._mock_clients.clear()
    db._mock_conversations.clear()
    db._mock_messages.clear()

@pytest.mark.asyncio
async def test_send_direct_whatsapp_message():
    """Verify broker can manually reply to a customer from within the CRM live chat drawer."""
    client_id = "test-chat-client"
    customer_phone = "919876543210"

    db._mock_clients[client_id] = {
        "id": client_id,
        "business_name": "Luxury Living Realty",
        "phone_number_id": "phone-123"
    }

    # Initial conversation
    conv = await db.get_or_create_conversation(client_id, customer_phone)
    conv_id = conv["id"]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Broker sends manual message
        res = await ac.post("/whatsapp/send", json={
            "client_id": client_id,
            "customer_phone": customer_phone,
            "message": "Hello! I am Amit from Luxury Living. When are you free for a call?",
            "conversation_id": conv_id,
            "auto_pause_bot": True
        })
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert data["bot_status"] == "paused_for_human_takeover"

        # Check message saved in history with sender 'agent'
        history = await db.get_messages_by_conversation(conv_id)
        assert len(history) == 1
        assert history[0]["sender"] == "agent"
        assert "Hello! I am Amit" in history[0]["content"]

        # Check conversation bot_active is now False
        conv_updated = await db.get_conversation_by_id(conv_id)
        assert conv_updated["bot_active"] is False

@pytest.mark.asyncio
async def test_toggle_conversation_bot():
    """Verify broker can toggle AI bot on or off per conversation for smooth handoff."""
    client_id = "test-chat-client-2"
    customer_phone = "919999888877"

    conv = await db.get_or_create_conversation(client_id, customer_phone)
    conv_id = conv["id"]
    assert conv["bot_active"] is True

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Toggle OFF (Pause)
        res_off = await ac.post(f"/conversation/{conv_id}/toggle-bot")
        assert res_off.status_code == 200
        assert res_off.json()["bot_active"] is False

        # 2. Toggle ON (Resume)
        res_on = await ac.post(f"/conversation/{conv_id}/toggle-bot")
        assert res_on.status_code == 200
        assert res_on.json()["bot_active"] is True

@pytest.mark.asyncio
async def test_bot_paused_suppresses_ai_reply():
    """When a broker pauses the bot, incoming customer messages are saved without triggering AI auto-replies."""
    client_id = "test-client-paused"
    phone_id = "phone-paused-123"
    customer_phone = "919777777777"

    db._mock_clients[phone_id] = {
        "id": client_id,
        "business_name": "Metro Homes",
        "phone_number_id": phone_id,
        "status": "ACTIVE"
    }
    db._mock_clients[client_id] = db._mock_clients[phone_id]

    conv = await db.get_or_create_conversation(client_id, customer_phone)
    conv_id = conv["id"]

    # Pause the bot for human takeover
    await db.pause_bot_for_conversation(conv_id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Customer sends message
        res = await ac.post("/test-message", json={
            "phone_number_id": phone_id,
            "sender_phone": customer_phone,
            "message_text": "Is anyone there?"
        })
        assert res.status_code == 200
        data = res.json()
        assert data["result"]["status"] == "bot_paused"

        # Verify customer message is recorded in transcript
        messages = await db.get_messages_by_conversation(conv_id)
        assert len(messages) >= 1
        assert any(m["content"] == "Is anyone there?" for m in messages)
