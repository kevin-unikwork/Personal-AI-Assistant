# Personal AI Life Operator (WhatsApp-First Assistant)

A WhatsApp-first autonomous personal assistant built with **FastAPI + LangChain tools**. It connects to **Twilio WhatsApp**, can **schedule Google Calendar events**, **send emails**, **set reminders**, **log expenses**, **track habits**, and run **proactive daily jobs** (briefings, reminders, check-in nudges).

> This repo is designed to be practical: the assistant lives on WhatsApp, supports short conversational commands, and uses a tool-driven agent loop for real actions.

---

## Table of Contents

- [What You Get](#what-you-get)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [System Flow](#system-flow)
- [Tools (Capabilities)](#tools-capabilities)
- [Data Model](#data-model)
- [Scheduler Jobs](#scheduler-jobs)
- [Safety & Confirmation](#safety--confirmation)
- [Configuration](#configuration)
- [Local Development](#local-development)
- [Running the WhatsApp Webhook](#running-the-whatsapp-webhook)
- [Testing](#testing)
- [Operational Notes](#operational-notes)
- [Limitations](#limitations)
- [Roadmap](#roadmap)
- [Troubleshooting](#troubleshooting)

---

## What You Get

- A **FastAPI server** with:
  - `POST /webhook/whatsapp` — Twilio inbound webhook endpoint
  - `GET /health` — health check with DB ping
- An **agent orchestrator** that:
  - Loads/creates a user record
  - Performs safety confirmation gating (YES/NO)
  - Retrieves short-term + long-term memory context
  - Runs a bounded tool-execution loop (ReAct style)
  - Logs actions to the database
- **Proactive automation** via APScheduler:
  - Reminder checks (every 5 min)
  - Daily briefing (cron)
  - Evening check-in nudge (cron)

---

## Key Features

### WhatsApp-First Experience

- Inbound WhatsApp messages via Twilio webhook.
- Outbound WhatsApp messages via Twilio API.
- Optional interactive UX:
  - Converts “Should I go ahead?” to **Yes/No** interactive templates
  - Converts numbered lists to **list picker** templates

### Voice Notes (Optional)

- If a WhatsApp message includes audio media, the system:
  - Downloads audio from Twilio Media URL
  - Transcribes to text (OpenAI Whisper API)
  - Feeds transcript into the orchestrator

### Calendar + Email + Tasks

- Google Calendar event creation:
  - Parses times, converts to UTC
  - Checks conflicts
  - Creates event
  - For service accounts (no attendee invites), it falls back to manual email + optional WhatsApp invite
- Gmail SMTP send + IMAP draft save (using a Gmail App Password)
- Reminders/tasks with due times, recurrence, and reminder sending

### Finance / Habits / Momentum

- Log expenses and get weekly/monthly summaries.
- Track habit streaks.
- Daily check-ins (mood/energy/sleep/win/blocker) and “momentum dashboard” score.

### Web Intel / Local Service Discovery

- Tavily-powered web search (for “what’s happening”, “find sources”, etc.)
- Tavily-powered local service discovery (top rated services in a location)

---

## System Architecture

High-level components:

```
                 ┌────────────────────────────┐
                 │          Twilio            │
                 │   WhatsApp Inbound/Out     │
                 └─────────────┬──────────────┘
                               │  webhook
                               v
┌──────────────────────────────────────────────────────────┐
│                         FastAPI                           │
│  main.py                                                   │
│  - lifespan: start scheduler, create tables               │
│  - routes: /webhook/whatsapp, /health                     │
└─────────────┬──────────────────────────────┬─────────────┘
              │                              │
              │ background task              │ scheduler
              v                              v
┌────────────────────────────┐      ┌──────────────────────┐
│  Orchestrator Agent         │      │ APScheduler Jobs      │
│  app/agents/orchestrator.py │      │ app/scheduler/jobs.py │
│  - safety confirmation      │      │ - reminders           │
│  - memory retrieval         │      │ - briefing            │
│  - tool loop (LLM+tools)    │      │ - check-in nudges      │
└─────────────┬──────────────┘      └──────────┬───────────┘
              │                                │
              v                                v
┌────────────────────────────┐      ┌──────────────────────┐
│ Tools (LangChain @tool)     │      │ Database (SQLAlchemy)│
│ app/tools/*.py              │      │ SQLite by default     │
│ calendar/email/tasks/etc.   │      │ app/models/*.py       │
└────────────────────────────┘      └──────────────────────┘

Memory:
- Short-term: in-memory conversation buffer (non-persistent)
- Long-term: FAISS vector store per-user (persisted under faiss_indexes/)
```

---

## System Flow

### 1) Inbound WhatsApp Message

1. Twilio calls `POST /webhook/whatsapp` with form data.
2. Server verifies Twilio signature (unless `DEBUG=true`).
3. The request returns a fast 200 response (empty TwiML), and work continues in a background task.

### 2) Voice Note Handling (If Media Present)

1. Download audio from Twilio using Basic Auth (`TWILIO_ACCOUNT_SID` + `TWILIO_AUTH_TOKEN`).
2. Transcribe with OpenAI Whisper.
3. Replace the user message with transcript text.

### 3) Orchestration & Decision

1. Load/create `User` by phone number.
2. If a pending “confirmation” exists, interpret the reply as YES/NO and proceed/cancel.
3. Load short-term conversation history (last ~20 turns).
4. Retrieve relevant long-term context from FAISS.
5. Run intent parsing (structured output) to decide if clarification/confirmation is required.
6. Run the agent tool loop for up to `MAX_TOOL_ITERATIONS=5`.
7. Persist:
   - short-term memory buffer
   - action log entry

### 4) Send Reply

1. If the response looks like an interactive prompt, try sending Twilio Content Template interactive UI.
2. Otherwise send a normal WhatsApp message.

---

## Tools (Capabilities)

Tools are registered in `app/tools/__init__.py` and exposed to the agent.

### Calendar

- `create_event` — Create Google Calendar event with conflict detection and invite fallback
- `list_events` — List events on a given date

### Tasks & Reminders

- `create_reminder` — Create a reminder task with due time and recurrence
- `list_tasks` — List tasks by status
- `complete_task` — Mark task complete
- `assign_task` — Delegate a task to another person via WhatsApp; email fallback supported

### Email

- `send_email` — Send via Gmail SMTP (should be used only after explicit user confirmation)
- `draft_email` — Create Gmail draft via IMAP

### Messaging

- `send_whatsapp` — Proactive outbound WhatsApp message

### Discovery / Search

- `web_search` — Tavily search for current info
- `find_local_services` — Tavily “top rated <category> in <location>”

### Briefing & Intel

- `get_daily_briefing` — Daily command center briefing (calendar + tasks + intel + finance + habits)
- `get_morning_intel` — Tavily weather + headlines

### Finance

- `log_expense` — Store an expense
- `get_expense_summary` — Summaries by period

### Habits

- `track_habit` — Mark a habit done today (streak logic)
- `get_habit_status` — Status dashboard

### Momentum Engine

- `log_daily_checkin` — Mood/energy/sleep/win/blocker
- `get_momentum_dashboard` — Score + next action

### Strategy

- `solve_life_problem` — A “master plan” tool that gathers life state and produces strategy steps

---

## Data Model

Tables (SQLAlchemy models in `app/models/`):

- `users`
  - `phone_number`, `timezone`, `preferences`, timestamps
- `tasks`
  - reminders + delegation (`assigned_to`, `assigned_by`), recurrence, status
- `daily_checkins`
  - unique per-user per-date mood/energy/sleep/win/blocker
- `expenses`
  - amount, category, description, timestamp
- `habits`
  - streak + last completed
- `action_logs`
  - intent, action, success/error fields (audit trail)

Database defaults to SQLite:

- `sqlite+aiosqlite:///./personal_ai.db`

Migrations:

- Alembic is configured (`alembic/`).
- There is also a small manual SQLite patch script (`migrate_db.py`) for legacy schema changes.

---

## Scheduler Jobs

Configured in `app/scheduler/jobs.py`:

- Reminder scan: runs every 5 minutes
  - Finds pending tasks near-due and sends WhatsApp reminders
  - Handles simple recurrence (`hourly`, `daily`, `weekly`)
- Daily briefing: cron at configured hour/minute
  - Sends a daily briefing to each user
- Evening check-in nudge: cron at configured hour/minute
  - If no check-in exists for today (in the user’s timezone), sends a nudge message

---

## Safety & Confirmation

The system has a “pending action” confirmation mechanism:

- The intent parser can mark an action as requiring confirmation.
- Orchestrator stores a pending action in memory.
- User replies “yes/ok/go ahead/1” to proceed or “no/cancel/2” to cancel.

Notes:

- Pending confirmations are stored in an **in-memory dict**, so they reset if the service restarts.

---

## Configuration

Settings are read from `.env` using `pydantic-settings` in `app/config.py`.

### Required env vars (typical)

| Variable | Required | Purpose |
|---|---:|---|
| `OPENAI_API_KEY` | Yes | LLM + Whisper transcription |
| `TWILIO_ACCOUNT_SID` | Yes | Twilio API auth |
| `TWILIO_AUTH_TOKEN` | Yes | Twilio signature validation + media download |
| `TWILIO_WHATSAPP_FROM` | Yes | Twilio WhatsApp sender (e.g. `whatsapp:+1415...`) |
| `GOOGLE_EMAIL` | Yes | Gmail SMTP/IMAP login |
| `GOOGLE_TEMP_PASSWORD` | Yes | Gmail App Password |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Yes | Path to service account JSON for Calendar |
| `GOOGLE_CALENDAR_ID` | No | Defaults to `primary` |
| `SECRET_KEY` | Yes | App secret value |

### Optional env vars

| Variable | Default | Purpose |
|---|---:|---|
| `TAVILY_API_KEY` | empty | Enables search/intel/service discovery tools |
| `DATABASE_URL` | SQLite | Database connection |
| `DEBUG` | `false` | If true, Twilio request signature validation is bypassed |
| `LOG_LEVEL` | `INFO` | Logging level |
| `DAILY_BRIEFING_HOUR` | `7` | Scheduler |
| `DAILY_BRIEFING_MINUTE` | `30` | Scheduler |
| `EVENING_CHECKIN_HOUR` | `21` | Scheduler |
| `EVENING_CHECKIN_MINUTE` | `0` | Scheduler |
| `REMINDER_LEAD_MINUTES` | `0` | Send reminders early |
| `TWILIO_WHATSAPP_QUICK_REPLY_CONTENT_SID` | empty | Twilio interactive template |
| `TWILIO_WHATSAPP_LIST_PICKER_CONTENT_SID` | empty | Twilio interactive template |

> Use `.env.example` as a template. Never commit real credentials.

---

## Local Development

### 1) Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate  # (Windows PowerShell: .venv\Scripts\Activate.ps1)
pip install -r requirements.txt
```

### 2) Configure environment

1. Copy `.env.example` to `.env`
2. Fill in real values for Twilio, OpenAI, and Google.

### 3) Run the API server

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Health check:

```bash
curl http://localhost:8000/health
```

---

## Running the WhatsApp Webhook

### Twilio Setup

1. Configure your Twilio WhatsApp sender (`TWILIO_WHATSAPP_FROM`).
2. Expose your local server via a tunnel (e.g., ngrok).
3. Set Twilio webhook URL to:

```
https://<your-public-domain>/webhook/whatsapp
```

### Important: Signature Verification

- In production, keep `DEBUG=false` so signature validation is enforced.
- If you are testing locally and signatures are failing, either:
  - ensure Twilio is hitting the correct public URL (proxy headers matter), or
  - temporarily set `DEBUG=true` for local testing only.

---

## Testing

Run tests:

```bash
pytest
```

The test suite includes:

- Interactive prompt detection/parsing
- Twilio template variable construction logic
- Check-in message parsing
- Timezone normalization helpers

---

## Operational Notes

### Persistence

- Short-term memory and safety confirmation state are in-memory (reset on restart).
- Long-term memory is persisted to disk in `faiss_indexes/`.
- SQLite DB file is `personal_ai.db` by default.

### Logging

- Loguru structured JSON logs are configured in `app/utils/logger.py`.

---

## Limitations

- In-memory state (short-term memory + pending confirmations) is not durable.
- Some tools mix sync/async patterns; the orchestrator runs tools in a thread loop to keep FastAPI responsive.
- Calendar service account cannot invite attendees directly without domain-wide delegation, so the system uses an email fallback.
- Voice notes require OpenAI Whisper (unless you replace transcription with another provider).

---

## Roadmap

Recommended next improvements:

1. Durable conversation + confirmation store (Redis/DB + TTL).
2. Structured tool return contract (e.g., `{ success, message, data }`) instead of plain strings.
3. Correlation IDs per inbound message + tool invocation for traceability.
4. Integration tests for: webhook → orchestrator → tool execution → messaging.
5. Configurable “capability flags” to disable tools in certain environments.

---

## Troubleshooting

### Push blocked due to secrets

- Do not store keys in `.env.example`.
- Keep `.env` out of git (already ignored via `.gitignore`).

### Twilio webhook returns 403

- Signature verification failed.
- Ensure the webhook URL matches the externally visible URL (tunnel/proxy headers).
- Confirm `TWILIO_AUTH_TOKEN` is correct.

### Calendar errors

- Ensure `GOOGLE_SERVICE_ACCOUNT_JSON` points to an existing JSON file.
- Confirm the service account has access to the calendar (`GOOGLE_CALENDAR_ID`).

### Email send fails

- Ensure Gmail App Password is correct.
- Gmail account must have 2FA enabled to create app passwords.

### Tavily tools say API key missing

- Add `TAVILY_API_KEY` to `.env` to enable intel/search/service discovery features.

