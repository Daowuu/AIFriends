# AIFriends 平台功能总览

## 1. 项目定位

AIFriends 当前是一个基于 Vue 3 + Django 的 AI 角色与平台原型项目。

目前项目重点在两层：

- 平台层：导航、路由、登录态、资料管理、角色管理
- 数据层：用户资料、角色信息、好友关系、消息记录、媒体文件上传与访问

目前已经进入基础文字聊天阶段，但更高级的 agent 能力还没有接入。

---

## 2. 技术架构

### 前端

- Vue 3
- TypeScript
- Vite
- Vue Router
- Pinia
- Tailwind CSS v4
- daisyUI
- Axios
- Croppie

### 后端

- Django 4.2
- Django REST Framework
- SimpleJWT
- SQLite

### 运行结构

- 前端开发服务：`127.0.0.1:5173`
- 后端开发服务：`127.0.0.1:8000`
- Vite 将 `/api`、`/media` 代理到 Django
- 生产/本地整合模式下，Django 直接托管前端打包产物

---

## 3. 当前页面功能

## 首页 `/`

### 已实现

- 真实角色流
- 搜索角色
- URL query 与搜索框同步
- 流式加载更多角色
- 点击角色卡片打开聊天弹层
- 点击作者进入个人主页

### 当前用途

- 承接公开角色发现流

### 未实现

- 推荐排序
- 标签筛选
- 热榜

---

## 好友页 `/friends`

### 已实现

- 好友列表接口对接
- 真实好友角色卡片展示
- 删除好友
- 打开聊天弹层
- 查看历史消息
- 发送文字消息
- 流式接收角色回复
- 语音输入聊天

### 当前用途

- 管理已经添加的角色好友并继续对话

### 未实现

- 未读计数
- 在线状态
- 会话分组与最近联系人排序

---

## 创作工作区 `/workspace`

### 已实现

- 角色列表加载
- 角色卡片展示
- 进入角色编辑页
- 删除角色
- 新建角色入口

### 当前用途

- 作为角色资产管理中心

### 未实现

- 角色筛选
- 角色排序
- 草稿箱
- 批量管理

---

## 登录页 `/login`

### 已实现

- 用户名密码登录
- 错误提示
- 登录成功后进入登录态
- 支持登录后跳回原页面

### 未实现

- 忘记密码
- 验证码
- 第三方登录

---

## 注册页 `/register`

### 已实现

- 用户注册
- 两次密码校验
- 注册成功后自动进入登录态

### 未实现

- 邮箱/短信验证
- 用户协议确认
- 风控策略

---

## 资料编辑页 `/profile`

### 已实现

- 修改用户名
- 修改展示名
- 修改简介
- 修改头像
- 头像裁剪上传
- 保存成功后导航栏头像和昵称同步更新
- 前往模型 API 设置页

### 未实现

- 个性封面
- 社交链接
- 更多安全设置

---

## 模型 API 设置页 `/settings/api`

### 已实现

- 启用或关闭个人模型配置
- 选择模型提供方
- 填写 API Key
- 填写 API Base
- 填写模型名
- 查看当前解析后的实际配置
- 清空已保存密钥
- 测试当前配置是否连通

### 当前用途

- 管理当前登录用户自己的聊天模型配置

### 未实现

- 连通性测试
- 加密存储密钥
- 更多高级推理参数设置

---

## 创建角色页 `/characters/create`

### 已实现

- 输入角色名字
- 输入角色介绍
- 上传并裁剪角色头像
- 上传并裁剪聊天背景
- 提交创建角色

### 未实现

- 角色标签
- 公开/私密切换
- 开场白
- 示例对话
- 角色世界观扩展字段

---

## 编辑角色页 `/characters/:id/edit`

### 已实现

- 拉取单个角色详情
- 编辑角色名字
- 编辑角色介绍
- 替换头像
- 替换背景
- 删除角色

### 未实现

- 编辑历史
- 自动保存
- 版本回滚

---

## 个人主页 `/space/:id`

### 已实现

- 展示用户头像、昵称、用户名、简介
- 展示该用户的角色流
- 支持流式加载
- 如果是本人主页，则角色卡片支持编辑和删除

### 当前用途

- 承接“用户空间”和“作者主页”浏览

### 未实现

- 关注关系
- 主页动态
- 角色置顶

---

## 404 页面

### 已实现

- 路由兜底页面

---

## 4. 当前导航与平台壳子

### 左侧导航

- 首页
- 好友
- 创作

### 顶部区域

- 平台 Logo
- 搜索输入框
- 登录按钮或用户菜单

### 用户菜单

- 编辑资料
- 我的角色
- 退出登录

---

## 5. 当前用户系统

## 用户模型组成

- Django `User`
- `UserProfile`

## UserProfile 当前字段

- `display_name`
- `bio`
- `avatar`

## 当前登录态机制

- `access_token`：前端内存持有
- `refresh_token`：浏览器 Cookie 持有
- 页面刷新后自动尝试恢复登录态

## 当前权限控制

以下页面必须登录后访问：

- `/workspace`
- `/profile`
- `/settings/api`
- `/characters/create`
- `/characters/:id/edit`

---

## 6. 当前角色系统

## Character 当前字段

- `name`
- `profile`
- `photo`
- `background_image`
- `created_at`
- `updated_at`
- `user`

## 当前角色能力

- 每个角色归属于一个用户
- 用户只能管理自己的角色
- 支持创建、查看、更新、删除
- 支持在首页和个人主页中公开展示
- 支持被其他用户添加为好友
- 支持作为聊天对象参与文字对话

## 当前角色展示形式

- 工作区卡片列表
- 角色头像
- 背景图
- 简介摘要
- 最近更新时间

---

## 7. 当前接口清单

## 用户认证

- `POST /api/user/account/login/`
- `POST /api/user/account/register/`
- `POST /api/user/account/logout/`
- `POST /api/user/account/refresh_token/`
- `GET /api/user/account/get_user_info/`

## 用户资料

- `POST /api/user/profile/update/`

## 用户模型设置

- `GET /api/user/settings/ai/`
- `POST /api/user/settings/ai/`
- `POST /api/user/settings/ai/test/`

## 角色

- `GET /api/create/character/list/`
- `POST /api/create/character/create/`
- `GET /api/create/character/<id>/`
- `POST /api/create/character/<id>/update/`
- `POST /api/create/character/<id>/remove/`

## 公开角色流与个人主页

- `GET /api/homepage/index/`
- `GET /api/user/space/<id>/`

## 好友

- `POST /api/friend/get_or_create/`
- `POST /api/friend/remove/`
- `GET /api/friend/list/`

## 聊天

- `GET /api/friend/message/history/`
- `POST /api/friend/message/chat/`

---

## 8. 当前聊天系统

## 当前已实现

- 文本消息持久化
- 聊天历史分页加载
- SSE 流式回复
- 角色级系统提示词
- 最近 10 条消息短期记忆
- 未配置模型 API 时的本地回退回复
- 用户级模型 API 配置
- 新消息自动打断上一条回复
- 语音输入模式
- 浏览器语音播报

## 当前模型与配置

- 支持通过 `backend/.env` 配置外部兼容 OpenAI 的模型服务
- 支持通过用户设置页覆盖默认环境配置
- 当前示例配置文件：`backend/.env.example`
- 默认示例模型名：`qwen-plus`
- 当前内置预设：阿里云百炼、DeepSeek、MiniMax、OpenAI、自定义兼容接口
- 支持测试当前表单配置是否可连通
- 支持给自己的角色自动创建聊天会话

## 当前聊天数据模型

- `Friend`：定义用户与角色的会话关系
- `Message`：保存用户消息和角色回复
- `SystemPrompt`：保存聊天系统提示词模板
- `UserAISettings`：保存用户自己的模型 API 配置

## 当前未实现

- 图片消息
- 消息撤回
- 未读状态
- function call
- 长期记忆
- 知识库检索
- 服务端流式 TTS 音频

---

## 9. 当前语音模块

## 当前已实现

- 文字 / 语音输入切换
- `vad-web` 人声检测
- 音浪动画反馈
- 前端录音后上传音频到后端 ASR
- 阿里云百炼 `qwen3-asr-flash` 语音识别
- 浏览器 `speechSynthesis` 播放角色回复
- 关闭聊天框后自动停止监听和播报

## 当前配置要求

- 前端 `vad` 静态资源位于 `frontend/public/vad/`
- 本地或服务端需要正确返回 `.mjs`、`.wasm`、`.onnx` 的 MIME 类型
- 若要使用后端 ASR，需提供阿里云百炼配置
- 设置页支持单独保存 ASR 的 `API Key`、`API Base`、`Model`
- 可单独配置：
  - `ASR_API_KEY`
  - `ASR_API_BASE`

## 当前限制

- 当前 ASR 只支持阿里云百炼兼容接口
- 当前 TTS 先使用浏览器能力，不走服务端
- 还没有音色选择、语速、音量等高级控制

---

## 10. 当前媒体处理能力

### 已实现

- 用户头像上传
- 角色头像上传
- 角色背景图上传
- 前端裁剪后转文件上传
- 更新图片时删除旧文件

### 当前实现特点

- 当前使用 `FileField`
- 当前未做严格图片类型校验
- 当前未压缩图片体积

---

## 11. 当前开发与构建方式

## 一键启动

在项目根目录执行：

```bash
npm run dev
```

## 单独启动

```bash
npm run backend
npm run frontend
```

## 打包

```bash
npm run build
```

前端打包后产物会进入 Django 静态目录，由 Django 托管。

---

## 12. 当前平台能力边界

以下能力已经具备基础雏形：

- 平台主界面
- 登录与注册
- 用户资料编辑
- 角色创建与编辑
- 首页角色发现流
- 用户个人主页
- 好友角色列表
- 文字聊天与消息记录
- 语音输入与浏览器语音播报
- 本地媒体文件存储

以下能力尚未开始或仍是占位：

- 角色广场
- 推荐流
- 评论、点赞、收藏
- 搜索服务
- 审核与风控

---

## 13. 文档维护要求

以后每次功能迭代，需要同步更新两份文档：

- [ITERATION_LOG.md](/Users/apple/project/AIFrients/docs/ITERATION_LOG.md)
- [PLATFORM_FUNCTIONS.md](/Users/apple/project/AIFrients/docs/PLATFORM_FUNCTIONS.md)

要求：

- 迭代日志记录“这次改了什么”
- 平台总览记录“平台现在能做什么”
- 新增页面、接口、数据模型时必须同步更新
