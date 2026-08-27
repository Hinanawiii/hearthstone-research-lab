# 制卡澄清台

制卡澄清台是一个只监听本机地址的开发工具。制卡代理先登记卡牌，再把会改变规则实现的
问题逐批放进队列。人工不用同时在线。系统会把每次回答追加到 SQLite，后来修订也不会
覆盖旧答案。

## 启动

先把当前标准环境同步到本地。`latest` 会解析为一个固定的 HearthstoneJSON 构建号，并把
构建号和来源 URL 一同归档：

```bash
cardlab import-standard --db runs/authoring/review.db --build latest
```

截至 2026-08-27，标准环境的导入范围是 `CORE`、`EMERALD_DREAM`、`THE_LOST_CITY`、
`TIME_TRAVEL`、`CATACLYSM` 和 `ESCAPEFROM_VIOLET_HOLD`。默认数据库已导入构建
`250339`：1,166 张可收藏卡进入制卡队列，另有 995 个不可收藏的衍生物和依赖定义保存在
来源目录中。后者不会占满人工队列，但制卡代理可以按 ID 查询。

重复导入只处理变化：没有变化的卡不会重新打开访谈。名称、规则文本或结构化卡牌数据发生
变化时，原有问题和回答仍会保留，但卡牌会重新进入待审状态。以后退环境的卡只从当前队列
隐藏，历史仍然保留。

随后启动页面：

```bash
cardlab review --db runs/authoring/review.db --port 8765
```

然后打开 <http://127.0.0.1:8765>。默认数据库位于 `runs/`，不会提交到 Git，也不会自动
上传。服务只绑定 `127.0.0.1`，目前不提供远程访问和身份认证。

页面支持以下人工操作：

- 登记卡牌原文；
- 查看 AI 累积提交的问题；
- 查看 AI 联网研究得到的候选答案、置信度和来源；
- 把候选答案填入人工回答框，核对或修改后再保存；
- 保存确定答案；
- 将无法判断的问题标记为“需要实机验证”；
- 查看同一问题的历次答案；
- 在 AI 完成语义检查后结束本轮提问。

## 制卡门禁

制卡到研究分成三道门：

1. `authoring_ready`：AI 已结束本轮提问，而且每个阻塞问题的最新人工记录都是
   `answered`；
2. `ready_to_generate`：满足上一项，并由人工明确批准进入正式制卡队列；
3. `ready_for_research`：生成后的实现已完成代码检查、自动测试和人工局面核验，被标记为
   `implementation_ready`。

问题问完并不会自动启动制卡。`needs_verification` 仍是未解决状态；即使一张卡没有澄清
问题，也要经过人工批准。新增问题、修改来源语义、重新开放访谈或追加人工答案，都会撤销
已有的生成批准和实现就绪状态。

外部制卡代理只能领取 `ready_to_generate` 的卡牌。当前仓库负责队列和门禁，还没有接入
自动制卡执行器；点击“人工批准制卡”只会把卡牌放进待生成队列，不会调用模型或写入规则
代码。

## AI 研究候选

制卡 AI 可以先研究自己提出的问题。研究提示词要求它区分伤害事件、生命值支付和直接失去
生命等规则概念，并优先查阅官方文本、补丁说明和维护中的进阶规则资料。模拟器源码、实机
复现和社群讨论排在其后。每条引用都要写明它支持哪项判断；遇到版本差异或证据不足时，
AI 应返回 `needs_verification`，而不是补齐一个看似确定的答案。

研究结果保存在 `ai_assessments`，与人工 `answers` 分开。页面会显示这份记录，也能把候选
答案填入回答框，但不会改变 `current_resolution` 或 `ready_to_generate`。点击填入后仍需
人工核对并保存。这可以避免模型用自己的结论通过自己的门禁。

当前仓库负责研究提示词、存储契约和页面交互，不内置联网模型调度器。工作流可以调用具有
搜索能力的模型，再把结构化结果提交到本地 API。提示词构造器位于
`cardlab.authoring.research_prompt`。

## 给制卡代理的本地 API

登记或更新卡牌：

```http
POST /api/cards
Content-Type: application/json

{
  "card_id": "JAIL_205",
  "name": "蟊贼脏鼠",
  "source_text": "在你的回合结束时，偷取所有在你的回合中进入对手手牌的牌。"
}
```

一次提交一个或多个问题：

```http
POST /api/cards/JAIL_205/questions
Content-Type: application/json

{
  "questions": [
    {
      "question_id": "rat-burglar-turn-history",
      "category": "timing",
      "prompt": "先发生进手事件，再打出蟊贼脏鼠；回合结束时会偷走此前进入的牌吗？",
      "rationale": "决定触发器读取整回合历史，还是只监听入场后的事件。",
      "blocking": true,
      "asked_by": "authoring-llm"
    }
  ]
}
```

声明 AI 已完成本轮提问：

```http
POST /api/cards/JAIL_205/interview
Content-Type: application/json

{"complete": true}
```

人工批准进入正式制卡队列：

```http
POST /api/cards/JAIL_205/generation-approval
Content-Type: application/json

{
  "approved": true,
  "reviewer": "human-reviewer",
  "note": "阻塞问题已核对，可以生成第一版实现。"
}
```

生成器和审查者依次归档实现状态；只有 `implementation_ready` 必须附带核验证据：

```http
POST /api/cards/JAIL_205/implementation
Content-Type: application/json

{
  "status": "implementation_ready",
  "reviewer": "human-reviewer",
  "note": "代码、测试和关键局面均已核验。",
  "evidence": {
    "code_review": "approved",
    "automated_tests": "passed",
    "human_scenario_review": "approved"
  }
}
```

实现状态只能按 `not_started -> generated -> under_review -> implementation_ready` 推进；
审查者也可以退回 `generated` 或标记为 `rejected`。

读取制卡门禁、当前答案和完整回答历史：

```http
GET /api/cards/JAIL_205
```

按 ID 读取可收藏卡、衍生物或其他依赖的原始目录记录：

```http
GET /api/source-cards/CAP_805t
```

人工通常直接在页面回答。若需要通过 API 归档观察结果：

```http
POST /api/questions/rat-burglar-turn-history/answers
Content-Type: application/json

{
  "resolution": "answered",
  "answer": "会；它在回合结束时查询整个当前回合的进手事件。",
  "respondent": "human-reviewer"
}
```

`resolution` 可以是 `answered` 或 `needs_verification`。重复提交不会改写旧记录，卡牌详情
中的 `current_resolution` 取最后一次回答。

归档 AI 的候选答案：

```http
POST /api/questions/rat-burglar-turn-history/ai-assessments
Content-Type: application/json

{
  "assessment_key": "rat-burglar-turn-history-web-v1",
  "disposition": "needs_verification",
  "answer": "候选结论；人工采纳前仍需核对。",
  "reasoning": "简短的证据摘要和未决边界。",
  "confidence": "medium",
  "researched_by": "authoring-ai-web-v1",
  "sources": [
    {
      "url": "https://example.test/rules",
      "title": "规则资料标题",
      "source_type": "maintained_rules",
      "claim": "这项来源具体支持的判断",
      "retrieved_at": "2026-08-27"
    }
  ]
}
```

`disposition` 可以是 `candidate_answer` 或 `needs_verification`；`confidence` 可以是 `low`、
`medium` 或 `high`。`assessment_key` 用于幂等重试。允许的 `source_type` 为 `official`、
`maintained_rules`、`source_code`、`client_test`、`community` 和 `other`。

## 工作流边界

页面会保存问题、人工判断、制卡批准和实现核验记录，但它无法证明 AI 已经问遍所有必要
问题。提问模型仍要检查目标、时序、区域、所有权、容量、随机性和快照，再由独立审查模型
补充反例。尚未解决的歧义会留在队列里，不会在无人知情时进入规则引擎。研究牌池如何引用
这些状态，见
[研究治理框架](RESEARCH_GOVERNANCE.zh-CN.md)。
