from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, Mapping, Optional

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
GENERATED_BY = "codex-gpt-5.6-core-summon-foundation-batch-v1"

TOKEN_CARDS: Dict[str, CardDef] = {
    "EX1_506a": CardDef(
        "EX1_506a",
        "鱼人斥候",
        CardType.MINION,
        1,
        1,
        1,
        races=("MURLOC",),
        collectible=False,
    ),
    "BAR_035t": CardDef(
        "BAR_035t",
        "迅捷土狼",
        CardType.MINION,
        1,
        1,
        1,
        rush=True,
        races=("BEAST",),
        collectible=False,
    ),
    "BOT_102t": CardDef(
        "BOT_102t",
        "火花",
        CardType.MINION,
        1,
        1,
        1,
        rush=True,
        races=("ELEMENTAL",),
        collectible=False,
    ),
    "CS2_065": CardDef(
        "CS2_065",
        "虚空行者",
        CardType.MINION,
        1,
        1,
        3,
        taunt=True,
        races=("DEMON",),
        collectible=False,
    ),
}

CARDS: Dict[str, CardDef] = {
    "CORE_EX1_506": CardDef(
        "CORE_EX1_506",
        "鱼人猎潮者",
        CardType.MINION,
        2,
        2,
        1,
        races=("MURLOC",),
        effects=(Effect("summon", 1, card_id="EX1_506a"),),
    ),
    "CORE_BAR_801": CardDef(
        "CORE_BAR_801",
        "击伤猎物",
        CardType.SPELL,
        1,
        target_mode=TargetMode.ANY_CHARACTER,
        effects=(
            Effect("damage", 1),
            Effect("summon", 1, target="owner", card_id="BAR_035t"),
        ),
    ),
    "CORE_BOT_451": CardDef(
        "CORE_BOT_451",
        "流电爆裂",
        CardType.SPELL,
        1,
        effects=(Effect("summon", 2, target="owner", card_id="BOT_102t"),),
        overload=1,
    ),
    "CORE_SW_088": CardDef(
        "CORE_SW_088",
        "恶魔来袭",
        CardType.SPELL,
        4,
        target_mode=TargetMode.ANY_CHARACTER,
        effects=(
            Effect("damage", 3),
            Effect("summon", 2, target="owner", card_id="CS2_065"),
        ),
    ),
    "CORE_RLK_062": CardDef(
        "CORE_RLK_062",
        "蛛魔护群守卫",
        CardType.MINION,
        4,
        1,
        3,
        taunt=True,
        races=("UNDEAD",),
        effects=(Effect("summon", 2, target="owner", card_id="CORE_RLK_062"),),
    ),
}

_SOURCE_TEXTS = {
    "CORE_EX1_506": "战吼：召唤一个1/1的鱼人斥候。",
    "CORE_BAR_801": "造成1点伤害。召唤一只1/1并具有突袭的土狼。",
    "CORE_BOT_451": "召唤两个1/1并具有突袭的“火花”。过载：（1）",
    "CORE_SW_088": "造成3点伤害。召唤两个1/3并具有嘲讽的虚空行者。",
    "CORE_RLK_062": "嘲讽。战吼：召唤本随从的两个复制。",
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
    "CS2_172": "血沼迅猛龙",
    "CS2_182": "冰风雪人",
}


def _player(state: Mapping[str, Any], role_zh: str) -> Mapping[str, Any]:
    return next(item for item in state["players"] if item["role_zh"] == role_zh)


def _board_cards(state: Mapping[str, Any], role_zh: str, card_id: str) -> list[Mapping[str, Any]]:
    return [
        item
        for item in _player(state, role_zh)["zones"]["board"]
        if item["card_id"] == card_id
    ]


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
        raise ValueError("unknown summon batch card: {}".format(card_id))
    card = CARDS[card_id]
    game = Game(seed=sum(ord(char) for char in card_id), card_registry=card_registry)
    actor = game.state.active_player
    enemy = 1 - actor
    own = game.state.players[actor]
    opposing = game.state.players[enemy]
    own.hero_health = 22
    opposing.hero_health = 25
    own.deck = ["CS2_120"]
    opposing.deck = ["CS2_172"]
    own.hand = [HandCard(103_000, card_id)]
    opposing.hand = []
    own.board = []
    opposing.board = [Minion(103_010, "CS2_182", 4, 7, 7, summoned_turn=0)]
    own.mana = own.max_mana = 10
    opposing.mana = opposing.max_mana = 10

    target: Optional[TargetRef] = None
    target_description = "无目标"
    if card_id in {"CORE_BAR_801", "CORE_SW_088"}:
        target = TargetRef.hero(actor)
        target_description = "我方英雄"
    if card_id == "CORE_RLK_062":
        own.board = [
            Minion(103_100 + index, "CS2_120", 2, 3, 3, summoned_turn=0)
            for index in range(4)
        ]

    action = Action(ActionType.PLAY, 103_000, target)
    before = review_state_from_observation(game.observation(actor))
    game.apply(action)
    after = review_state_from_observation(game.observation(actor))
    own_before = _player(before, "我方")
    own_after = _player(after, "我方")
    assertions = [
        _assertion(
            "mana",
            "我方法力",
            own_before["resources"]["mana"],
            own_after["resources"]["mana"],
            "支付{}点法力".format(card.cost),
        )
    ]

    if card_id == "CORE_EX1_506":
        token_id = "EX1_506a"
        summoned = _board_cards(after, "我方", token_id)
        assertions.append(
            _assertion(
                "murloc-scout",
                "鱼人斥候数量",
                0,
                len(summoned),
                "战吼额外召唤一个1/1鱼人",
            )
        )
        title = "鱼人猎潮者：战吼召唤鱼人斥候"
        purpose = "核对主随从先入场，随后召唤具有独立实体编号的衍生物。"
        explanation = "若主随从入场后场上已满七个位置，鱼人斥候不会被召唤。"
    elif card_id == "CORE_BAR_801":
        token_id = "BAR_035t"
        summoned = _board_cards(after, "我方", token_id)
        assertions.extend(
            [
                _assertion(
                    "friendly-damage",
                    "我方英雄生命值",
                    own_before["hero"]["health"],
                    own_after["hero"]["health"],
                    "伤害可选择我方角色并造成1点伤害",
                ),
                _assertion(
                    "rush-hyena",
                    "迅捷土狼数量",
                    0,
                    len(summoned),
                    "召唤一个1/1并具有突袭的野兽",
                ),
            ]
        )
        title = "击伤猎物：伤害后召唤突袭土狼"
        purpose = "核对任意角色目标、效果顺序和衍生物突袭标签。"
        explanation = "土狼在召唤回合只能依靠突袭攻击敌方随从，不能攻击敌方英雄。"
    elif card_id == "CORE_BOT_451":
        token_id = "BOT_102t"
        summoned = _board_cards(after, "我方", token_id)
        assertions.extend(
            [
                _assertion(
                    "two-sparks",
                    "火花数量",
                    0,
                    len(summoned),
                    "按顺序召唤两个1/1并具有突袭的元素",
                ),
                _assertion(
                    "overload",
                    "待锁定法力",
                    own_before["resources"]["overload_pending"],
                    own_after["resources"]["overload_pending"],
                    "记录1点过载，留到使用者下回合锁定",
                ),
            ]
        )
        title = "流电爆裂：批量召唤突袭火花并记录过载"
        purpose = "核对多次召唤、元素种族、突袭和过载资源。"
        explanation = "召唤逐个占用场上位置；空间不足时只保留先成功召唤的火花。"
    elif card_id == "CORE_SW_088":
        token_id = "CS2_065"
        summoned = _board_cards(after, "我方", token_id)
        assertions.extend(
            [
                _assertion(
                    "friendly-damage",
                    "我方英雄生命值",
                    own_before["hero"]["health"],
                    own_after["hero"]["health"],
                    "伤害可选择我方角色并造成3点伤害",
                ),
                _assertion(
                    "two-voidwalkers",
                    "虚空行者数量",
                    0,
                    len(summoned),
                    "召唤两个1/3并具有嘲讽的恶魔",
                ),
            ]
        )
        title = "恶魔来袭：伤害后召唤两个嘲讽恶魔"
        purpose = "核对任意角色目标、复数召唤和虚空行者的嘲讽及恶魔标签。"
        explanation = "即使伤害选择我方角色，后续两个召唤效果仍会正常执行。"
    else:
        token_id = card_id
        matching_swarmguards = _board_cards(after, "我方", token_id)
        assertions.append(
            _assertion(
                "two-copies",
                "蛛魔护群守卫数量",
                0,
                len(matching_swarmguards),
                "主随从入场后召唤两个基础复制，合计三个",
            )
        )
        summoned = matching_swarmguards[1:]
        title = "蛛魔护群守卫：召唤两个不会再触发战吼的复制"
        purpose = "核对召唤复制保留基础属性、嘲讽和亡灵种族，但不重复战吼。"
        explanation = "召唤不是从手牌使用；两个复制不会各自再召唤复制。"

    summoned_ids = [item["entity_id"] for item in summoned]
    summoned_cards = [item["card_id"] for item in summoned]
    return {
        "scenario_id": "{}-summon-review-v1".format(card_id.lower().replace("_", "-")),
        "title_zh": title,
        "purpose_zh": purpose,
        "before": before,
        "action": {
            "type": "play_card",
            "actor_player_id": actor,
            "source_entity_id": 103_000,
            "card_id": card_id,
            "target": asdict(target) if target else None,
            "description_zh": "我方使用《{}》，目标为{}。".format(
                card.name, target_description
            ),
            "engine_action": action.to_dict(),
        },
        "after": after,
        "assertions": assertions,
        "special_cases": [
            {
                "kind": "special_tags",
                "summary_zh": "召唤实体和场上位置单独记录。",
                "details": {
                    "entity_id": summoned_ids[0],
                    "card_id": token_id,
                    "tags_before": {
                        "friendly_board_count": len(own_before["zones"]["board"])
                    },
                    "tags_after": {
                        "friendly_board_count": len(own_after["zones"]["board"]),
                        "summoned_entity_ids": summoned_ids,
                        "summoned_card_ids": summoned_cards,
                    },
                    "explanation_zh": explanation,
                },
            }
        ],
    }


__all__ = [
    "AUTHORING_METADATA",
    "CARDS",
    "SCENARIO_CARD_NAMES_ZH",
    "TOKEN_CARDS",
    "build_review_scenario",
]
