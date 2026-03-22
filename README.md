# AIFriends

[English](README.md) | [简体中文](README.zh-CN.md)

AIFriends is a single-instance AI character chat project. It focuses on four things:

- character consistency
- persistent session memory
- text / voice sharing one character logic
- lightweight multi-character role experiments

The product surface is intentionally small:

- `/` character list
- `/chat/:characterId` conversation page
- `/studio` character + runtime workspace
- `/discussion` multi-character discussion room

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

### 2. Configure the runtime file

Edit:

- [backend/.env](/Users/apple/project/AIFrients/backend/.env)

`/studio` reads and writes this same file. Runtime settings changed in Studio are synced back to `backend/.env`.

## Minimal Config

Most important variables:

```env
AI_RUNTIME_CONFIG_JSON='{
  "version": 4,
  "active": {
    "chat_provider": "openai"
  },
  "api_keys": {
    "openai": "",
    "minimax": "",
    "aliyun_voice": ""
  },
  "chat": {
    "openai": {
      "api_base": "https://api.openai.com/v1",
      "model_name": "gpt-5.4",
      "updated_at": ""
    }
  },
  "voice": {
    "provider": "aliyun",
    "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "asr_model_name": "qwen3-asr-flash",
    "tts_model_name": "cosyvoice-v3.5-plus",
    "updated_at": ""
  }
}'

DJANGO_SECRET_KEY=""
DJANGO_DEBUG="true"
DJANGO_ALLOWED_HOSTS="127.0.0.1,localhost,testserver"
DJANGO_CORS_ALLOWED_ORIGINS="http://127.0.0.1:5173,http://localhost:5173"
```

After updating `backend/.env`, restart Django.

### 3. Migrate and run

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

### 4. Built-in character seeds

The repo now ships with a built-in character seed file:

- [backend/web/fixtures/default_characters.json](/Users/xxx/project/AIFriends/backend/web/fixtures/default_characters.json)

Current behavior:

- If the local character library is empty, the first visit to the homepage feed or `/api/character/list/` will auto-seed these characters into the local database.
- If the local database already has characters, the seed will not overwrite them.
- On another machine, after `git pull`, a fresh empty database will automatically get the built-in roles as soon as the character list is loaded.

Important:

- Auto-seeding only handles empty-library initialization.
- It does not force-import the seed into a non-empty local database.

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
3. Drag the character tabs in Studio if you want to reorder the list
4. Check the role overview and memory state
5. Adjust chat / ASR / TTS runtime in the same Studio
6. Trial chat and voice preview
7. Enter `/chat/:characterId` for the formal conversation
8. If you want a multi-character prototype, enter `/discussion` to create a moderated discussion room

## Using the Sample Role

If you just want to try the full workflow quickly:

1. Open `/studio`
2. Go to `角色配置`
3. Click `填入爱莉希雅示例`
4. Review the generated profile, prompt, AI behavior, voice draft, avatar, and background image
5. Save the character
6. Continue with `角色概览`, `试聊诊断`, or open `/chat/:characterId`

The sample button is useful as a starting point because it fills all three configuration steps at once instead of only creating an empty draft.

## Built-in roles vs. the sample role

There are now two layers of role bootstrapping:

1. Built-in character seeds
   These guarantee that a fresh environment has a usable starter role library.
2. `填入爱莉希雅示例`
   This is a Studio shortcut for generating a fuller Elysia draft with prompt, voice draft, and media assets.

They serve different purposes:

- built-in seeds solve “does this environment have roles at all?”
- the sample button solves “how do I quickly create one polished demo role?”

## Screenshots

### Chat

![Chat](docs/assets/readme/chat.png)

### Studio

![Studio](docs/assets/readme/studio.png)

## Docs

Start here if you want implementation details:

1. [AI Overview](/Users/apple/project/AIFrients/docs/AI_OVERVIEW.md)
2. [AI Engineering](/Users/apple/project/AIFrients/docs/AI_ENGINEERING.md)
3. [Discussion Engineering](/Users/xxx/project/AIFriends/docs/DISCUSSION_ENGINEERING.md)
4. [Platform Functions](/Users/apple/project/AIFrients/docs/PLATFORM_FUNCTIONS.md)

Supporting files:

- [AI Evaluation Cases](/Users/apple/project/AIFrients/docs/ai_eval_cases.json)
- [Iteration Log](/Users/apple/project/AIFrients/docs/ITERATION_LOG.md)

## License

[MIT](/Users/apple/project/AIFrients/LICENSE)
