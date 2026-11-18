# ARVANA — AI WhatsApp Lead Qualification & CRM Engine

An automated WhatsApp lead management backend engineered for Indian businesses (Real Estate & D2C Brands), built with **Python FastAPI**, **Meta WhatsApp Cloud API**, **Google Gemini 1.5 Flash**, and **Supabase PostgreSQL**.

---

## 📁 Project Architecture & Clean Folder Structure

```
E:\BUISNESS\ARVANA\
├── main.py                     # FastAPI application, Webhook handlers & Admin endpoints
├── requirements.txt            # Python dependencies (FastAPI, Uvicorn, Gemini SDK, Supabase)
├── .env.example                # Template for environment secrets
├── .env                        # Local secrets (never committed to Git)
├── .gitignore                  # Git ignore rules (.venv, .env, __pycache__, node_modules)
│
├── config/                     # Client & Industry Configuration Blueprints
│   └── templates/
│       └── industry_templates.py # Seed prompt blueprints for Agency, Real Estate & Clinics
│
├── crm-design-preview/         # High-Fidelity Client CRM & Agency Dashboard Frontend
│   ├── index.html              # Interactive CRM SPA (Leads, Calendar, Simulator, Admin)
│   ├── package.json            # Vite frontend configuration
│   └── vite.config.js          # Dev server proxy configuration
│
├── database/                   # Supabase PostgreSQL SQL Schemas & Migrations
│   ├── supabase_schema.sql     # Core tables (clients, conversations, messages, leads)
│   ├── supabase_schema_updates.sql # Booking & broker availability tables
│   └── insert_test_client.sql  # Initial real estate test client data
│
├── docs/                       # Technical & Domain Documentation
│   ├── BOOKING_SYSTEM.md       # Real estate site visit booking architecture
│   ├── CLASSIFICATION_RULES.md # AI Lead qualification logic (HOT / WARM / COLD)
│   └── archive/                # Architecture design guides
│
└── lib/                        # Core tenant-agnostic backend engines
    ├── ai.py                   # Google Gemini AI qualification & structured extraction
    ├── bookings.py             # Availability scheduler & site visit booking engine
    ├── db.py                   # Supabase database client (with in-memory fallback)
    ├── notifications.py        # Real-time broker alert notifications
    └── whatsapp.py             # Meta Graph API client for WhatsApp messaging
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
