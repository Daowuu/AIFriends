# AIFriends

[English](README.md) | [简体中文](README.zh-CN.md)

AIFriends is a character-driven AI chat project centered on three capabilities:

- role consistency
- long-term relationship memory
- voice-aligned interaction

It is built for creator-controlled character chat.

## What You Can Do

- Create and tune characters in `AI Studio`
- Configure public persona, `custom_prompt`, dialogue style, memory mode, and voice
- Run trial chat and voice preview before entering the formal chat page
- Use text chat, voice input, and voice playback with one shared character logic
- Try the chat experience before logging in
- Inspect runtime diagnostics for chat / ASR / TTS

## Main Routes

- `/` public feed
- `/chat/:characterId` formal chat
- `/studio` AI Studio
- `/friends` friend / relationship page
- `/profile` profile page
- `/settings/api` user runtime settings

`/workspace` redirects to `/studio`.

## Quick Start

### 1. Clone

```bash
git clone https://github.com/Daowuu/AIFriends.git
cd AIFriends
```

### 2. Start the backend

Recommended Python: `3.12+`

```bash
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

### 3. Start the frontend

Recommended Node: `20+`

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1
```

Frontend default:

- `http://127.0.0.1:5173`

### 4. Start both together

From repo root:

```bash
npm install
npm run dev
```

## Minimal Config

Server-side defaults are centralized in:

- [backend/.env.example](backend/.env.example)

First copy the local config file:

```bash
cp backend/.env.example backend/.env
```

Then edit:

- [backend/.env](backend/.env)

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
DEMO_TEXT_CHAT_LIMIT="20"
DEMO_VOICE_CHAT_LIMIT="5"
DJANGO_SECRET_KEY=""
DJANGO_DEBUG="true"
DJANGO_ALLOWED_HOSTS="127.0.0.1,localhost,testserver"
DJANGO_CORS_ALLOWED_ORIGINS="http://127.0.0.1:5173,http://localhost:5173"
```

After updating `backend/.env`, restart the Django server.

Runtime resolution:

- valid user config: use user config
- broken user config: return `invalid`
- no user config: use server-side defaults when available
- no valid runtime anywhere: return `missing`

## Common Commands

```bash
python3 backend/manage.py check
python3 scripts/run_ai_eval.py
npm run build
```

## Reading Order

If you only need to run the project, this README is enough.  
If you need to understand or extend the AI logic, read in this order:

1. [AI Overview](docs/AI_OVERVIEW.md)
2. [AI Engineering](docs/AI_ENGINEERING.md)
3. [Platform Functions](docs/PLATFORM_FUNCTIONS.md)
4. [Iteration Log](docs/ITERATION_LOG.md)

Supporting files:

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
