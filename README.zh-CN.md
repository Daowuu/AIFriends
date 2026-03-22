# AIFriends

[English](README.md) | [简体中文](README.zh-CN.md)

AIFriends 是一个以角色为核心的 AI 聊天应用，重点关注长期陪伴、语音交互和创作者控制。

这个项目的核心理念是：AI 角色不应该只是回答问题，它还应该长期保持角色一致性、记住关系、支持语音输入输出，并给创作者一套稳定的工作流去塑造角色行为。

## 项目能力

- 以角色为核心的 AI 聊天，支持按“用户-角色”维度持续保留会话
- AI Studio，供创作者配置角色人设、Prompt 规则、对话风格、记忆模式和音色
- 语音输入（ASR）与语音播报（TTS）
- 支持接入阿里云 / DashScope 兼容的自定义音色 `voice_id`
- 使用结构化 prompt 分层，而不是单个超长 system prompt
- 轻量长期记忆：
  - 会话摘要
  - 关系记忆
  - 用户偏好记忆
- 聊天 / ASR / TTS 的运行时诊断与来源解析
- 在 Studio 中直接试聊与试听，方便快速迭代角色

## 产品方向

AIFriends 当前不是：

- 通用 Agent 平台
- 知识库问答系统
- 工具执行平台

当前更关注：

- 角色一致性
- 关系连续性
- 语音一致性
- 创作者控制能力
- 运行时透明性

所以这个仓库里的 AI 工程重点主要放在：

- Prompt 结构化
- 记忆质量
- 诊断能力
- 多模态一致性

而不是优先做 RAG 或工具执行。

## 核心页面

- `/` 首页内容流
- `/chat/:characterId` 用户正式聊天页
- `/studio` 创作者 AI Studio
- `/friends` 好友 / 关系页
- `/profile` 个人主页

## 技术栈

### 前端

- Vue 3
- TypeScript
- Vue Router
- Pinia
- Vite
- Tailwind CSS
- daisyUI

### 后端

- Django
- Django REST Framework
- SimpleJWT
- SQLite（本地开发）
- OpenAI 兼容聊天接口
- DashScope 兼容 ASR / TTS

## AI 架构

当前 AI 工程按 5 层组织：

1. `runtime`
   负责解析这一轮聊天 / ASR / TTS 实际由谁在运行。
2. `conversation`
   负责组装 prompt 分层并流式返回回复。
3. `memory`
   负责维护轻量会话记忆，保证关系连续。
4. `diagnostics`
   负责暴露 prompt layers、记忆注入、fallback 和 runtime 来源。
5. `persona`
   负责创作者可控的角色行为定义。

详细设计见：

- [AI Overview](docs/AI_OVERVIEW.md)

## 本地开发

### 1. 克隆仓库

```bash
git clone <your-repo-url>
cd AIFriends
```

### 2. 后端启动

当前仓库还没有提供固定版 `requirements.txt`，所以后端依赖需要显式安装。

建议先创建一个干净的 Python 3.12+ 环境：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install django djangorestframework djangorestframework-simplejwt django-cors-headers python-dotenv openai
```

然后执行：

```bash
cp backend/.env.example backend/.env
python3 backend/manage.py migrate
python3 backend/manage.py runserver
```

后端默认运行在：

- `http://127.0.0.1:8000`

### 3. 前端启动

建议 Node 版本：`20+`

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1
```

前端默认运行在：

- `http://127.0.0.1:5173`

### 4. 一键启动前后端

在仓库根目录执行：

```bash
npm run dev
```

这会同时启动：

- Django 后端
- Vite 前端

## 环境变量

后端配置样例见：

- [backend/.env.example](backend/.env.example)

主要变量：

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

说明：

- 服务端默认的 chat / ASR / TTS 配置现在统一收敛在 `backend/.env`
- 如果没有启用用户级聊天配置，后端会优先尝试服务端默认聊天环境变量
- ASR 可以走独立配置，也可以在允许时复用 DashScope 兼容聊天配置

## AI Studio 工作流

当前创作者推荐工作流：

1. 创建或选择角色
2. 填写角色公开信息
3. 添加 `custom_prompt` 作为模型规则
4. 调整对话行为：
   - 回复风格
   - 回复长度
   - 主动性
   - 记忆模式
   - 角色边界
5. 配置音色
6. 在 Studio 中：
   - 试听音色
   - 试聊角色
   - 查看运行时与诊断信息
7. 最后进入 `/chat/:characterId` 正式聊天页

## 记忆模型

每个“用户-角色”关系会在 `Friend` 模型中维护长期记忆：

- `conversation_summary`
- `relationship_memory`
- `user_preference_memory`
- `memory_updated_at`

关键行为：

- 记忆是按“用户 + 角色”隔离的
- 不会在不同角色之间共享
- 不会在不同用户之间共享
- “重置聊天窗口”不等于“清空长期记忆”

## 诊断能力

当前系统已经提供轻量 AI 诊断，避免聊天链路完全黑盒。

当前可观测信息包括：

- 当前轮用了哪些 prompt layers
- 是否注入了记忆
- 是否触发了记忆刷新
- runtime 来源
- 是否走了 fallback
- Studio 可查看最近一次调试快照

## 评估

仓库中包含轻量的内部评估样例：

- [docs/ai_eval_cases.json](docs/ai_eval_cases.json)
- [scripts/run_ai_eval.py](scripts/run_ai_eval.py)

执行：

```bash
python3 scripts/run_ai_eval.py
```

会输出一份人工审阅清单，用于检查：

- 角色一致性
- 语音一致性
- 偏好记忆命中
- fallback 暴露是否正确

## 项目结构

```text
AIFriends/
├── backend/
│   ├── backend/          # Django 项目配置
│   ├── web/              # API、AI 服务、模型、视图
│   ├── media/            # 本地开发时的上传文件
│   └── manage.py
├── frontend/
│   ├── src/components/   # UI 组件
│   ├── src/views/        # 页面
│   ├── src/router/       # 前端路由
│   └── src/types/        # TypeScript 类型
├── docs/
│   ├── AI_OVERVIEW.md
│   └── ai_eval_cases.json
└── scripts/
    ├── dev.sh
    └── run_ai_eval.py
```

## 构建

前端生产构建：

```bash
npm run build
```

或者单独执行：

```bash
cd frontend
npm run type-check
npm run build-only
```

## 当前状态

已经完成并适合继续开发的部分：

- 基于 AI Studio 的创作者工作流
- 角色编辑与音色配置
- 试聊与诊断
- 结构化 prompt 组装
- 轻量长期记忆
- chat / ASR / TTS runtime summary
- 用户正式聊天页

当前仍然不是主线的方向：

- RAG
- 通用 Agent 能力
- 真实工具执行
- 复杂工作流自动化

## Roadmap

当前优先方向：

- 提升记忆刷新质量
- 增强角色一致性评估
- 强化 diagnostics 和 provider 兼容标签
- 提升创作者 Prompt 工程化体验
- 未来按需补角色知识增强

## 许可证

当前仓库还没有加入 `LICENSE` 文件。  
如果你准备把这个项目公开到 GitHub，建议在发布前补一个明确的开源许可证。
