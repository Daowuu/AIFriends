# AIFriends

[English](README.md) | [简体中文](README.zh-CN.md)

AIFriends is a single-instance AI character chat project. It focuses on three things:

- character consistency
- persistent session memory
- text / voice sharing one character logic

The product surface is intentionally small:

- `/` character list
- `/chat/:characterId` conversation page
- `/studio` character + runtime workspace

## Quick Start

Recommended:

- Python `3.12+`
- Node `20+`

### 1. Clone and install dependencies

```bash
git clone https://github.com/Daowuu/AIFriends.git
cd AIFriends

python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt

cp backend/.env.example backend/.env

cd frontend
npm install
cd ..
```

### 2. Configure the backend env

Edit:

- [backend/.env](/Users/apple/project/AIFrients/backend/.env)

## Minimal Config

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

After updating `backend/.env`, restart Django.

### 3. Run the project

Terminal 1:

```bash
source .venv/bin/activate
python3 backend/manage.py migrate
python3 backend/manage.py runserver
```

Terminal 2:

```bash
cd frontend
npm run dev -- --host 127.0.0.1
```

Default URLs:

- Backend: `http://127.0.0.1:8000`
- Frontend: `http://127.0.0.1:5173`

Optional from the repo root:

```bash
npm run dev
```

## Main Commands

```bash
python3 backend/manage.py check
python3 scripts/run_ai_eval.py
cd frontend && npm run type-check
cd frontend && npm run build-only
```

## Project Flow

1. Create or edit a character in `/studio`
2. Configure `custom_prompt`, memory mode, and voice
3. Adjust chat / ASR / TTS runtime in the same Studio
4. Trial chat and voice preview
5. Enter `/chat/:characterId` for the formal conversation

## Docs

Start here if you want implementation details:

1. [AI Overview](/Users/apple/project/AIFrients/docs/AI_OVERVIEW.md)
2. [AI Engineering](/Users/apple/project/AIFrients/docs/AI_ENGINEERING.md)
3. [Platform Functions](/Users/apple/project/AIFrients/docs/PLATFORM_FUNCTIONS.md)

Supporting files:

- [AI Evaluation Cases](/Users/apple/project/AIFrients/docs/ai_eval_cases.json)
- [Iteration Log](/Users/apple/project/AIFrients/docs/ITERATION_LOG.md)

## License

[MIT](/Users/apple/project/AIFrients/LICENSE)
