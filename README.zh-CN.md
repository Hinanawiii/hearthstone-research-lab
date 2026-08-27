# 炉石游戏研究实验室

[English](README.md)

Hearthstone Research Lab（简称 CardLab）是一个可以实际运行的卡牌游戏研究框架。自我
对弈的专用策略网络和 LLM 研究员共用一套实验流程：LLM 先理解游戏，提出可证伪的战略
假说，再把假说转成受控实验。只替人调整学习率和网络层数不算游戏研究。

这是一个早期研究项目，不是完整的炉石模拟器，也不是天梯机器人或客户端自动化工具。
`legacy-mage-v1` 只覆盖一套对称的 30 张卡组：15 种可收集卡各两张，外加幸运币与火焰冲击。
范围故意收得很小，目的是让规则正确性、复盘过程和实验结论都能被人检查。

## LLM 到底在研究什么

一份有效提案必须同时包括：

- 关于节奏、资源、场面或随机决策等游戏机制的主张；
- 事先写明的方向性预测，以及会推翻主张的证据；
- 至少一个对比两种真实游戏选择的局面探针；
- 可执行的游戏层干预，例如概念特征、局面课程、策略先验或评测探针。

如果提案只有优化器、学习率、网络宽度或训练轮数，它会被验证器直接拒绝。LLM 可以通过
类型明确、可审计的接口操作专用 AI，但不能修改规则引擎、隐藏信息边界、固定种子评测器和
提案验证器。

## 快速开始

需要 Python 3.9 或更高版本。基础模拟不依赖第三方库，神经网络训练需要 PyTorch。

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[train,dev]'

cardlab simulate --games 4 --seed 1
cardlab packet --games 12 --output runs/research-packet.json
cardlab propose --backend mock --output runs/proposal.json
cardlab autoresearch --backend mock --episodes 20 --eval-games 8 \
  --run-dir runs/first-cycle
```

`mock` 后端只用于测试协议，并不是真正的 LLM。接入兼容 OpenAI Chat Completions 的接口：

```bash
export CARDLAB_LLM_BASE_URL='https://your-endpoint.example/v1'
export CARDLAB_LLM_API_KEY='...'
export CARDLAB_LLM_MODEL='your-model'
cardlab autoresearch --backend openai-compatible --episodes 100 --eval-games 40
```

不要提交 API Key。`runs/` 下的模型、研究包和提案默认不会进入 Git。

## 当前实现

- 固定随机种子的完整对局与 JSONL 动作轨迹；
- 隐藏对手手牌和双方牌库顺序的玩家观察；
- 法力、水晶临时增益、抽牌、疲劳、手牌与场面上限、嘲讽、冲锋、战斗、定向伤害、随机
  伤害、火焰冲击和幸运币；
- 随机策略、透明的贪心基线和一个小型策略/价值网络；
- LLM 研究数据包、结构化假说验证、可执行研究控制、同条件基线/候选评测和追加式理论账本。

解释实验结果前，请先阅读[架构说明](docs/ARCHITECTURE.md)、
[研究协议](docs/RESEARCH_PROTOCOL.md)和[牌池契约](docs/CARD_POOL.md)。

候选模型通过门禁，只说明它在预先指定的评测里达标，并不等于假说中的因果机制已经得到
证明。结果不显著时，账本会如实记录 `inconclusive`，而不是偷偷更换随机种子重跑。

项目采用 [MIT License](LICENSE)。炉石传说及相关名称是 Blizzard Entertainment 的商标；
本项目与 Blizzard Entertainment 无隶属、授权或赞助关系，也不包含卡图、音频、客户端代码
或其他专有素材。具体边界见 [TRADEMARKS.md](TRADEMARKS.md)。
