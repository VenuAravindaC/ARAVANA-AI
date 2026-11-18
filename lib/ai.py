"""
ARVANA AI Engine - Google Gemini 1.5 Flash
Pure neutral multi-tenant engine:
Takes client prompt and knowledge directly from the database.
Never hardcodes agency-specific persona or assumes identity.
"""

import os
import json
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("arvana.ai")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Safe neutral fallback if a client record has no prompt configured yet
SAFE_NEUTRAL_PROMPT = """
You are a helpful and polite customer support assistant for this business.
- Acknowledge the customer's message warmly.
- Keep responses concise (under 3 sentences).
- IMPORTANT: Ask only ONE question at a time. Never overwhelm the customer with a list of questions.
- FEATURE 4 GUARDRAIL: Do NOT invent products, prices, inventory, or business details that have not been provided to you.
- FEATURE 4 GUARDRAIL: If the customer asks something you don't know from the knowledge base, respond: "That's a great question! Let me connect you with our team who can help you with that right away."
- FEATURE 2: If the customer wants to book a site visit or appointment, ask: "What date and time works best for you?" and then confirm: "Perfect! I'll have our team confirm this booking and reach out to you shortly."
"""

# Configure Google Gemini AI if key is present
client_configured = False
if GEMINI_API_KEY and GEMINI_API_KEY != "your_gemini_api_key_here":
    try:
        from google import genai
        from google.genai import types
        client_configured = True
    except Exception as e:
        logger.warning(f"Failed to initialize google-genai: {e}")


def generate_reply(
    messages: list,
    system_prompt: str = None,
    business_knowledge: dict = None,
    available_slots: str = None
) -> str:
    """
    Generates a contextual response using the specific client's prompt from the database.
    If no prompt is configured for this client, uses a safe neutral response (NEVER impersonates ARVANA).
    """
    # Use the client's database prompt, or fall back to safe neutral assistant
    active_prompt = system_prompt if system_prompt else SAFE_NEUTRAL_PROMPT

    if business_knowledge:
        knowledge_text = json.dumps(business_knowledge, indent=2)
        active_prompt += f"\n\nBUSINESS KNOWLEDGE & INVENTORY (STRICTLY ADHERE TO THIS):\n{knowledge_text}"

    # FEATURE 2: Inject live calendar availability for booking requests
    if available_slots:
        active_prompt += f"\n\nAVAILABLE BOOKING SLOTS (Use these for site visits/appointments):\n{available_slots}\n\nIMPORTANT: Only offer these available times. If customer picks an unavailable time, politely redirect to available options."

    if not client_configured:
        last_msg = messages[-1]["content"] if messages else "Hello"
        return (
            f"[Local Test Simulation] Received: '{last_msg}'. "
            "To test with real Gemini AI, add your free GEMINI_API_KEY in .env."
        )

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(
            api_key=GEMINI_API_KEY,
            http_options=types.HttpOptions(timeout=10000)
        )

        # Generate response with conversation history context
        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=messages[-1]["content"],
            config=types.GenerateContentConfig(
                system_instruction=active_prompt,
                temperature=0.7
            )
        )

        return response.text.strip()
    except Exception as e:
        logger.error(f"Error calling Gemini AI: {e}")
        return "Thank you for reaching out! Our team has received your message and will get back to you shortly."


def extract_lead_data(messages: list, extraction_schema: str = None, classification_rules: str = None) -> dict:
    """
    Analyzes conversation and extracts structured lead criteria into JSON.
    Uses custom schema if defined, or a standard universal lead format.
    """
    if not messages:
        return {"classification": "NEW", "ai_summary": "No messages yet."}

    conversation_text = ""
    for msg in messages:
        sender = "Customer" if msg["role"] == "user" else "Assistant"
        conversation_text += f"{sender}: {msg['content']}\n"

    # Dynamic extraction prompt with customizable classification rules
    base_instructions = extraction_schema or """
Extract the following details as valid JSON:
{
  "name": string or null,
  "inquiry_type": string or null,
  "specific_requirements": string or null,
  "budget": string or null,
  "timeline": string or null,
  "classification": "HOT" | "WARM" | "COLD" | "NEW",
  "ai_summary": string (1-2 sentence executive summary of the lead's need)
}
"""

    # Use client's custom classification rules or fallback to defaults
    rules = classification_rules or """
DEFAULT CLASSIFICATION RULES:
- HOT: Clear budget + urgent timeline (within 7 days) OR asks for immediate call/site visit OR says "ready to buy/book now"
- WARM: Shows interest, has budget OR timeline, but not both urgent OR exploring multiple options
- COLD: Vague responses, no clear budget or timeline, or unresponsive after multiple messages
- NEW: Initial inquiry, not enough information to classify yet
"""

    full_prompt = (
        "Analyze this WhatsApp conversation and extract structured lead data into JSON according to these instructions:\n"
        f"{base_instructions}\n\n"
        f"CLASSIFICATION RULES:\n{rules}\n\n"
        f"Conversation:\n{conversation_text}"
    )

    if not client_configured:
        return {
            "name": None,
            "inquiry_type": "General Inquiry",
            "specific_requirements": "Testing simulator mode",
            "budget": "Pending live key",
            "timeline": "Exploring",
            "classification": "NEW",
            "ai_summary": "Lead simulated in local test mode."
        }

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(
            api_key=GEMINI_API_KEY,
            http_options=types.HttpOptions(timeout=10000)
        )

        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=full_prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.3
            )
        )
        return json.loads(response.text)
    except Exception as e:
        logger.error(f"Error during lead extraction: {e}")
        return {
            "classification": "NEW",
            "ai_summary": f"Extraction pending: {str(e)}"
        }
