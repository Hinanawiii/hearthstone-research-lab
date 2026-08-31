from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from .generated.advanced_status_batch import CARDS as ADVANCED_STATUS_BATCH_CARDS
from .generated.damage_batch import CONTRACTS as DAMAGE_CONTRACTS
from .generated.status_batch import CARDS as STATUS_BATCH_CARDS
from .generated.tribe_poison_batch import CARDS as TRIBE_POISON_BATCH_CARDS
from .store import ReviewStore

CLASSIFICATION_VERSION = "core-authoring-batches.v1"


@dataclass(frozen=True)
class BatchCategory:
    key: str
    label_zh: str
    dependency_zh: str


CATEGORIES: Tuple[BatchCategory, ...] = (
    BatchCategory(
        "deterministic_damage",
        "确定性伤害",
        "目标选择、固定伤害、群体范围和过载；先复用同一套伤害结算原语。",
    ),
    BatchCategory(
        "stats_status_and_resources",
        "属性、状态与资源",
        "增减属性、治疗、护甲、冻结、沉默、法力和其他持续状态。",
    ),
    BatchCategory(
        "weapons_and_hero_combat",
        "武器与英雄战斗",
        "武器区、耐久度、英雄攻击以及相关触发。",
    ),
    BatchCategory(
        "summon_death_and_corpses",
        "召唤、死亡与残骸",
        "衍生物、亡语、复活、消灭、死亡队列和死亡骑士残骸。",
    ),
    BatchCategory(
        "hand_deck_and_random",
        "手牌牌库与随机",
        "抽牌、发现、洗入、复制、变形、随机生成和隐藏信息。",
    ),
    BatchCategory(
        "event_triggers_and_history",
        "事件触发与历史",
        "回合、攻击、施法、受伤、抽牌等事件总线，以及跨回合历史。",
    ),
    BatchCategory(
        "special_actions_and_zones",
        "特殊动作与区域",
        "奥秘、地标、抉择、流放、连击、可交易和费用替换等动作模型。",
    ),
    BatchCategory(
        "composite_and_unique",
        "复合与独特效果",
        "同时依赖多套系统或无法安全归入单一基础批次的卡牌。",
    ),
)

_CATEGORY_BY_KEY = {item.key: item for item in CATEGORIES}

_SPECIAL_MARKERS = (
    "奥秘",
    "抉择",
    "流放",
    "连击",
    "可交易",
    "法力值消耗减少",
    "法力值消耗增加",
    "法力值消耗为",
    "改为消耗生命值",
)
_EVENT_MARKERS = (
    "每当",
    "每次",
    "在你的回合结束时",
    "在你的回合开始时",
    "在每个回合开始时",
    "在你对手的回合",
    "如果你在本回合",
    "在本随从被攻击后",
    "在你的英雄攻击后",
    "在你施放",
    "在你使用",
    "在你抽",
    "在一个友方",
    "本局对战的剩余时间",
    "光环",
    "你的其他",
    "所有友方攻击",
    "每有",
    "相邻的随从拥有",
    "法术伤害",
)
_ZONE_MARKERS = (
    "抽",
    "发现",
    "随机",
    "手牌",
    "牌库",
    "洗入",
    "置入你的手牌",
    "移回拥有者的手牌",
    "随机将",
    "随机置入",
    "变形",
    "偷取",
    "香蕉",
)
_SUMMON_DEATH_MARKERS = (
    "召唤",
    "复活",
    "亡语",
    "残骸",
    "死亡",
    "消灭",
    "死去",
)
_STATUS_RESOURCE_MARKERS = (
    "恢复",
    "护甲",
    "获得+",
    "获得 +",
    "使一个",
    "使你的",
    "使所有",
    "攻击力",
    "生命值",
    "冻结",
    "沉默",
    "剧毒",
    "法力水晶",
    "过载",
)


def classify_core_card(card: Mapping[str, Any]) -> str:
    card_id = str(card["card_id"])
    card_type = str(card.get("card_type", ""))
    text = str(card.get("source_text", ""))
    if card_id in DAMAGE_CONTRACTS:
        return "deterministic_damage"
    if (
        card_id in STATUS_BATCH_CARDS
        or card_id in TRIBE_POISON_BATCH_CARDS
        or card_id in ADVANCED_STATUS_BATCH_CARDS
    ):
        return "stats_status_and_resources"
    if card_type == "WEAPON" or "武器" in text or "英雄攻击" in text:
        return "weapons_and_hero_combat"
    if card_type == "LOCATION" or any(marker in text for marker in _SPECIAL_MARKERS):
        return "special_actions_and_zones"
    if any(marker in text for marker in _EVENT_MARKERS):
        return "event_triggers_and_history"
    if any(marker in text for marker in _SUMMON_DEATH_MARKERS):
        return "summon_death_and_corpses"
    if any(marker in text for marker in _ZONE_MARKERS):
        return "hand_deck_and_random"
    if any(marker in text for marker in _STATUS_RESOURCE_MARKERS):
        return "stats_status_and_resources"
    return "composite_and_unique"


def build_core_batch_report(store: ReviewStore) -> Dict[str, Any]:
    remaining = [
        card
        for card in store.list_cards()
        if card["card_set"] == "CORE" and card["implementation_status"] == "not_started"
    ]
    grouped: Dict[str, List[Dict[str, Any]]] = {item.key: [] for item in CATEGORIES}
    for card in remaining:
        category_key = classify_core_card(card)
        grouped[category_key].append(
            {
                key: card[key]
                for key in (
                    "card_id",
                    "name",
                    "card_class",
                    "card_type",
                    "cost",
                    "source_text",
                    "generation_approved",
                    "implementation_status",
                )
            }
        )
    batches = []
    for category_spec in CATEGORIES:
        cards = sorted(
            grouped[category_spec.key],
            key=lambda item: (
                str(item["card_class"]),
                str(item["card_type"]),
                int(item["cost"] if item["cost"] is not None else -1),
                str(item["card_id"]),
            ),
        )
        batches.append(
            {
                "key": category_spec.key,
                "label_zh": category_spec.label_zh,
                "dependency_zh": category_spec.dependency_zh,
                "card_count": len(cards),
                "cards": cards,
            }
        )
    versions = sorted({str(card["source_version"]) for card in remaining})
    return {
        "classification_version": CLASSIFICATION_VERSION,
        "card_set": "CORE",
        "source_versions": versions,
        "remaining_card_count": len(remaining),
        "batches": batches,
    }


def batch_counts(report: Mapping[str, Any]) -> Sequence[Mapping[str, Any]]:
    return [
        {
            "key": batch["key"],
            "label_zh": batch["label_zh"],
            "card_count": batch["card_count"],
        }
        for batch in report["batches"]
    ]


__all__ = [
    "CATEGORIES",
    "CLASSIFICATION_VERSION",
    "batch_counts",
    "build_core_batch_report",
    "classify_core_card",
]
