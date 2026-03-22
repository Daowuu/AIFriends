# AIFriends

[English](README.md) | [简体中文](README.zh-CN.md)

AIFriends is a character-driven AI chat project focused on:

- role consistency
- long-term relationship memory
- voice-aligned interaction

It is built for creator-controlled character chat, not general-purpose agents or large-scale RAG.

## Features

- AI Studio for character creation, prompt tuning, voice setup, trial chat, and diagnostics
- Formal chat page with text input, voice input, and voice playback
- Structured prompt layers
- Lightweight long-term memory per user and per character
- Runtime diagnostics for chat / ASR / TTS

## Routes

- `/` public feed
- `/chat/:characterId` formal chat
- `/studio` AI Studio
- `/friends` friend / relationship page
- `/profile` profile page
- `/settings/api` user runtime settings

`/workspace` redirects to `/studio`.

## Quick Start

### Backend

Recommended Python: `3.12+`

```bash
git clone https://github.com/Daowuu/AIFriends.git
cd AIFriends

python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install django djangorestframework djangorestframework-simplejwt django-cors-headers python-dotenv openai

cp backend/.env.example backend/.env
python3 backend/manage.py migrate
python3 backend/manage.py runserver
```

Backend default:

- `http://127.0.0.1:8000`

### Frontend

Recommended Node: `20+`

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1
```

Frontend default:

- `http://127.0.0.1:5173`

### One-command dev

From repo root:

```bash
npm install
npm run dev
```

## Minimal Config

Server-side defaults are centralized in:

- [backend/.env.example](backend/.env.example)

Most important variables:

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
```

## Common Commands

```bash
python3 backend/manage.py check
python3 scripts/run_ai_eval.py
npm run build
```

## Docs

- [AI Overview](docs/AI_OVERVIEW.md)
- [AI Engineering](docs/AI_ENGINEERING.md)
- [Platform Functions](docs/PLATFORM_FUNCTIONS.md)
- [Iteration Log](docs/ITERATION_LOG.md)
- [AI Evaluation Cases](docs/ai_eval_cases.json)

## Project Structure

```text
AIFriends/
├── backend/
├── frontend/
├── docs/
└── scripts/
```

## License

[MIT](LICENSE)
