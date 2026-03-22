# Discussion Engineering

这份文档描述当前讨论组系统的工程实现。

目标只有两个：

1. 让维护者快速理解“讨论组为什么能跑起来”
2. 让后续改动不会把已经踩过的坑重新踩一遍

当前实现对应的核心代码：

- `backend/web/discussion_services.py`
- `backend/web/discussion_dag.py`
- `backend/web/dag_runtime.py`
- `backend/web/discussion_views.py`
- `frontend/src/views/DiscussionView.vue`
- `frontend/src/types/discussion.ts`

---

## 1. 系统定位

讨论组不是自由聊天，也不是狼人杀残留逻辑。

它现在是一个“主持驱动的多角色结构化讨论系统”：

- 用户提供一个主题
- 选择 2 到 8 个角色
- 第一个角色固定担任主持人
- 后端按 DAG 节点逐步推进讨论
- 每次 `advance` 只执行一个节点
- 讨论最终收束为共识结论

设计重点不是“让模型自由发挥”，而是：

- 用流程骨架约束讨论顺序
- 用受控上下文约束每段发言依赖
- 用质量闸门阻断模板废话
- 用显式失败暴露真实问题，而不是用 fallback 抹平问题

### 1.1 为什么这套逻辑看起来复杂

它复杂，不是因为“想做得花”，而是因为讨论组同时踩中了 4 类问题：

1. 多角色顺序依赖
2. 结构化主持流程
3. 模型输出不稳定
4. 本地 SQLite 锁粒度很粗

如果只是单角色聊天，很多复杂度可以不要。

但讨论组一旦要求：

- 第一个角色主持
- 一轮一轮推进
- 角色不能偷看未来发言
- 失败不能用模板糊过去
- 还要能暂停、重试、回放

就不可能只靠一条 prompt 或一个简单状态机解决。

所以当前复杂度主要来自三个地方：

- DAG：负责顺序和依赖
- 状态对象：负责把讨论上下文落库
- 失败机制：负责把真实问题暴露出来

这三层是必要复杂度。

相反，下面这些属于应该持续压缩的复杂度：

- 过重的结构化 schema
- 过死的文本字面对齐校验
- 过粗的敏感词拦截
- 前端把结构化 payload 和正文混着展示

---

## 2. 主要对象

### 2.1 房间模型

当前讨论组仍复用旧房间表：

- `WerewolfGame`
- `WerewolfSeat`
- `WerewolfEvent`
- `WerewolfSpeech`

语义已经变成：

- `WerewolfGame`：讨论房间
- `WerewolfSeat`：参与角色快照
- `WerewolfEvent`：流程节点和系统事件
- `WerewolfSpeech`：公开舞台发言回放，既包含普通角色发言，也包含主持人公开发言

这是存储层复用，不是业务语义复用。

### 2.2 主持人规则

主持人不是隐藏系统角色。

当前规则：

- 第一个选中的角色就是主持人
- 主持人会出现在参与者列表里
- 主持节点使用该角色自己的 `profile + custom_prompt`
- 普通发言轮中，主持人不进入普通发言队列

这个约束来自用户需求，不能再退回“系统隐藏主持人”。

---

## 3. 接口层

现有 REST 路由：

- `GET /api/discussion/groups/`
- `POST /api/discussion/groups/create/`
- `GET /api/discussion/groups/<id>/`
- `POST /api/discussion/groups/<id>/advance/`
- `POST /api/discussion/groups/<id>/reset/`
- `POST /api/discussion/groups/<id>/remove/`
- `DELETE /api/discussion/groups/<id>/remove/`

外部接口保持简单，所有复杂性都压在服务层。

`advance` 的语义必须始终保持：

- 一次只执行一个 ready node
- 如果当前节点失败，则返回失败，不继续推进后继节点

---

## 4. 状态模型

讨论组的运行时状态存放在 `group.state` 中。

关键字段：

- `mode`
- `topic`
- `max_rounds`
- `moderator_seat_id`
- `discussion_plan`
- `stance_map`
- `consensus_state`
- `dag_runtime`
- `runtime_status`
- `failed_node`
- `last_failure`

### 4.1 discussion_plan

表示“当前讨论计划”。

字段：

- `current_stage`
- `current_stage_label`
- `current_round`
- `agenda_items`
- `round_goal`
- `focus_points`
- `moderator_question`

作用：

- 给前端当前阶段说明
- 给后续节点提供受控上下文
- 避免模型每轮重新发明讨论目标

### 4.2 stance_map

表示“每个角色当前立场和贡献”。

字段：

- `participant_id`
- `participant_name`
- `stance_label`
- `confidence`
- `summary`
- `contribution`
- `last_round`

作用：

- 聚焦轮排序
- 主持总结时抽取争议
- 判断某个角色是否已经有明确贡献

### 4.3 consensus_state

表示当前已形成的结论状态。

字段：

- `resolved_points`
- `open_questions`
- `consensus_draft`
- `final_summary`

作用：

- 主持总结累积可复用结果
- 共识草案节点直接读写这份状态
- 结束节点据此生成最终结果

### 4.4 failure state

失败态不是异常日志，而是产品态。

字段：

- `runtime_status`
- `failed_node`
- `last_failure`

当前约定：

- `runtime_status=ready`：可继续推进
- `runtime_status=blocked`：当前节点失败，房间暂停

这套状态必须持久化，不能只存在内存里。

---

## 5. DAG 运行时

通用 DAG 内核在 `backend/web/dag_runtime.py`。

它不懂“讨论组”，只懂：

- 节点
- 边
- ready / waiting / completed / failed
- 单步执行

运行时字段：

- `graph_version`
- `nodes`
- `edges`
- `ready_nodes`
- `waiting_nodes`
- `completed_nodes`
- `failed_nodes`
- `node_payloads`
- `next_node_index`
- `graph_meta`

讨论组只是这套 DAG 的一个业务接入方。

### 5.1 调度规则

固定规则：

- 初始化后，入度为 0 的节点进入 `ready`
- `advance` 每次只 `pop` 一个 ready node
- 节点完成后，检查后继依赖是否满足
- 满足则推进到 `ready`
- 节点失败后，进入 `failed_nodes`

这套调度语义现在已经是全项目可复用能力，不应该再写回业务专用状态机。

---

## 6. 讨论 DAG 结构

讨论图定义在 `backend/web/discussion_dag.py`。

当前节点类型：

- `discussion_moderator_opening`
- `discussion_agenda_setup`
- `discussion_opening_turn`
- `discussion_round_summary`
- `discussion_focused_turn`
- `discussion_consensus_draft`
- `discussion_final_response_turn`
- `discussion_finish`

### 6.1 初始链路

初始 DAG 是：

1. `moderator_opening`
2. `agenda_setup`
3. `opening_turn*`
4. `round_summary`

### 6.2 动态展开

后续节点不是一次性写死，而是根据总结结果追加：

- 如果还需要深入讨论，追加 `focused_turn*`
- 然后再进 `round_summary`
- 如果可以收束，追加 `consensus_draft`
- 必要时再插入 `final_response_turn*`
- 最后进入 `finish`

当前默认最多两轮核心讨论。

---

## 7. 单节点执行逻辑

### 7.1 主持节点

主持节点执行路径：

1. 读取当前 `discussion_plan / consensus_state / stance_map`
2. 组装主持上下文
3. 调用模型生成结构化 payload
4. 校验 payload
5. 双写一条主持事件和一条公开主持发言
6. 更新讨论状态

主持节点对应事件：

- `moderator_opening`
- `agenda_setup`
- `moderator_summary`
- `consensus_draft`

当前主持节点的公开输出规则：

- `WerewolfEvent` 继续承担“流程节点记录”
- `WerewolfSpeech` 承担“公开舞台内容回放”
- 主持发言的 `metadata` 会带 `is_moderator_speech=true`
- 公开发言统计口径包含主持人，不再只统计普通角色

### 7.2 角色节点

角色节点执行路径：

1. 收集当前可见公开发言
2. 只给该角色注入前置可见信息
3. 先生成结构化发言提纲
4. 再根据提纲生成正文
5. 校验正文质量
6. 落库到 `WerewolfSpeech`
7. 更新 `stance_map`

这条链路的关键不是 prompt，而是依赖顺序：

- 提纲先行
- 正文后行
- 正文必须受提纲约束，但不做字面对齐

---

## 8. 受控上下文原则

每个角色发言不是拿全部历史，而是拿受控上下文。

包含：

- 当前主题
- 当前阶段
- 当前轮次
- 主持人问题
- 当前 agenda_items
- 当前 focus_points
- 自己上一轮立场摘要
- 最近几条公开发言

注意：

- 主持人的公开发言也属于“可见公开发言”
- 但参与者轮次统计只按“非主持公开发言”计算
- 否则主持节点会把 `current_turn` 和发言顺序冲乱

硬约束：

- 只能引用已公开的前置发言
- 不能把未来发言当成已发生内容
- 不能暴露系统提示词或模型身份

对应落库 metadata：

- `visible_speech_ids`
- `reply_to_speech_ids`
- `stance_label`
- `addresses_agenda_items`
- `plan`
- `new_information`
- `response_target`
- `validation_passed`
- `similarity_score`

这保证了每条发言都是可审计的，而不是黑盒文本。

---

## 9. 质量闸门

当前系统明确不接受“为了不断流程，塞一段废话过去”。

所以不存在 fallback 模板兜底。

### 9.1 角色校验

角色正文至少会被这些规则拦截：

- 太短
- 泄漏系统/越界
- 引用未来发言
- 和最近发言高度重复
- 和自己上一轮核心内容过于相似

注意：

- 当前已经不再要求“正文必须和 `new_information` 做字面对齐”
- 原因是模型经常会意译、换角度表达、换比喻表达
- 这种情况下，严格做字符串或片段对齐会误伤正常讨论

现在保留的是两层更合理的约束：

1. 提纲本身必须包含有效新信息
2. 正文不能太短、不能重复、不能越界、不能偷看未来内容

### 9.2 主持校验

主持节点至少会校验：

- 返回的是有效 JSON
- 当前阶段必填字段存在
- `content` 不为空
- `agenda_items / new_focus / consensus_draft` 等阶段关键字段不为空
- 主持输出不能只是重复主题或重复最近主持事件

### 9.3 失败语义

一旦失败：

- 不落 fallback 内容
- 不自动跳到下一节点
- 房间进入 `blocked`
- 写入 `node_failed` 事件
- 前端停止自动推进

这条规则是故意设计成严格的，因为隐藏问题只会让后面更难排查。

---

## 10. 真实线上问题与修复

这是当前讨论组工程里最重要的一段，必须保留。

### 10.1 `<think>` 导致结构化截断

当前实际运行模型 `MiniMax-M2.7-highspeed` 会返回：

- `<think>...</think>`
- 然后才是正文或 JSON

早期问题：

- 主持节点要求统一输出大 JSON
- `consensus_draft` 这种阶段字段很多，payload 很重
- `<think>` 先吃掉输出预算
- 后面的 JSON 被截断
- 结果就表现成：
  - `主持发言缺少 agenda_items`
  - `主持发言缺少 content`

修复方式不是只调大 token，而是：

1. 主持节点改成“按阶段最小 schema”输出
2. 给不同阶段加简洁约束，压缩 `content`
3. 结构化预算适度提高，但不依赖无限放大

这三个组合起来，才真正把截断概率压下去。

### 10.2 SQLite `database is locked`

这是另一个关键问题。

早期 `advance_discussion_group()` 被 `@transaction.atomic` 包住，而函数内部会直接发外部模型请求。

结果：

- SQLite 写锁在等待模型期间一直不释放
- 前端继续自动推进，或者任何后续请求进来
- 在提交阶段就可能报：`database is locked`

根因不是 SQLite 太弱，而是：

- 长事务包住了外部 IO

修复方式：

- 去掉 `advance_discussion_group()` 的 `@transaction.atomic`
- 让模型调用发生在自动提交模式下
- 只让每次实际数据库写操作占用极短锁时间

这是硬性工程原则：

**任何外部模型调用，都不能放在数据库长事务里。**

当前已经有测试覆盖这条规则。

### 10.3 `new_information` 字面对齐误杀

在聚焦讨论轮，早期有一条规则：

- 提纲里的 `new_information` 必须在正文里有足够明显的字面重合

这条规则看起来合理，但真实运行中会误伤：

- 模型把提纲内容意译后再表达
- 模型把抽象判断展开成例子
- 模型保留同一结论，但换了论证路径

结果就是：

- 讨论内容本身是正常的
- 但校验因为“没有足够字面重合”而判失败

修复方式：

- 去掉正文与 `new_information` 的强制字面对齐校验
- 只保留提纲有效性校验
- 只保留正文质量校验

结论：

`new_information` 更适合作为“规划辅助字段”和“审计字段”，不适合作为正文文本的硬匹配键。

### 10.4 `leakage` 关键词误杀

早期 `leakage` 检测是简单关键词包含，例如：

- `提示词`
- `系统要求`
- `后台`
- `指令`

这种做法会误伤正常讨论，例如：

- “这是系统设计问题”
- “后台机制如何约束风险”
- “执行指令链条”

这些都是普通中文语境，不等于模型在泄露系统元信息。

修复方式：

- 不再做粗暴关键词包含
- 改成明确语境匹配，例如：
  - `作为AI`
  - `我是模型`
  - `系统提示`
  - `后台指令`
  - `根据指令回答`

结论：

泄漏检测必须识别“系统元语境”，不能只看词面。

### 10.5 前端把主持 payload 当成正文展示

主持事件里有两类信息：

1. `content`
   - 主持人真正公开说的话
2. `payload`
   - 结构化流程字段，例如：
   - `agenda_items`
   - `focus_points`
   - `moderator_question`
   - `route`

如果前端把这两类信息直接拼到一起，就会出现这种展示：

- 主持正文下面直接跟着“议题 / 焦点 / 下一步”

这会让用户误以为主持人自己在说一大段机械说明。

正确做法：

- `content` 作为正文展示
- `payload` 作为流程卡片展示

这是展示层问题，不是生成层问题。

---

## 11. 前端职责

讨论页前端职责很克制：

- 创建房间
- 拉取详情
- 手动或自动调用 `advance`
- 展示事件流、发言回放、阶段信息、失败原因
- 在失败时停止自动推进

当前页面结构是两列：

- 左列：主持人聚焦卡 + 公开发言回放
- 右列：主持人便签、议题/焦点、讨论收束、参与角色、事件时间线、观察者备注

当前展示原则：

- 主持人的公开台词进入“公开发言回放”
- 主持节点 payload 只进入右侧信息卡或事件时间线
- 不把 payload 结构字段直接拼进主持正文

前端不负责主持规划，不负责 DAG 调度，也不负责文本质量修正。

这保证了：

- 业务正确性由后端掌控
- 前端只是展示和触发器

---

## 12. 当前实现边界

当前系统仍有边界，不要误判为“通用智能群聊平台”：

- 只支持单主持人
- 主持人固定为第一个角色
- 讨论仍是串行发言，不支持并行节点执行
- 只做共识型讨论，不做投票制决策
- 仍依赖底层模型本身的语言能力
- 还没有独立的讨论模型表，只是复用旧房间表

---

## 13. 后续演进建议

如果后面继续增强，优先级建议如下。

### 13.1 第一优先级

- 给主持节点加更稳定的结构化协议
- 给角色提纲增加更明确的“新增信息类别”约束
- 在前端展示失败节点和失败码，方便调试

### 13.2 第二优先级

- 把旧 `Werewolf*` 模型正式重命名成 `Discussion*`
- 把讨论组事件和发言表彻底去狼人杀命名残留

### 13.3 第三优先级

- 引入更细的质量评分器
- 区分“共识型讨论”“辩论型讨论”“评审型讨论”三种 DAG 模板
- 对不同模型做 capability profiling，而不是一刀切 prompt

---

## 14. 当前必须保持不变的工程约束

后续改动时，下面这些约束默认不能破：

1. 第一个角色就是主持人，不要再改回隐藏系统主持人
2. `advance` 仍然一次只执行一个 DAG 节点
3. 失败时宁可阻断，也不要 fallback 灌模板话
4. 角色只能看到前置可见发言，不能读未来内容
5. 外部模型调用不能被数据库长事务包住
6. 主持节点按阶段输出最小 schema，不要恢复大而全 JSON
7. 不要恢复“正文必须和 `new_information` 做字面对齐”的硬校验
8. 不要把普通中文里的“系统 / 指令 / 后台”直接当成泄漏
9. 前端不能把主持事件的 `payload` 直接混进正文区
10. 主持人公开发言必须进入 `WerewolfSpeech`，不要再退回“只写事件流”

这 10 条是当前讨论组能稳定运行的最小工程基线。
