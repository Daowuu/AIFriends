# AI Overview

AIFriends 的 AI 主线很明确：持续增强 **角色一致性、关系记忆、语音一致性、创作者控制**。

当前项目最重要的 AI 问题是：

- 角色能否长期稳定地像自己
- 角色能否记住用户和关系状态
- 语音输入、文字输入、语音播报能否共享同一套角色逻辑
- 创作者能否稳定控制角色行为
- 运行时与失败原因能否被清楚诊断

## AI 分层

当前 AI 工程按 5 层理解：

1. `runtime`
   解析这一轮 chat / ASR / TTS 到底由谁在运行，以及为什么这样判定。
2. `conversation`
   负责 prompt 分层组装、模型调用、流式回复和回复后处理。
3. `memory`
   负责会话摘要、关系记忆、用户偏好记忆的注入与刷新。
4. `diagnostics`
   负责暴露 prompt layers、记忆注入、fallback、runtime 来源和错误原因。
5. `persona`
   负责角色本体设定、创作者 AI 配置和角色行为边界。

## 当前策略

- 优先优化 prompt 结构、轻量记忆、语音一致性和运行时透明性
- 让 Studio 成为创作者侧的试聊、试听和诊断入口
- 以角色聊天、关系连续和创作者工作流为核心演进方向

## 文档入口

- 完整 AI 工程文档：
  [AI Engineering](./AI_ENGINEERING.md)
- 仓库入口说明：
  [README](../README.md)
- 中文仓库说明：
  [README.zh-CN](../README.zh-CN.md)

## 适合从哪里开始读

- 想快速理解项目 AI 目标：先看这份 Overview
- 想理解实现逻辑和失败模式：看 [AI Engineering](./AI_ENGINEERING.md)
- 想启动项目和查看开发方式：看 README
