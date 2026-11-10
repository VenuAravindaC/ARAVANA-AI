"""
Meta WhatsApp Cloud API Client
Handles outbound message delivery using official Meta Graph API v19.0.
"""

import os
import logging
import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("arvana.whatsapp")

GRAPH_API_VERSION = "v19.0"
GRAPH_API_BASE_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

DEFAULT_TOKEN = os.getenv("META_WHATSAPP_TOKEN")
DEFAULT_PHONE_ID = os.getenv("META_PHONE_NUMBER_ID")


async def send_whatsapp_text(
    to_phone: str,
    text: str,
    phone_number_id: str = None,
    access_token: str = None
) -> dict:
    """
    Sends a plain text message to a user via Meta WhatsApp Cloud API.

    :param to_phone: Recipient phone number with country code (e.g. '919876543210')
    :param text: Message body text
    :param phone_number_id: Meta Phone Number ID (defaults to .env value)
    :param access_token: Meta Access Token (defaults to .env value)
    :return: Response dict from Meta API
    """
    token = access_token or DEFAULT_TOKEN
    phone_id = phone_number_id or DEFAULT_PHONE_ID

    # Clean phone number (strip '+' or spaces)
    clean_phone = to_phone.replace("+", "").replace(" ", "").replace("-", "")

    # Local / Mock mode fallback if no Meta token configured yet
    if not token or not phone_id:
        logger.warning(
            "[MOCK MODE] Outbound WhatsApp message not sent to live Meta API "
            "(META_WHATSAPP_TOKEN or META_PHONE_NUMBER_ID not set in .env). "
            f"Target: {clean_phone} | Message: {text}"
        )
        return {
            "status": "mock_delivered",
            "to": clean_phone,
            "message": text,
            "note": "Configure META_WHATSAPP_TOKEN in .env for live Meta delivery"
        }

    url = f"{GRAPH_API_BASE_URL}/{phone_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": clean_phone,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": text
        }
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        data = response.json()

        if response.status_code >= 400:
            logger.error(f"Meta Graph API error: {response.status_code} - {data}")
            return {"status": "error", "code": response.status_code, "error": data}

        return {"status": "delivered", "data": data}
