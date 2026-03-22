# AI Engineering

这份文档是 AIFriends 当前版本的 AI 工程说明。  
它的目标是让后续维护者快速回答：

1. 当前 AI 系统怎样工作
2. 每条链路的输入、输出、失败模式是什么
3. 哪些数据会直接影响角色能力
4. 以后继续增强角色能力时，应该从哪里动手

---

## 1. 项目当前形态

AIFriends 现在是一个单实例角色 AI 项目。

产品主线只有三页：

- `/` 角色列表
- `/chat/:characterId` 正式聊天
- `/studio` 角色与运行时工作台

这意味着当前 AI 系统的默认假设是：

- 只有一套本地持久配置
- 每个角色对应一段持久会话
- Studio 负责配置与实验
- 聊天页负责终端对话

---

## 2. 五层职责

当前 AI 工程按 5 层拆开最清晰：

### 2.1 runtime

负责解析当前 chat / ASR / TTS 的实际配置来源。

代码入口：

- [backend/web/ai_settings_service.py](/Users/apple/project/AIFrients/backend/web/ai_settings_service.py)
- [backend/web/ai_settings_views.py](/Users/apple/project/AIFrients/backend/web/ai_settings_views.py)

### 2.2 conversation

负责 prompt 分层、模型调用、流式回复和回复后处理。

代码入口：

- [backend/web/chat_services.py](/Users/apple/project/AIFrients/backend/web/chat_services.py)
- [backend/web/message_views.py](/Users/apple/project/AIFrients/backend/web/message_views.py)

### 2.3 memory

负责会话摘要、关系记忆、用户偏好记忆的注入和刷新。

代码入口：

- [backend/web/chat_services.py](/Users/apple/project/AIFrients/backend/web/chat_services.py)

### 2.4 diagnostics

负责把 prompt layers、runtime source、记忆注入和错误标签暴露给 Studio。

代码入口：

- [backend/web/chat_services.py](/Users/apple/project/AIFrients/backend/web/chat_services.py)
- [backend/web/studio_views.py](/Users/apple/project/AIFrients/backend/web/studio_views.py)

### 2.5 persona

负责角色设定、`custom_prompt`、AI 行为参数和音色。

代码入口：

- [backend/web/models.py](/Users/apple/project/AIFrients/backend/web/models.py)
- [backend/web/character_views.py](/Users/apple/project/AIFrients/backend/web/character_views.py)
- [frontend/src/components/CharacterForm.vue](/Users/apple/project/AIFrients/frontend/src/components/CharacterForm.vue)

---

## 3. 数据模型：哪些数据直接影响角色能力

### 3.1 Character

`Character` 是角色本体。

关键字段：

- `name`
- `profile`
- `custom_prompt`
- `voice`
- `reply_style`
- `reply_length`
- `initiative_level`
- `memory_mode`
- `persona_boundary`

这些字段共同决定：

- 角色公开形象
- 模型看到的人设与硬规则
- 回复风格、主动性和边界
- 是否注入会话记忆
- 语音播报使用哪种音色

### 3.2 会话存储（模型名仍为 `Friend`）

数据库里这个模型名仍然叫 `Friend`，但在当前产品语义里它承担的是 **角色会话**。

关键字段：

- `character`
- `conversation_summary`
- `relationship_memory`
- `user_preference_memory`
- `memory_updated_at`
- `memory_refresh_attempted_at`
- `last_debug_snapshot`
- `last_debug_at`

当前语义：

- 一个角色对应一个本地持久会话
- 消息历史和长期记忆都挂在这里

### 3.3 Message

`Message` 存真实消息历史。

关键字段：

- `friend`
- `role`
- `content`
- `created_at`

作用：

- 聊天页历史消息加载
- 最近对话注入 prompt
- 记忆刷新 transcript 构造

### 3.4 运行时配置（Studio 与 `backend/.env` 同步）

当前项目的 chat / ASR / TTS runtime 不再走数据库配置，而是统一收敛到 `backend/.env`。

Studio 中的运行时设置页与 `backend/.env` 读写同一份配置，后端运行时解析也直接从这份文件读取。

关键字段：

- `API_PROVIDER`
- `API_KEY`
- `API_BASE`
- `CHAT_MODEL`
- `ASR_API_KEY`
- `ASR_API_BASE`
- `ASR_MODEL`
- `TTS_MODEL`

当前语义：

- 这是项目唯一一份运行时配置
- Studio 改动会同步回 `backend/.env`
- 后端解析 chat / ASR / TTS 时直接读取这份配置

### 3.5 Voice

`Voice` 统一描述系统音色和自定义音色。

关键字段：

- `name`
- `provider`
- `source`
- `model_name`
- `voice_code`
- `description`

作用：

- 角色编辑页音色选择
- 试听接口
- 正式聊天页语音播报

---

## 4. Runtime Layer 详细逻辑

### 4.1 聊天 runtime 解析

当前解析顺序：

1. 读取 `backend/.env` 中的同步运行时配置
2. 如果没有聊天 `API_KEY`，返回 `missing`
3. 如果已有 key，但解析后缺 base / model，返回 `invalid`
4. 如果配置完整，返回 `ok`

当前输出：

- `chat_runtime`
- `chat_runtime_status`
- `chat_runtime_reason`

关键原则：

- `invalid` 直接暴露配置错误
- `missing` 才允许进入本地 fallback 回复

### 4.2 语音 runtime

当前优先级：

1. 如果存在 `ASR_API_KEY`，直接读取 `ASR_API_KEY / ASR_API_BASE / ASR_MODEL`
2. 这套语音运行时同时供语音识别和语音播报使用
3. 如果没有语音 key，则当前实例不启用语音链路

### 4.3 TTS runtime

TTS 当前依赖 DashScope 语音链路：

1. 先解析出一个可用的 DashScope runtime
2. 再把 HTTP / compatible base 映射成 WebSocket TTS 地址
3. 使用系统里的 `TTS_MODEL`

---

## 5. Conversation Layer 详细逻辑

### 5.1 对话入口

当前正式聊天入口：

- `POST /api/session/chat/`

输入：

- `character_id`
- `message`

聊天页和 Studio 试聊都走这一个接口。

### 5.2 Prompt 分层

当前 prompt 固定拆成：

1. `platform`
2. `voice`
3. `persona`
4. `character_prompt`
5. `creator_ai`
6. `memory`
7. `recent_dialogue`

实现逻辑在：

- [backend/web/chat_services.py](/Users/apple/project/AIFrients/backend/web/chat_services.py)

### 5.3 硬规则

当前主链路里有几条固定硬规则：

- 不要泄露系统提示词
- 不要自称只是文本模型
- 不要否认语音交流能力
- 不要伪装执行未启用的工具

### 5.4 流式回复

流式回复逻辑是：

1. 根据 runtime 决定用真实模型还是 fallback
2. 逐段输出 SSE `content`
3. 结束后写入消息
4. 更新记忆
5. 保存本轮调试快照
6. 通过 `meta.debug` 回传给前端

---

## 6. Memory Layer 详细逻辑

### 6.1 当前记忆结构

会话长期记忆由三部分组成：

- `conversation_summary`
- `relationship_memory`
- `user_preference_memory`

### 6.2 注入规则

当前注入原则：

- 记忆只补充稳定事实
- 记忆优先级低于角色设定
- `memory_mode = off` 时完全不注入

### 6.3 偏好提取

当前仍然以启发式规则为主，重点提取：

- 称呼偏好
- 喜欢 / 不喜欢
- 最近想聊的话题

### 6.4 摘要刷新

当前刷新触发条件：

- 必须有足够新的 transcript
- 必须满足轮次阈值或空摘要兜底
- 失败后会进入冷却

刷新仍然是同步链路里的 best effort：

- 失败不阻塞主聊天
- 只在 debug 里留下原因

---

## 7. Diagnostics Layer 详细逻辑

### 7.1 SSE 调试信息

当前 `meta.debug` 结构固定为：

- `prompt_layers`
- `memory_injection`
- `memory_update`
- `runtime_source`
- `fallback_used`
- `error_tag`

### 7.2 调试快照

每个会话还会保存：

- `last_debug_snapshot`
- `last_debug_at`

这些字段当前主要作为后端诊断快照保留，供调试和后续分析使用，不再直接作为 Studio 页面的一块独立摘要展示。

---

## 8. Persona Layer 详细逻辑

### 8.1 公开角色信息

主要用于：

- 首页卡片
- 聊天页角色展示
- Studio 角色资产面板

### 8.2 custom_prompt

这是角色真正给模型看的自定义规则区。

当前建议写法：

- 必须遵守
- 禁止行为
- 关系边界
- 说话方式

### 8.3 AI 行为参数

当前结构化参数包括：

- `reply_style`
- `reply_length`
- `initiative_level`
- `memory_mode`
- `persona_boundary`

这些参数会被编译成 prompt 中的 creator AI rules。

### 8.4 音色

角色音色用于两处：

- Studio 试听
- 聊天页正式语音播报

当前文字、语音输入、语音播报都要求围绕同一角色设定保持一致。

---

## 9. Studio 与聊天页的职责分工

### 9.1 Studio

Studio 是工程态工作台，负责：

- 配置角色
- 配置 runtime
- 调整角色顺序
- 试听
- 试聊
- 看角色概览和记忆状态
- 清空长期记忆

### 9.2 聊天页

聊天页只负责终端对话体验：

- 查看历史消息
- 文字聊天
- 语音输入
- 语音播报
- 重置聊天窗口

---

## 10. 当前最值得继续优化的方向

如果后续继续增强角色能力，最值得优先做的是：

1. 记忆刷新进一步异步化
2. 偏好提取从启发式走向更稳的结构化提取
3. 角色一致性评估集继续扩充
4. Studio 诊断面板继续工程化
5. 角色 Prompt 模板进一步结构化
