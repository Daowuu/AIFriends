# AIFriends

[English](README.md) | [简体中文](README.zh-CN.md)

AIFriends is a character-driven AI chat application focused on long-term companionship, voice interaction, and creator control.

It is built around one core idea: an AI character should not just answer questions, it should stay in character, remember the relationship, support voice input/output, and give creators a stable workflow to shape how that character behaves.

## What It Does

- Character-based AI chat with persistent per-user, per-character conversations
- AI Studio for creators to define persona, prompt rules, dialogue style, memory mode, and voice settings
- Voice input with ASR and voice output with TTS
- Custom voice support with Aliyun / DashScope-compatible voice IDs
- Structured prompt layering instead of a single giant system prompt
- Lightweight long-term memory:
  - conversation summary
  - relationship memory
  - user preference memory
- Runtime diagnostics for chat / ASR / TTS source resolution
- Studio-side trial chat and voice preview for rapid iteration

## Product Direction

AIFriends is not designed as a general-purpose agent platform or a knowledge-base chatbot.

The current focus is:

- role consistency
- memory continuity
- voice consistency
- creator control
- runtime transparency

That means the main AI engineering work in this repo is around prompt structure, memory quality, diagnostics, and multimodal alignment rather than RAG or tool execution.

## Core Pages

- `/` Home feed
- `/chat/:characterId` end-user chat page
- `/studio` creator-facing AI Studio
- `/friends` user friend / relationship page
- `/profile` personal profile

## Tech Stack

### Frontend

- Vue 3
- TypeScript
- Vue Router
- Pinia
- Vite
- Tailwind CSS
- daisyUI

### Backend

- Django
- Django REST Framework
- SimpleJWT
- SQLite for local development
- OpenAI-compatible chat API clients
- DashScope-compatible ASR / TTS integration

## AI Architecture

The current AI stack is organized into five layers:

1. `runtime`
   Resolves which chat / ASR / TTS config is actually active.
2. `conversation`
   Builds prompt layers and streams the final response.
3. `memory`
   Maintains lightweight per-session memory for relationship continuity.
4. `diagnostics`
   Exposes prompt layers, memory injection, fallback state, and runtime source.
5. `persona`
   Encodes creator-controlled character behavior.

More detail lives in:

- [AI Overview](docs/AI_OVERVIEW.md)

## Local Development

### 1. Clone the repo

```bash
git clone <your-repo-url>
cd AIFriends
```

### 2. Backend setup

Create a Python environment and install the backend dependencies you use locally.

At minimum, this project expects a Django + DRF stack plus OpenAI-compatible client support.  
If you are recreating the environment from scratch, install the backend packages your local setup already uses before running migrations.

Then:

```bash
cp backend/.env.example backend/.env
python3 backend/manage.py migrate
python3 backend/manage.py runserver
```

Backend runs by default at:

- `http://127.0.0.1:8000`

### 3. Frontend setup

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1
```

Frontend runs by default at:

- `http://127.0.0.1:5173`

### 4. One-command dev startup

From repo root:

```bash
npm run dev
```

This starts both:

- Django backend
- Vite frontend

## Environment Variables

The backend reads configuration from:

- [backend/.env.example](backend/.env.example)

Key variables:

```env
API_PROVIDER="aliyun"
API_KEY=""
API_BASE="https://dashscope.aliyuncs.com/compatible-mode/v1"
CHAT_MODEL="qwen-plus"
CHAT_SUPPORTS_DASHSCOPE_AUDIO="true"
ASR_API_KEY=""
ASR_API_BASE="https://dashscope.aliyuncs.com/compatible-mode/v1"
ASR_MODEL="qwen3-asr-flash"
TTS_MODEL="cosyvoice-v3.5-plus"
DJANGO_SECRET_KEY=""
DJANGO_DEBUG="true"
DJANGO_ALLOWED_HOSTS="127.0.0.1,localhost,testserver"
DJANGO_CORS_ALLOWED_ORIGINS="http://127.0.0.1:5173,http://localhost:5173"
DJANGO_CSRF_TRUSTED_ORIGINS=""
DJANGO_MEDIA_URL="/media/"
```

Notes:

- Server-side default chat / ASR / TTS settings are centralized in `backend/.env`.
- If user-level chat config is not enabled, the backend can fall back to server-side chat env settings.
- ASR can run from its own dedicated config, or reuse a DashScope-compatible chat runtime when allowed.

## AI Studio Workflow

The intended creator workflow is:

1. Create or select a character
2. Fill in public persona info
3. Add `custom_prompt` rules for the model
4. Tune dialogue behavior:
   - reply style
   - reply length
   - initiative level
   - memory mode
   - persona boundary
5. Configure voice
6. Use Studio to:
   - preview voice
   - run trial chat
   - inspect runtime diagnostics
7. Move to the formal `/chat/:characterId` page

## Memory Model

Each user-character relationship keeps its own long-term memory in the `Friend` model:

- `conversation_summary`
- `relationship_memory`
- `user_preference_memory`
- `memory_updated_at`

Important behavior:

- memory is per-user and per-character
- memory is not shared across characters
- memory is not shared across users
- resetting the chat window is not the same thing as clearing long-term memory

## Diagnostics

The system exposes lightweight AI diagnostics so the chat stack is inspectable instead of opaque.

Current debug outputs include:

- prompt layers used in the current round
- whether memory was injected
- whether memory refresh was triggered
- runtime source
- fallback status
- last debug snapshot for Studio

## Evaluation

The repo contains lightweight internal evaluation cases for regression checking:

- [docs/ai_eval_cases.json](docs/ai_eval_cases.json)
- [scripts/run_ai_eval.py](scripts/run_ai_eval.py)

Run:

```bash
python3 scripts/run_ai_eval.py
```

This produces a manual review checklist for:

- persona consistency
- voice consistency
- preference-memory hit rate
- fallback transparency

## Project Structure

```text
AIFriends/
├── backend/
│   ├── backend/          # Django project config
│   ├── web/              # API, AI services, models, views
│   ├── media/            # Uploaded assets in local dev
│   └── manage.py
├── frontend/
│   ├── src/components/   # UI building blocks
│   ├── src/views/        # Main pages
│   ├── src/router/       # Frontend routing
│   └── src/types/        # Shared TS types
├── docs/
│   ├── AI_OVERVIEW.md
│   └── ai_eval_cases.json
└── scripts/
    ├── dev.sh
    └── run_ai_eval.py
```

## Build

Frontend production build:

```bash
npm run build
```

Or:

```bash
cd frontend
npm run type-check
npm run build-only
```

## Current State

Implemented well enough for active development:

- creator workflow via AI Studio
- character editing and voice configuration
- trial chat and diagnostics
- structured prompt assembly
- lightweight long-term memory
- runtime summary for chat / ASR / TTS
- end-user chat page

Still intentionally not the main focus:

- RAG
- general-purpose agent tooling
- real tool execution
- complex workflow automation

## Roadmap

Priority directions:

- better memory refresh quality
- stronger role-consistency evaluation
- richer diagnostics and provider compatibility tagging
- more creator-friendly prompt tooling
- optional future role-knowledge enhancement

## License

No license file has been added yet.  
If you plan to publish this repository on GitHub, add a proper `LICENSE` file before making reuse expectations public.
