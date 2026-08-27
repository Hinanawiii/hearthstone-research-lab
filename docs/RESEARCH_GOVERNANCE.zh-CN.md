# 研究治理框架

这层机制把“LLM 提出值得研究的游戏问题”和“执行训练或探针”分开。它只登记提案、人工
决定、牌池依赖、模型谱系和实验结果，不会自行启动训练、自我对弈或探针。

本地服务启动后，可在 <http://127.0.0.1:8765/research.html> 审核提案。

## 提案状态

研究提案按以下顺序推进：

```text
draft -> critic_reviewed -> awaiting_human -> approved
                |                 |
                +-> revision_requested -> draft
                                  |
                                  +-> rejected
```

每次状态变化都要记录操作者和审核意见。LLM 可以写草稿，另一个模型负责反方审查；按照
工作流约定，最后的批准必须由人工作出。系统暂时不通过角色字段强行识别人类，但审核页面
和事件记录会完整保留责任人。

提案至少应说明一个游戏内机制、可检验的预测和可能推翻它的观察。单纯调整网络层数、学习
率或训练轮数，不算独立的游戏研究问题。

## 有限研究牌池

提案获批后，可以创建一个研究胶囊。它不是整个标准环境，而是本次研究实际需要的有限依赖
集合，其中每张牌都要标明用途：

- `primary`：直接研究对象；
- `token`：衍生牌或召唤物；
- `random_pool`：发现、生成或随机效果可能引用的牌；
- `interaction`：构造关键交互局面所需的牌。

只有集合中的每张牌都达到 `ready_for_research`，人工才能冻结胶囊。冻结记录会保存卡牌
来源指纹、生成批准时间、实现核验时间和核验证据摘要。之后只要来源、批准或实现状态发生
变化，胶囊就会被判定为过期；旧胶囊不能继续登记实验，必须重新审核并冻结。

## 实验与冠军模型

实验登记需要同时满足：

1. 研究提案已经人工批准；
2. 研究胶囊已经冻结且没有过期；
3. 基线是当前冠军模型；
4. 探针声明的 `required_card_ids` 是胶囊的非空子集；
5. 种子、对照、指标和执行器配置已经写入实验记录。

登记实验只会生成不可变的实验哈希，不代表实验已经运行。外部执行器提交结果后，实验仍要
交给人工审核；只有通过审核的实验才能晋升候选冠军。候选模型必须把本次实验的基线冠军
登记为父节点。晋升后，原冠军会被标记为 `retired`，谱系不会被覆盖。

## 本地 API

提案页面使用以下接口：

```http
POST /api/research/proposals
POST /api/research/proposals/{proposal_id}/transitions
GET  /api/research/proposals
GET  /api/research/proposals/{proposal_id}
```

框架还提供胶囊、冠军和实验登记接口：

```http
POST /api/research/capsules
POST /api/research/capsules/{capsule_id}/freeze
GET  /api/research/capsules/{capsule_id}

POST /api/research/champions
POST /api/research/champions/{champion_id}/promote
GET  /api/research/champions/{champion_id}

POST /api/research/experiments
POST /api/research/experiments/{experiment_id}/transitions
GET  /api/research/experiments/{experiment_id}
```

这些接口和制卡澄清台共用一个 SQLite 数据库，因此胶囊门禁读取的是同一份人工决定和实现
状态。当前页面先覆盖提案审核；胶囊、实验和冠军页面将在实际启动第一批研究前补齐。

## 当前边界

框架已经能阻止未澄清、未批准或未核验的卡牌进入冻结牌池，也能拦住试图绕过提案和结果
人工审核的流程。以下工作还没有接入：

- 自动选择第一批现代卡牌；
- 调用制卡模型生成规则实现；
- 运行训练、自我对弈或探针；
- 根据结果自动修改算法或晋升模型。

现阶段可以先积累提案和制卡问题。正式研究要等第一批相关卡牌完成
`ready_for_research`，再由人工批准一个具体提案并冻结对应胶囊。
