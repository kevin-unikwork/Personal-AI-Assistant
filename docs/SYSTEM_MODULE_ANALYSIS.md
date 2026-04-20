# Personal AI Operator: Module Analysis and Extension Guide

## 1) Runtime Entry and API Layer

### `main.py`
- Initializes FastAPI app lifecycle.
- Starts scheduler and ensures DB tables exist on startup.
- Registers API routers.
- Role: composition root for runtime.

### `app/api/webhook.py`
- Handles Twilio WhatsApp inbound webhook.
- Validates Twilio signature (bypassed in debug mode).
- Offloads heavy processing to background task.
- Supports voice-note flow by transcribing media before orchestration.
- Calls `run_orchestrator(...)` and sends WhatsApp reply.

### `app/api/health.py`
- Lightweight health endpoint with DB connectivity check.

## 2) Agent Layer

### `app/agents/orchestrator.py`
- Core control-plane of the assistant.
- Responsibilities:
  - User lookup/create.
  - Safety confirmation gate via `SafetyGuard`.
  - Short-term + long-term memory retrieval.
  - Intent parsing for clarification/confirmation pre-emption.
  - LLM tool loop (ReAct-style) with bounded iterations.
  - Action logging to DB.
- Recent improvement made:
  - Tool user-context injection is now centralized (`inject_user_context`) instead of hardcoded by tool name.
  - Result: easier onboarding for new tools that need `phone_number`/`user_phone`.

### `app/agents/intent_parser.py`
- Structured intent extraction using Pydantic schema.
- Decides whether clarification or confirmation is required.
- Strong point: typed outputs.
- Improvement path: include confidence score and tool-hint field.

### `app/agents/safety_guard.py`
- In-memory pending-action state machine for YES/NO confirmations.
- Limitation: volatile (lost on restart), no TTL eviction.
- Improvement path: move to Redis or DB-backed store.

## 3) Tool Layer

### Current Tool Modules
- `calendar_tool.py`: event creation/listing, conflict check, fallback invite mechanics.
- `email_tool.py`: send/draft email wrappers.
- `whatsapp_tool.py`: proactive outbound WhatsApp.
- `task_tool.py`: reminders, assignment, list/complete tasks.
- `search_tool.py`: Tavily web search.
- `service_discovery_tool.py`: local services discovery via Tavily.
- `briefing_tool.py`: daily command-center synthesis.
- `intel_tool.py`: weather/headline intel.
- `expense_tool.py`: expense logging and summaries.
- `habit_tool.py`: habit streak tracking and status.
- `solver_tool.py`: cross-domain strategy generation.
- `appointment_tool.py`: specialized appointment booking wrapper.

### `app/tools/__init__.py`
- Tool registration point for orchestrator.
- Recent improvement made:
  - Added grouped catalog (`AGENT_TOOL_GROUPS`) for clearer organization.
  - Flattened `agent_tools` generated from groups.
  - Added `inject_user_context(...)` helper to reduce orchestration coupling.
- Why this matters:
  - New tools can be added in one place with clearer domain grouping.
  - Common identity plumbing no longer needs per-tool hacks in orchestrator.

## 4) Memory Layer

### `app/memory/short_term.py`
- In-memory conversation history (last 20 turns).
- Limitation: no persistence across restart.

### `app/memory/long_term.py`
- FAISS-based vector memory per user.
- Persists embedded preferences/context for retrieval.
- Limitation: no pruning/versioning strategy yet.

## 5) Data and Persistence

### `app/database.py`
- Async SQLAlchemy engine/session management.

### Models (`app/models/*.py`)
- `user.py`: identity, preferences, timezone, tokens.
- `task.py`: reminders/delegations lifecycle.
- `action_log.py`: audit/log trail.
- `expense.py`: spending records.
- `habit.py`: habit streak state.

### Migrations
- Alembic base migration present.
- `migrate_db.py` also performs manual SQLite column patching.
- Improvement path: keep all schema changes in Alembic revisions only.

## 6) Scheduler and Proactive Automation

### `app/scheduler/jobs.py`
- Periodic reminder scans and daily briefings.
- Recent improvement made:
  - Switched daily briefing invocation to public async tool API (`ainvoke`) instead of private/fragile `_arun` usage.

## 7) Integrations and Utilities

### `app/utils/google_auth.py`
- Service-account calendar client factory.

### `app/utils/email_client.py`
- SMTP send and IMAP draft save.

### `app/utils/twilio_client.py`
- Twilio WhatsApp send helper.

### `app/utils/voice_handler.py`
- Twilio media download + OpenAI Whisper transcription.

### `app/utils/logger.py`
- Centralized Loguru setup.

## 8) Test Coverage Snapshot

### `tests/`
- Test skeletons exist, but many are placeholders/incomplete and some are outdated with current implementation.
- Current risk: regressions can slip during feature expansion.

## 9) Key Strengths Today
- Clear separation between API, orchestration, tools, and data models.
- Good breadth of practical assistant capabilities already implemented.
- Reasonable safety baseline with explicit confirmation workflow.

## 10) Main Bottlenecks for Scaling Features
- In-memory state for safety + short-term memory (not durable).
- Tool-level async/sync patterns are mixed and occasionally brittle.
- Prompt/system logic is large and centralized; hard to evolve safely.
- Limited automated tests for critical workflows.

## 11) Recommended Next Functionalities (to make future changes easy)

1. Feature registry + capability flags
- Add a small `capabilities` config layer to enable/disable tools and experimental features per environment.

2. Durable conversation/safety state
- Move pending confirmations and short-term memory into Redis/DB with TTL.

3. Tool contract standardization
- Define a shared response contract for tools: `{ success, message, data, error_code }`.

4. Workflow-level service layer
- Add `app/services/` for multi-step business workflows (e.g., “book + notify + follow-up”).

5. Add robust integration tests
- Start with high-value paths:
  - inbound message -> intent -> safety confirmation
  - calendar booking with conflict
  - delegated task with WhatsApp fallback path

6. Observability upgrade
- Add correlation IDs per user message and per tool invocation for traceability.

## 12) Simple “How to add a new functionality” flow

1. Create tool in `app/tools/new_feature_tool.py` with `@tool`.
2. Register it in a logical group in `app/tools/__init__.py`.
3. Add safety rule in `intent_parser` + confirmation handling if action is irreversible.
4. Add at least one integration-style test in `tests/`.
5. Add logging + action log entry for the new workflow.

## 13) Newly Added Sticky Feature: Life Momentum Engine
- New model: `app/models/daily_checkin.py`
- New tools:
  - `log_daily_checkin` for daily mood/energy/sleep/win/blocker check-ins
  - `get_momentum_dashboard` for a daily score and next-best action
- New proactive scheduler behavior:
  - Evening check-in reminder if user has not logged today's check-in
- Purpose:
  - Encourages daily engagement and creates a routine loop around the assistant.

---
This document is designed to be updated as the architecture evolves.
