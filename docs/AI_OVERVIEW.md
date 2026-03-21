# AI Overview

这份文档只总结项目中和 AI 直接相关的部分，方便后续单独维护、排查和扩展。

## 1. 当前 AI 能力

项目里已经接入的 AI 能力主要有 4 类：

1. 聊天模型
- 角色对话走兼容 OpenAI Chat Completions 的接口
- 当前支持的 provider：
  - 阿里云百炼
  - DeepSeek
  - MiniMax
  - OpenAI
  - 自定义兼容 OpenAI 接口

2. 角色系统提示词
- 每次聊天都会构造角色专属 system prompt
- 包含角色名、角色设定、作者、语音约束
- 支持数据库中的系统提示词模板

3. 语音识别 ASR
- 前端录音后上传音频到后端
- 后端当前只接阿里云百炼兼容 ASR
- 默认模型：`qwen3-asr-flash`

4. 语音播报 TTS
- 角色回复后可请求后端 TTS 音频
- 后端当前接阿里云 CosyVoice
- 支持系统音色和自定义 `voice_id`
- 如果服务端 TTS 失败，前端仍有浏览器 `speechSynthesis` 兜底

## 2. 后端 AI 相关模型

文件：
- [models.py](/Users/apple/project/AIFrients/backend/web/models.py)

核心模型：

1. `SystemPrompt`
- 用于保存聊天系统提示词模板
- 当前角色聊天使用的 key 是 `character_chat`

2. `UserAISettings`
- 保存每个用户自己的 AI 配置
- 主要字段：
  - `enabled`
  - `provider`
  - `api_key`
  - `api_base`
  - `model_name`
  - `asr_enabled`
  - `asr_api_key`
  - `asr_api_base`
  - `asr_model_name`

3. `Voice`
- 保存角色可用音色
- 主要字段：
  - `provider`
  - `source`
  - `model_name`
  - `voice_code`
  - `description`
  - `language`
  - `is_active`

4. `Character.voice`
- 角色和音色关联
- 决定 TTS 时使用哪个音色

## 3. 聊天模型链路

文件：
- [chat_services.py](/Users/apple/project/AIFrients/backend/web/chat_services.py)
- [message_views.py](/Users/apple/project/AIFrients/backend/web/message_views.py)
- [ai_settings_service.py](/Users/apple/project/AIFrients/backend/web/ai_settings_service.py)

### 3.1 运行时模型配置

`get_runtime_ai_config(user)` 的优先级：

1. 用户设置页里启用的聊天模型配置
2. 服务端环境变量：
  - `API_KEY`
  - `API_BASE`
  - `CHAT_MODEL`

### 3.2 聊天请求流程

接口：
- `POST /api/friend/message/chat/`

流程：

1. 前端发送 `friend_id + message`
2. 后端根据角色构造聊天 messages
3. 注入角色专属 system prompt
4. 使用兼容 OpenAI 的流式聊天接口返回 SSE
5. 回复结束后写入 `Message`

### 3.3 角色 system prompt

`build_system_prompt(friend)` 当前会拼接：

- 平台级 system prompt
- 运行时语音规则
- 角色名
- 角色设定
- 语音设定
- 作者

补充说明：
- 当前已经显式约束模型不要说自己“不能语音”“只是文本模型”
- 这个约束是运行时直接拼进去的，不依赖数据库默认值是否更新

### 3.4 think 过滤

聊天链路会过滤 `<think>...</think>`，避免推理内容显示到前端。

## 4. 用户 AI 设置

文件：
- [ai_settings_service.py](/Users/apple/project/AIFrients/backend/web/ai_settings_service.py)
- [ai_settings_views.py](/Users/apple/project/AIFrients/backend/web/ai_settings_views.py)
- [ApiSettingsView.vue](/Users/apple/project/AIFrients/frontend/src/views/ApiSettingsView.vue)

### 4.1 聊天模型设置

设置页支持：
- 单独启用聊天模型配置
- 选择 provider
- 配置 `API Key / API Base / Model`
- 测试聊天模型连接

默认 provider 预设：
- 阿里云百炼
- DeepSeek
- MiniMax
- OpenAI
- 自定义兼容接口

### 4.2 ASR 设置

设置页支持：
- 单独启用 ASR 配置
- 配置 `ASR API Key / API Base / Model`
- 测试 ASR 连接

当前 ASR 默认值：
- `ASR_API_BASE = https://dashscope.aliyuncs.com/compatible-mode/v1`
- `ASR_MODEL = qwen3-asr-flash`

### 4.3 DashScope 复用规则

`get_dashscope_runtime_config(user)` 当前优先级：

1. 用户单独保存的 ASR 配置
2. 用户聊天配置中可识别为 DashScope 的聊天配置
3. 服务端环境变量：
  - `ASR_API_KEY`
  - `ASR_API_BASE`
  - `ASR_MODEL`
  - 或回退到 `API_KEY / API_BASE`

## 5. 语音识别 ASR

文件：
- [asr_views.py](/Users/apple/project/AIFrients/backend/web/asr_views.py)
- [InputField.vue](/Users/apple/project/AIFrients/frontend/src/components/character/chat_field/input_field/InputField.vue)

接口：
- `POST /api/friend/message/asr/`

流程：

1. 前端录音或 VAD 截取音频
2. 前端把音频转成 `data:audio/...` Data URL
3. 后端用兼容 OpenAI 的方式请求阿里云 ASR
4. 返回识别文本
5. 前端再把文本作为聊天消息发给聊天接口

前端语音输入当前支持：
- 实时 VAD 自动断句
- 手动录音
- 麦克风设备选择
- 麦克风可用性探测
- 过滤 Continuity / iPhone 这类不稳定设备

## 6. 语音播报 TTS

文件：
- [tts_views.py](/Users/apple/project/AIFrients/backend/web/tts_views.py)
- [ChatField.vue](/Users/apple/project/AIFrients/frontend/src/components/character/chat_field/ChatField.vue)

接口：
- `POST /api/friend/message/tts/`
- `POST /api/create/character/voice/preview/`

### 6.1 实际对话 TTS

`/api/friend/message/tts/` 用于角色正式回复后的语音播报。

逻辑：

1. 根据 `friend_id` 找到角色
2. 解析角色音色
3. 获取 DashScope 运行时配置
4. 调用 CosyVoice 合成音频
5. 返回 `audio/mpeg`

### 6.2 音色试听

`/api/create/character/voice/preview/` 用于创建/编辑角色时试听音色，不要求先保存角色。

### 6.3 前端播放策略

前端 `speakReply()` 当前优先级：

1. 优先请求后端 TTS 音频
2. 后端失败时回退浏览器 `speechSynthesis`

另外前端已经处理了：
- 播报时暂停实时监听
- 播报结束恢复监听
- 避免角色语音被再次识别成用户输入

## 7. 角色音色体系

文件：
- [character_views.py](/Users/apple/project/AIFrients/backend/web/character_views.py)
- [CharacterForm.vue](/Users/apple/project/AIFrients/frontend/src/components/CharacterForm.vue)
- [CreateCharacterView.vue](/Users/apple/project/AIFrients/frontend/src/views/CreateCharacterView.vue)
- [UpdateCharacterView.vue](/Users/apple/project/AIFrients/frontend/src/views/UpdateCharacterView.vue)

### 7.1 系统音色

通过迁移预置了一批系统音色，存储在 `Voice` 表中。

### 7.2 自定义音色

用户可以填写：
- 自定义音色名
- 自定义 `voice_id`
- 对应模型名
- 描述

本质上就是把阿里云返回的 `voice_id` 保存为 `Voice(source='custom')`。

### 7.3 角色音色管理接口

接口：
- `GET /api/create/character/voice/list/`
- `POST /api/create/character/voice/save/`
- `POST /api/create/character/voice/<voice_id>/remove/`
- `POST /api/create/character/voice/preview/`

## 8. 前端 AI 相关组件

### 8.1 聊天页

文件：
- [ChatView.vue](/Users/apple/project/AIFrients/frontend/src/views/ChatView.vue)
- [ChatField.vue](/Users/apple/project/AIFrients/frontend/src/components/character/chat_field/ChatField.vue)

负责：
- 独立聊天页
- 加载角色详情
- 自动建会话
- 渲染消息、输入区、语音播报

### 8.2 语音输入组件

文件：
- [InputField.vue](/Users/apple/project/AIFrients/frontend/src/components/character/chat_field/input_field/InputField.vue)

负责：
- 文字/语音模式切换
- 实时监听
- 手动录音
- 麦克风设备管理
- ASR 上传

### 8.3 角色音色配置组件

文件：
- [CharacterForm.vue](/Users/apple/project/AIFrients/frontend/src/components/CharacterForm.vue)

负责：
- 角色音色选择
- 自定义音色录入
- 音色试听

## 9. AI 相关接口清单

### 聊天
- `POST /api/friend/message/chat/`
- `GET /api/friend/message/history/`

### 语音识别
- `POST /api/friend/message/asr/`
- `POST /api/user/settings/ai/test_asr/`

### 语音播报
- `POST /api/friend/message/tts/`
- `POST /api/create/character/voice/preview/`

### AI 设置
- `GET/POST /api/user/settings/ai/`
- `POST /api/user/settings/ai/test/`

### 音色管理
- `GET /api/create/character/voice/list/`
- `POST /api/create/character/voice/save/`
- `POST /api/create/character/voice/<voice_id>/remove/`

## 10. 当前边界与限制

1. 聊天模型
- 只支持兼容 OpenAI Chat Completions 的聊天接口

2. ASR
- 当前只支持阿里云百炼兼容接口

3. TTS
- 当前只接阿里云 CosyVoice
- 角色音色依赖 `Voice.model_name + Voice.voice_code`

4. 自定义音色
- 当前支持“填写已有 `voice_id`”
- 还没有在项目内完成“上传音频直接创建复刻音色”的完整闭环

5. 前端语音
- 仍然受浏览器权限、HTTPS、安全上下文、系统麦克风路由影响

## 11. 最值得继续扩展的方向

1. 在项目内直接接入“声音复刻创建音色”
2. 把音色管理单独做成管理页
3. 增加更多 AI 行为配置：
- 回复风格
- 记忆策略
- 安全策略
- 多 system prompt 模板
4. 进一步拆分前端语音模块，降低主包体积
