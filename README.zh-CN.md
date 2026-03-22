# AIFriends

[English](README.md) | [简体中文](README.zh-CN.md)

AIFriends 是一个单实例的角色 AI 聊天项目，核心关注三件事：

- 角色一致性
- 持久会话记忆
- 文字与语音共用同一套角色逻辑

产品主线只保留三页：

- `/` 角色列表
- `/chat/:characterId` 聊天页
- `/studio` 角色与运行时工作台

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
pip install -r requirements.txt
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

### 4. 一起启动

在仓库根目录执行：

```bash
npm install
npm run dev
```

## 最小配置

先复制后端 env 文件：

```bash
cp backend/.env.example backend/.env
```

然后编辑：

- [backend/.env](/Users/apple/project/AIFrients/backend/.env)

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

修改完 `backend/.env` 后，重启 Django。

## 常用命令

```bash
python3 backend/manage.py check
python3 scripts/run_ai_eval.py
cd frontend && npm run type-check
cd frontend && npm run build-only
```

## 项目主流程

1. 在 `/studio` 创建或编辑角色
2. 配置 `custom_prompt`、记忆模式和音色
3. 在同一处调整 chat / ASR / TTS 运行时
4. 先试聊、试听
5. 再进入 `/chat/:characterId` 做正式对话

## 文档导航

如果要看实现细节，建议按这个顺序阅读：

1. [AI Overview](/Users/apple/project/AIFrients/docs/AI_OVERVIEW.md)
2. [AI Engineering](/Users/apple/project/AIFrients/docs/AI_ENGINEERING.md)
3. [Platform Functions](/Users/apple/project/AIFrients/docs/PLATFORM_FUNCTIONS.md)

辅助文件：

- [AI Evaluation Cases](/Users/apple/project/AIFrients/docs/ai_eval_cases.json)
- [Iteration Log](/Users/apple/project/AIFrients/docs/ITERATION_LOG.md)

## 许可证

[MIT](/Users/apple/project/AIFrients/LICENSE)
