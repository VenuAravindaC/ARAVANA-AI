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
- Do NOT invent products, prices, inventory, or business details that have not been provided to you.
"""

# Configure Google Generative AI if key is present
client_configured = False
if GEMINI_API_KEY and GEMINI_API_KEY != "your_gemini_api_key_here":
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        client_configured = True
    except Exception as e:
        logger.warning(f"Failed to initialize google-generativeai: {e}")


def generate_reply(
    messages: list,
    system_prompt: str = None,
    business_knowledge: dict = None
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

    if not client_configured:
        last_msg = messages[-1]["content"] if messages else "Hello"
        return (
            f"[Local Test Simulation] Received: '{last_msg}'. "
            "To test with real Gemini AI, add your free GEMINI_API_KEY in .env."
        )

    try:
        import google.generativeai as genai
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash-latest",
            system_instruction=active_prompt
        )

        history_formatted = []
        for msg in messages[:-1]:
            role = "user" if msg["role"] == "user" else "model"
            history_formatted.append({"role": role, "parts": [msg["content"]]})

        chat = model.start_chat(history=history_formatted)
        latest_message = messages[-1]["content"]
        response = chat.send_message(latest_message)

        return response.text.strip()
    except Exception as e:
        logger.error(f"Error calling Gemini AI: {e}")
        return "Thank you for reaching out! Our team has received your message and will get back to you shortly."


def extract_lead_data(messages: list, extraction_schema: str = None) -> dict:
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

    # Dynamic extraction prompt
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
Rules:
- HOT: Clear budget, urgent need or asks for instant call/visit.
- WARM: Interested but timeline is flexible or exploring options.
- COLD: Vague responses or unresponsive.
- NEW: Initial inquiry, not enough details yet.
"""

    full_prompt = (
        "Analyze this WhatsApp conversation and extract structured lead data into JSON according to these instructions:\n"
        f"{base_instructions}\n\n"
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
        import google.generativeai as genai
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash-latest",
            generation_config={"response_mime_type": "application/json"}
        )
        response = model.generate_content(full_prompt)
        return json.loads(response.text)
    except Exception as e:
        logger.error(f"Error during lead extraction: {e}")
        return {
            "classification": "NEW",
            "ai_summary": f"Extraction pending: {str(e)}"
        }
