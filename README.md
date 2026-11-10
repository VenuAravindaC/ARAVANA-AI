# ARVANA — AI WhatsApp Lead Qualification & CRM Engine

An automated WhatsApp lead management backend engineered for Indian businesses (Real Estate & D2C Brands), built with **Python FastAPI**, **Meta WhatsApp Cloud API**, **Google Gemini 1.5 Flash**, and **Supabase PostgreSQL**.

---

## 📁 Project Architecture & Clean Folder Structure

```
E:\BUISNESS\ARVANA\
├── main.py                     # FastAPI application & Meta Webhook handlers
├── requirements.txt            # Python dependencies (FastAPI, Uvicorn, Gemini SDK, Supabase)
├── supabase_schema.sql         # Database schema for multi-tenant clients & leads
├── .env.example                # Template for environment secrets
├── .env                        # Local secrets (never committed to Git)
├── .gitignore                  # Git ignore rules (.venv, .env, __pycache__)
│
├── config/                     # Client & Industry Configuration Blueprints
│   └── templates/
│       └── industry_templates.py # Seed prompt blueprints for Agency, Real Estate & D2C
│
├── lib/                        # Core backend engines (100% Tenant-Agnostic)
│   ├── ai.py                   # Dynamic Gemini AI engine (takes prompt from Database)
│   ├── db.py                   # Supabase database client (with local in-memory fallback)
│   └── whatsapp.py             # Meta Graph API v19.0 client for outbound messaging
```

---

## 🚀 How to Set Up & Run Locally

### 1. Initialize Python Virtual Environment (`.venv`)
Open your terminal in `E:\BUISNESS\ARVANA\` and run:

```bash
# Create virtual environment
py -m venv .venv

# Activate it (Windows PowerShell)
.venv\Scripts\activate

# Or activate in Git Bash / Command Prompt
source .venv/Scripts/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Start the FastAPI Server
```bash
uvicorn main:app --reload --port 8000
```

Once started:
* **Interactive API Documentation:** Open `http://localhost:8000/docs`
* **Health Check:** `http://localhost:8000/`

---

## 🧪 How to Test Without Meta Credentials (Local Simulation)

You can simulate live WhatsApp conversations instantly:

1. Open `http://localhost:8000/docs` in your browser.
2. Click on **`POST /test-message`** → **"Try it out"**.
3. Send a test inquiry:
   ```json
   {
     "customer_phone": "919876543210",
     "message": "Hi, I run a real estate agency in Bangalore. Need automated WhatsApp lead follow-ups. Budget is 25k."
   }
   ```
4. Click **"Execute"**.
5. The backend will:
   * Load conversation memory
   * Generate an AI qualification response
   * Extract lead criteria (Name, Budget, Timeline, Industry)
   * Score the lead (🔥 **HOT**)
   * Save it to the CRM database!
6. View captured leads anytime by visiting: `http://localhost:8000/leads`.

---

## 🔑 Going Live with Meta WhatsApp Cloud API

When Meta's verification cooldown resets:
1. Paste your credentials into `.env`:
   * `META_WHATSAPP_TOKEN`
   * `META_PHONE_NUMBER_ID`
   * `META_WABA_ID`
2. Point your Meta Developer Webhook to:
   * **Callback URL:** `https://your-public-url.com/webhook`
   * **Verify Token:** `arvana_secret_webhook_verify_token_2026`
   * **Webhook Fields:** Subscribe to `messages`.
