# VoiceAssistant

This repository contains two LiveKit-based voice agents:

- `agent_user`: user-facing assistant for conversations and contact capture
- `agent_admin`: admin-facing assistant for protected contact lookup operations

## Project Structure

```text
agent_user/
  agent.py
  api.py
  check.py
  db_driver.py
  promts.py
  tools/
    contact_management.py
    intermediate_tools.py
    session_management.py

agent_admin/
  agent.py
  api.py
  check.py
  db_driver.py
  promts.py
  tools/
    admin_tools.py
    contact_management.py
    session_management.py
```

## What The Tools Do

### User tools (`agent_user/tools`)

- `store_user_data`: validates and stores contact details in SQLite.
- `validate_contact_info`: validates email and phone format.
- `check_duplicate_contact`: prevents duplicate contacts by phone/email.
- `format_phone_number`: normalizes phone number format.
- `summarize_conversation`: summarizes conversation history.
- `google_search` (in `intermediate_tools.py`): calls Google Custom Search API and returns title/link/snippet.

### Admin tools (`agent_admin/tools`)

- `list_all_contacts`: returns all contacts (admin-only).
- `get_contact_details_by_phone`: returns one contact by phone (admin-only).
- `admin_only` decorator: validates admin phone/token and enforces basic rate limiting.

## How Tools Are Connected In Flow

### User flow

1. `agent_user/agent.py` starts LiveKit worker and connects to a room.
2. It creates `RealtimeModel` with `GOOGLE_API_KEY`.
3. It starts `AgentSession` with the configured tool list.
4. Tool exports are grouped through `agent_user/api.py` and `agent_user/tools/__init__.py`.

Current active user tools in `agent_user/agent.py`:

- `store_user_data`
- `summarize_conversation`

Note: `google_search` exists in `agent_user/tools/intermediate_tools.py` but is not currently added to the active tool list in `agent_user/agent.py`.

### Admin flow

1. `agent_admin/agent.py` starts LiveKit worker.
2. It starts an `AgentSession` with admin tools.
3. Admin requests pass through auth logic in `agent_admin/tools/admin_tools.py`.
4. Tool exports are grouped through `agent_admin/api.py` and `agent_admin/tools/__init__.py`.

## Environment Variables

Create a `.env` file in the repo root (or export variables in terminal):

```env
GOOGLE_API_KEY=your_gemini_key
GOOGLE_API_KEY_CUSTOM_SEARCH=your_google_custom_search_key
GOOGLE_CSE_ID=your_custom_search_engine_id

# Admin-only
ADMIN_PHONE_HASH=sha256_of_admin_phone
ADMIN_SECRET_TOKEN=your_admin_secret

# LiveKit (if required by your setup)
LIVEKIT_URL=your_livekit_url
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_api_secret
```

## How To Bring API Keys To Terminal

### Option 1: Export all values from `.env` (your requested command)

```bash
export $(cat .env | xargs)
```

### Option 2: Safer loading for complex values

```bash
set -a
source .env
set +a
```

### Option 3: Export one by one

```bash
export GOOGLE_API_KEY="your_gemini_key"
export GOOGLE_API_KEY_CUSTOM_SEARCH="your_custom_search_key"
export GOOGLE_CSE_ID="your_cse_id"
```

## Local Installation

From repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r agent_user/requirements.txt
pip install -r agent_admin/requirements.txt
```

Optional quick API checks:

```bash
python agent_user/check.py
python agent_admin/check.py
```

## Run Locally

### Run user agent

```bash
cd agent_user
source ../.venv/bin/activate
python agent.py
```

### Run admin agent (separate terminal)

```bash
cd agent_admin
source ../.venv/bin/activate
python agent.py
```

## Database

- SQLite is used by both agents.
- Default DB file: `auto_db.sqlite`.
- Table initialization is handled in each `db_driver.py`.
