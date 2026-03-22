# AI Overview

这份文档的作用是先回答三个问题：

1. AIFriends 的 AI 主线是什么
2. 当前 AI 系统由哪些层组成
3. 接下来应该先读哪份文档

## 1. AI 主线

AIFriends 当前围绕四件事持续增强：

- 角色一致性
- 关系记忆
- 语音一致性
- 创作者控制

这些能力共同服务于一个目标：让角色在长期对话里保持稳定、记得关系、在文字和语音场景下表现一致，并且让创作者能够持续调校角色行为。

## 2. 五层结构

当前 AI 工程按 5 层理解最清晰：

1. `runtime`
   解析当前 chat / ASR / TTS 实际由谁运行。
2. `conversation`
   负责 prompt 分层、模型调用、流式回复和回复后处理。
3. `memory`
   负责会话摘要、关系记忆、用户偏好记忆。
4. `diagnostics`
   负责暴露 prompt layers、runtime 来源、记忆注入和错误标签。
5. `persona`
   负责角色设定、创作者 AI 配置和角色行为边界。

## 3. 当前工程重点

当前工程重点集中在：

- prompt 结构化
- 轻量记忆质量
- 语音链路一致性
- runtime 透明性
- Studio 创作者工作流

## 4. 阅读顺序

建议按下面的顺序阅读：

1. [README](../README.md)
   先看启动方式、主要路由和最小配置。
2. [AI Engineering](./AI_ENGINEERING.md)
   再看完整的实现逻辑、数据模型和失败模式。
3. [Platform Functions](./PLATFORM_FUNCTIONS.md)
   最后看当前产品表面的页面职责和创作者路径。
4. [Iteration Log](./ITERATION_LOG.md)
   如果需要理解历史演进，再查这份档案。

## 5. 这份文档适合什么时候看

- 想快速知道项目 AI 重点时
- 想知道完整工程文档该从哪里读起时
- 想先建立整体框架，再进入实现细节时
