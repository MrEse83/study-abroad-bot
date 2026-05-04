# CliniQ — AI-Powered Clinic Appointment System

Patients book appointments via WhatsApp using natural language.
Powered by LangChain + GPT-4o + FastAPI + Neon PostgreSQL + n8n.

---

## Stack
- **FastAPI** — API backend
- **LangChain + GPT-4o** — AI agent (multi-turn conversation)
- **Neon PostgreSQL** — database
- **Twilio** — WhatsApp messaging
- **n8n** — notifications (WhatsApp + email)

---

## Setup

### 1. Clone and enter the project
```bash
cd cliniq
```

### 2. Create virtual environment
```bash
python -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set up environment variables
```bash
cp .env.example .env
```
Fill in your actual values in `.env`

### 5. Run the server
```bash
uvicorn app.main:app --reload
```

### 6. Visit the API docs
```
http://localhost:8000/docs
```

---

## How it works

1. Patient sends a WhatsApp message to your Twilio number
2. Twilio forwards the message to `/whatsapp/webhook`
3. LangChain agent (GPT-4o) reads the message and decides what to do
4. Agent calls tools: check patient → list doctors → check slots → book
5. Appointment is saved to Neon PostgreSQL
6. n8n is triggered → sends confirmation to patient + alert to doctor

---

## Folder structure
```
cliniq/
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── database.py          # Neon DB connection
│   ├── models.py            # Database tables
│   ├── schemas.py           # Request/response validation
│   ├── config.py            # Environment variables
│   ├── routers/
│   │   ├── patients.py      # Patient registration endpoints
│   │   ├── doctors.py       # Doctor + slot management
│   │   ├── appointments.py  # Appointment endpoints
│   │   └── whatsapp.py      # Twilio webhook + AI agent
│   └── services/
│       ├── ai_agent.py      # LangChain agent logic
│       ├── availability.py  # Slot checking helpers
│       └── notifications.py # n8n webhook trigger
├── .env.example
├── requirements.txt
└── README.md
```
