# AIFriends

[English](README.md) | [简体中文](README.zh-CN.md)

AIFriends 是一个单实例的角色 AI 聊天项目，核心关注四件事：

- 角色一致性
- 持久会话记忆
- 文字与语音共用同一套角色逻辑
- 轻量的多角色实验能力

产品主线现在保留四页：

- `/` 角色列表
- `/chat/:characterId` 聊天页
- `/studio` 角色与运行时工作台
- `/werewolf` 狼人杀原型页

## 快速开始

建议环境：

- Python `3.12+`
- Node `20+`

### 1. 克隆并安装依赖

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

### 2. 配置运行时文件

编辑：

- [backend/.env](/Users/apple/project/AIFrients/backend/.env)

`/studio` 里的运行时设置会直接读取并回写这同一份文件。

## 最小配置

最重要的变量：

```env
API_PROVIDER="aliyun"
API_KEY=""
API_BASE="https://dashscope.aliyuncs.com/compatible-mode/v1"
CHAT_MODEL="qwen-plus"

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

### 3. 迁移并运行项目

终端 1：

```bash
source .venv/bin/activate
python3 backend/manage.py migrate
python3 backend/manage.py runserver
```

终端 2：

```bash
cd frontend
npm run dev -- --host 127.0.0.1
```

默认地址：

- 后端：`http://127.0.0.1:8000`
- 前端：`http://127.0.0.1:5173`

如果你已经在仓库根目录装好了前端依赖，也可以直接：

```bash
npm run dev
```

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
3. 如果需要，可以在 Studio 顶部拖动角色切换条来调整顺序
4. 在 `角色概览` 中检查角色资产、记忆状态和当前运行时摘要
5. 在同一处调整 chat / ASR / TTS 运行时
6. 先试聊、试听
7. 再进入 `/chat/:characterId` 做正式对话
8. 如果想做多角色实验，可以进入 `/werewolf` 创建一局基础狼人杀

## 如何使用示例角色

如果你想快速体验完整工作流，最简单的方式是：

1. 打开 `/studio`
2. 进入 `角色配置`
3. 点击 `填入爱莉希雅示例`
4. 检查自动填入的角色介绍、Prompt、AI 参数、音色草稿、头像和背景图
5. 保存角色
6. 再去 `角色概览`、`试聊诊断` 或 `/chat/:characterId`

这个按钮的作用不是只填名字，而是一次性补齐三步配置，适合拿来快速启动一个可用角色。

## 项目截图

### 聊天页

![聊天页](docs/assets/readme/chat.png)

### Studio

![Studio](docs/assets/readme/studio.png)

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
