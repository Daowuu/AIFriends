# AIFriends

[English](README.md) | [简体中文](README.zh-CN.md)

AIFriends 是一个以角色为核心的 AI 聊天项目，当前围绕三项能力持续迭代：

- 角色一致性
- 长期关系记忆
- 语音一致性的互动

它面向“创作者可控的角色聊天”。

## 你可以做什么

- 在 `AI Studio` 中创建和调试角色
- 配置公开人设、`custom_prompt`、对话风格、记忆模式和音色
- 在进入正式聊天页前先试聊、试听
- 用同一套角色逻辑承接文字聊天、语音输入和语音播报
- 未登录时可以直接进行简单试玩
- 查看 chat / ASR / TTS 的运行时诊断

## 主要路由

- `/` 公开内容流
- `/chat/:characterId` 正式聊天页
- `/studio` AI Studio
- `/friends` 好友 / 关系页
- `/profile` 个人资料页
- `/settings/api` 用户级 runtime 设置页

`/workspace` 会跳到 `/studio`。

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/Daowuu/AIFriends.git
cd AIFriends
```

### 2. 启动后端

建议 Python：`3.12+`

```bash
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

### 3. 启动前端

建议 Node：`20+`

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1
```

前端默认地址：

- `http://127.0.0.1:5173`

### 4. 一键启动

在仓库根目录执行：

```bash
npm install
npm run dev
```

## 最小配置

服务端默认配置集中在：

- [backend/.env.example](backend/.env.example)

先复制一份本地配置文件：

```bash
cp backend/.env.example backend/.env
```

然后编辑：

- [backend/.env](backend/.env)

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
DEMO_TEXT_CHAT_LIMIT="20"
DEMO_VOICE_CHAT_LIMIT="5"
DJANGO_SECRET_KEY=""
DJANGO_DEBUG="true"
DJANGO_ALLOWED_HOSTS="127.0.0.1,localhost,testserver"
DJANGO_CORS_ALLOWED_ORIGINS="http://127.0.0.1:5173,http://localhost:5173"
```

修改完 `backend/.env` 后，重启 Django 服务。

runtime 解析顺序：

- 用户配置完整：优先使用用户配置
- 用户配置损坏：返回 `invalid`
- 未启用用户配置：尝试服务端默认配置
- 系统里没有可用 runtime：返回 `missing`

## 常用命令

```bash
python3 backend/manage.py check
python3 scripts/run_ai_eval.py
npm run build
```

## 建议阅读顺序

如果只是启动项目，这份 README 就够了。  
如果要继续理解或迭代 AI 逻辑，建议按这个顺序阅读：

1. [AI Overview](docs/AI_OVERVIEW.md)
2. [AI Engineering](docs/AI_ENGINEERING.md)
3. [Platform Functions](docs/PLATFORM_FUNCTIONS.md)
4. [Iteration Log](docs/ITERATION_LOG.md)

辅助文件：

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
