from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, Mapping

from ...engine import Game
from ...model import (
    Action,
    ActionType,
    CardDef,
    CardType,
    Effect,
    HandCard,
    Minion,
    TargetMode,
    TargetRef,
)
from ..review_format import review_state_from_observation

SOURCE_VERSION = "250339"
GENERATED_BY = "codex-gpt-5.6-core-death-history-batch-v1"

TOKEN_CARDS: Dict[str, CardDef] = {
    "SW_439t": CardDef(
        "SW_439t",
        "橡果",
        CardType.SPELL,
        1,
        effects=(Effect("summon", 1, card_id="SW_439t2"),),
        collectible=False,
        casts_when_drawn=True,
    ),
    "SW_439t2": CardDef(
        "SW_439t2",
        "满足的松鼠",
        CardType.MINION,
        1,
        2,
        1,
        races=("BEAST",),
        collectible=False,
    ),
    "UNG_810": CardDef(
        "UNG_810",
        "剑龙",
        CardType.MINION,
        4,
        2,
        6,
        taunt=True,
        races=("BEAST",),
        collectible=False,
    ),
}

CARDS: Dict[str, CardDef] = {
    "CORE_SW_439": CardDef(
        "CORE_SW_439",
        "活泼的松鼠",
        CardType.MINION,
        1,
        2,
        1,
        races=("BEAST",),
        rarity="RARE",
        deathrattle_effects=(Effect("shuffle_into_deck", 4, card_id="SW_439t"),),
    ),
    "CORE_BT_201": CardDef(
        "CORE_BT_201",
        "强能箭猪",
        CardType.MINION,
        3,
        2,
        4,
        races=("MECHANICAL", "BEAST"),
        rarity="EPIC",
        deathrattle_effects=(Effect("random_damage_source_attack"),),
    ),
    "CORE_YOD_026": CardDef(
        "CORE_YOD_026",
        "邪魔仆从",
        CardType.MINION,
        1,
        2,
        1,
        races=("DEMON",),
        rarity="COMMON",
        deathrattle_effects=(Effect("random_buff_other_friendly_source_attack"),),
    ),
    "CORE_UNG_952": CardDef(
        "CORE_UNG_952",
        "剑龙骑术",
        CardType.SPELL,
        5,
        target_mode=TargetMode.ANY_MINION,
        effects=(
            Effect(
                "buff_and_attach_deathrattle",
                attack=2,
                health=6,
                card_id="UNG_810",
            ),
        ),
    ),
    "CORE_CATA_002": CardDef(
        "CORE_CATA_002",
        "佳莉娅·米奈希尔",
        CardType.MINION,
        6,
        4,
        5,
        races=("UNDEAD",),
        rarity="LEGENDARY",
        effects=(Effect("resurrect_highest_cost_friendly", 1),),
    ),
    "CORE_GVG_114": CardDef(
        "CORE_GVG_114",
        "斯尼德的伐木机",
        CardType.MINION,
        7,
        5,
        7,
        races=("MECHANICAL",),
        rarity="LEGENDARY",
        deathrattle_effects=(Effect("summon_random_rarity", keyword="LEGENDARY"),),
    ),
}

_SOURCE_TEXTS = {
    "CORE_SW_439": "亡语：将四张橡果洗入你的牌库。当抽到橡果时，召唤一只2/1的松鼠。",
    "CORE_BT_201": "亡语： 造成等同于本随从攻击力的伤害，随机分配到所有敌人身上。",
    "CORE_YOD_026": "亡语：随机使一个友方随从获得本随从的攻击力。",
    "CORE_UNG_952": "使一个随从获得+2/+6和嘲讽。当该随从死亡时，召唤一只剑龙。",
    "CORE_CATA_002": "战吼：复活你在本局对战中死亡的法力值消耗最高的随从。",
    "CORE_GVG_114": "亡语：随机召唤一个传说随从。",
}

AUTHORING_METADATA: Dict[str, Dict[str, Any]] = {
    card_id: {
        "source_version": SOURCE_VERSION,
        "source_text": _SOURCE_TEXTS[card_id],
        "source_text_zh": _SOURCE_TEXTS[card_id],
        "name_zh": card.name,
        "generated_by": GENERATED_BY,
        "review_status": "awaiting_human_scenario_review",
    }
    for card_id, card in CARDS.items()
}

SCENARIO_CARD_NAMES_ZH = {
    **{card_id: card.name for card_id, card in CARDS.items()},
    **{card_id: card.name for card_id, card in TOKEN_CARDS.items()},
    "CS2_120": "淡水鳄",
    "CS2_200": "石拳食人魔",
}


def _player(state: Mapping[str, Any], role_zh: str) -> Mapping[str, Any]:
    return next(item for item in state["players"] if item["role_zh"] == role_zh)


def _assertion(
    assertion_id: str,
    subject_zh: str,
    before: Any,
    after: Any,
    expected_zh: str,
) -> Dict[str, Any]:
    return {
        "assertion_id": assertion_id,
        "subject_zh": subject_zh,
        "before": before,
        "after": after,
        "expected_zh": expected_zh,
    }


def build_review_scenario(
    card_id: str, card_registry: Mapping[str, CardDef]
) -> Dict[str, Any]:
    if card_id not in CARDS:
        raise ValueError("unknown death history batch card: {}".format(card_id))
    card = CARDS[card_id]
    game = Game(seed=sum(ord(char) for char in card_id), card_registry=card_registry)
    actor = game.state.active_player
    enemy = 1 - actor
    own = game.state.players[actor]
    opposing = game.state.players[enemy]
    own.mana = own.max_mana = 10
    opposing.mana = opposing.max_mana = 10
    own.hand = []
    opposing.hand = []
    own.board = []
    opposing.board = []
    own.deck = ["CS2_120"]
    opposing.deck = ["CS2_120"]

    if card_id in {"CORE_SW_439", "CORE_BT_201", "CORE_YOD_026", "CORE_GVG_114"}:
        attack = 5 if card_id in {"CORE_BT_201", "CORE_YOD_026"} else card.attack
        own.board = [
            Minion(
                119_000,
                card_id,
                attack,
                1,
                card.health,
                races=card.races,
                summoned_turn=0,
            )
        ]
        if card_id == "CORE_YOD_026":
            own.board.append(Minion(119_001, "CS2_120", 2, 3, 3, summoned_turn=0))
        action = Action(ActionType.HERO_POWER, target=TargetRef.minion(actor, 119_000))
        description = "我方英雄技能消灭仅剩1点生命的《{}》。".format(card.name)
    elif card_id == "CORE_UNG_952":
        own.hand = [HandCard(119_010, card_id)]
        own.board = [Minion(119_011, "CS2_120", 2, 3, 3, summoned_turn=0)]
        action = Action(ActionType.PLAY, 119_010, TargetRef.minion(actor, 119_011))
        description = "我方对淡水鳄使用《剑龙骑术》。"
    else:
        own.hand = [HandCard(119_020, card_id)]
        own.graveyard = ["CS2_120", "CS2_200"]
        action = Action(ActionType.PLAY, 119_020)
        description = "我方使用《佳莉娅·米奈希尔》，墓地中有2费和6费随从。"

    before = review_state_from_observation(game.observation(actor))
    game.apply(action)
    after = review_state_from_observation(game.observation(actor))
    own_before = _player(before, "我方")
    own_after = _player(after, "我方")
    opposing_before = _player(before, "敌方")
    opposing_after = _player(after, "敌方")
    assertions = []
    special_cases: list[Dict[str, Any]]

    if card_id == "CORE_SW_439":
        assertions.append(
            _assertion(
                "shuffle-four-acorns",
                "我方牌库数量",
                own_before["zones"]["deck"]["count"],
                own_after["zones"]["deck"]["count"],
                "亡语洗入四张橡果",
            )
        )
        special_cases = [
            {
                "kind": "deck_change",
                "summary_zh": "四张橡果加入并重新打乱我方牌库。",
                "details": {
                    "player_id": actor,
                    "before_count": own_before["zones"]["deck"]["count"],
                    "after_count": own_after["zones"]["deck"]["count"],
                    "drawn_count": 0,
                    "added_count": 4,
                    "shuffled_count": 4,
                    "order_changed": True,
                    "known_top_before": [],
                    "known_top_after": [],
                },
            }
        ]
    elif card_id == "CORE_BT_201":
        assertions.append(
            _assertion(
                "attack-snapshot-damage",
                "敌方英雄生命值",
                opposing_before["hero"]["health"],
                opposing_after["hero"]["health"],
                "死亡时攻击力为5，因此分成五次1点伤害",
            )
        )
        special_cases = _death_tags(card_id, 119_000, own_before, own_after, "保存死亡时的5点攻击力快照。")
    elif card_id == "CORE_YOD_026":
        croc_before = own_before["zones"]["board"][1]
        croc_after = own_after["zones"]["board"][0]
        assertions.append(
            _assertion(
                "attack-snapshot-buff",
                "淡水鳄攻击力",
                croc_before["attack"],
                croc_after["attack"],
                "随机池只有淡水鳄，获得死亡来源的5点攻击力",
            )
        )
        special_cases = _death_tags(card_id, 119_000, own_before, own_after, "攻击力快照不读取随从离场后的基础值。")
    elif card_id == "CORE_UNG_952":
        target_after = own_after["zones"]["board"][0]
        assertions.extend(
            [
                _assertion(
                    "stegodon-stats",
                    "淡水鳄属性",
                    [2, 3],
                    [target_after["attack"], target_after["health"]],
                    "获得+2/+6并具有嘲讽",
                ),
                _assertion(
                    "attached-deathrattle",
                    "附加亡语",
                    [],
                    target_after["tags"].get("attached_deathrattle_effects", []),
                    "在随从实例上附加死亡时召唤剑龙的亡语",
                ),
            ]
        )
        special_cases = [
            {
                "kind": "special_tags",
                "summary_zh": "剑龙亡语附着在被强化的随从实例上。",
                "details": {
                    "entity_id": target_after["entity_id"],
                    "card_id": "CS2_120",
                    "tags_before": {},
                    "tags_after": target_after["tags"],
                    "explanation_zh": "沉默或变形等后续机制需要作用于实例附加亡语，而非原始卡牌定义。",
                },
            }
        ]
    elif card_id == "CORE_CATA_002":
        result_cards = [item["card_id"] for item in own_after["zones"]["board"]]
        assertions.append(
            _assertion(
                "resurrect-highest-cost",
                "我方场上随从",
                [],
                result_cards,
                "佳莉娅入场后复活墓地中费用最高的6费石拳食人魔",
            )
        )
        special_cases = _death_tags(card_id, 119_020, own_before, own_after, "复活读取公开墓地历史，不从墓地列表移除记录。")
    else:
        summoned = [item for item in own_after["zones"]["board"] if item["card_id"] == card_id]
        assertions.append(
            _assertion(
                "summon-legendary",
                "亡语召唤的传说随从",
                0,
                len(summoned),
                "当前已实现传说池仅含斯尼德自身，因此稳定召唤一个5/7机械",
            )
        )
        special_cases = _death_tags(card_id, 119_000, own_before, own_after, "候选池按已注册、可收集、传说随从过滤。")

    return {
        "scenario_id": "{}-death-history-review-v1".format(card_id.lower().replace("_", "-")),
        "title_zh": "{}：死亡快照与后续效果核验".format(card.name),
        "purpose_zh": "核对死亡历史、实例亡语、死亡时属性快照和抽到时施放。",
        "before": before,
        "action": {
            "type": "play_or_destroy_fixture",
            "actor_player_id": actor,
            "source_entity_id": action.source_id,
            "card_id": card_id,
            "target": asdict(action.target) if action.target else None,
            "description_zh": description,
            "engine_action": action.to_dict(),
        },
        "after": after,
        "assertions": assertions,
        "special_cases": special_cases,
    }


def _death_tags(
    card_id: str,
    entity_id: int,
    own_before: Mapping[str, Any],
    own_after: Mapping[str, Any],
    explanation_zh: str,
) -> list[Dict[str, Any]]:
    return [
        {
            "kind": "special_tags",
            "summary_zh": "死亡来源和墓地历史单独记录。",
            "details": {
                "entity_id": entity_id,
                "card_id": card_id,
                "tags_before": {"graveyard": own_before["zones"].get("graveyard", [])},
                "tags_after": {"graveyard": own_after["zones"].get("graveyard", [])},
                "explanation_zh": explanation_zh,
            },
        }
    ]


__all__ = [
    "AUTHORING_METADATA",
    "CARDS",
    "SCENARIO_CARD_NAMES_ZH",
    "TOKEN_CARDS",
    "build_review_scenario",
]
