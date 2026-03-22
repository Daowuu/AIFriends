# AIFriends

[English](README.md) | [简体中文](README.zh-CN.md)

AIFriends 是一个以角色为核心的 AI 聊天项目，当前重点是：

- 角色一致性
- 长期关系记忆
- 语音一致性的互动

它面向“创作者可控的角色聊天”，不是通用 Agent 平台，也不是大规模 RAG 项目。

## 功能

- AI Studio：创建角色、调 Prompt、配置音色、试聊、诊断
- 正式聊天页：文字输入、语音输入、语音播报
- 结构化 prompt 分层
- 按“用户 + 角色”隔离的轻量长期记忆
- chat / ASR / TTS 运行时诊断

## 路由

- `/` 公开内容流
- `/chat/:characterId` 正式聊天页
- `/studio` AI Studio
- `/friends` 好友 / 关系页
- `/profile` 个人资料页
- `/settings/api` 用户级 runtime 设置页

`/workspace` 会跳到 `/studio`。

## 快速开始

### 后端

建议 Python：`3.12+`

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

后端默认地址：

- `http://127.0.0.1:8000`

### 前端

建议 Node：`20+`

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1
```

前端默认地址：

- `http://127.0.0.1:5173`

### 一键启动

在仓库根目录执行：

```bash
npm install
npm run dev
```

## 最小配置

服务端默认配置集中在：

- [backend/.env.example](backend/.env.example)

最重要的变量：

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

## 常用命令

```bash
python3 backend/manage.py check
python3 scripts/run_ai_eval.py
npm run build
```

## 文档

- [AI Overview](docs/AI_OVERVIEW.md)
- [AI Engineering](docs/AI_ENGINEERING.md)
- [Platform Functions](docs/PLATFORM_FUNCTIONS.md)
- [Iteration Log](docs/ITERATION_LOG.md)
- [AI Evaluation Cases](docs/ai_eval_cases.json)

## 项目结构

```text
AIFriends/
├── backend/
├── frontend/
├── docs/
└── scripts/
```

## 许可证

[MIT](LICENSE)
