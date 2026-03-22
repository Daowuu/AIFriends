# AI Overview

这是一页导航文档，只回答三件事：

1. AIFriends 当前在做什么 AI 能力
2. 这些能力按什么层次理解最清楚
3. 详细实现应该去哪看

## 1. 当前 AI 主线

AIFriends 当前把 AI 能力集中在：

- 角色一致性
- 会话记忆
- 语音一致性
- 运行时透明性
- 创作者可控的角色调校

项目的产品主线是：

`角色列表 -> Studio 配置与试聊 -> 正式聊天`

## 2. 五层结构

当前 AI 工程按 5 层理解最清晰：

1. `runtime`
   负责解析 chat / ASR / TTS 当前实际使用的配置来源。
2. `conversation`
   负责 prompt 分层、模型调用、流式回复和回复后处理。
3. `memory`
   负责会话摘要、关系记忆、用户偏好记忆。
4. `diagnostics`
   负责 prompt layers、runtime source、记忆注入和错误标签。
5. `persona`
   负责角色设定、`custom_prompt`、AI 行为配置和音色。

## 3. 建议阅读顺序

1. [README](../README.md)
   先看怎么启动，以及产品表面有哪些入口。
2. [AI Engineering](./AI_ENGINEERING.md)
   再看完整实现逻辑、数据结构和失败模式。
3. [Platform Functions](./PLATFORM_FUNCTIONS.md)
   最后看当前 UI 层的页面职责和工作流。
4. [Iteration Log](./ITERATION_LOG.md)
   如果需要理解历史演进，再查这份档案。
