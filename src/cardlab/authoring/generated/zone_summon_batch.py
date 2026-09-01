from __future__ import annotations

from typing import Any, Dict, Mapping

from ...engine import Game
from ...model import Action, ActionType, CardDef, CardType, Effect, HandCard, Minion
from ..review_format import review_state_from_observation
from .summon_batch import CARDS as SUMMON_FIXTURE_CARDS

SOURCE_VERSION = "250339"
GENERATED_BY = "codex-gpt-5.6-core-zone-summon-batch-v1"

CARDS: Dict[str, CardDef] = {
    "CORE_CFM_790": CardDef(
        "CORE_CFM_790",
        "卑劣的脏鼠",
        CardType.MINION,
        2,
        2,
        6,
        taunt=True,
        effects=(Effect("summon_random_opponent_hand_minion", 1),),
    ),
    "CORE_SCH_181": CardDef(
        "CORE_SCH_181",
        "高阶女巫维洛",
        CardType.MINION,
        8,
        5,
        5,
        effects=(Effect("summon_random_demon_from_hand_and_deck", 1),),
    ),
    "CORE_DAL_575": CardDef(
        "CORE_DAL_575",
        "卡德加",
        CardType.MINION,
        2,
        2,
        2,
        summon_multiplier=2,
    ),
}

_SOURCE_TEXTS = {
    "CORE_CFM_790": "嘲讽，战吼：使你的对手随机从手牌中召唤一个随从。",
    "CORE_SCH_181": "战吼：随机从你的手牌和牌库中召唤一个恶魔。",
    "CORE_DAL_575": "你的召唤随从的卡牌召唤数量翻倍。",
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
    "CORE_BOT_451": "流电爆裂",
    "BOT_102t": "火花",
    "CS2_029": "火球术",
    "CS2_065": "虚空行者",
    "CS2_120": "淡水鳄",
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
        raise ValueError("unknown zone summon batch card: {}".format(card_id))
    registry = dict(card_registry)
    if card_id == "CORE_DAL_575":
        registry["CORE_BOT_451"] = SUMMON_FIXTURE_CARDS["CORE_BOT_451"]
    card = CARDS[card_id]
    game = Game(seed=sum(ord(char) for char in card_id), card_registry=registry)
    actor = game.state.active_player
    enemy = 1 - actor
    own = game.state.players[actor]
    opposing = game.state.players[enemy]
    own.mana = own.max_mana = 10
    opposing.mana = opposing.max_mana = 10
    own.hand = [HandCard(117_000, card_id)]
    opposing.hand = []
    own.board = []
    opposing.board = []
    own.deck = ["CS2_120"]
    opposing.deck = ["CS2_120"]

    if card_id == "CORE_CFM_790":
        opposing.hand = [
            HandCard(117_010, "CS2_120", attack_bonus=1, health_bonus=2),
            HandCard(117_011, "CS2_029"),
        ]
        action = Action(ActionType.PLAY, 117_000)
        description = "我方使用《卑劣的脏鼠》，敌方手牌中有一张随从和一张法术。"
    elif card_id == "CORE_SCH_181":
        own.hand.extend(
            [HandCard(117_020, "CS2_065"), HandCard(117_021, "CS2_029")]
        )
        own.deck = ["CS2_120", "CS2_065"]
        action = Action(ActionType.PLAY, 117_000)
        description = "我方使用《高阶女巫维洛》，手牌和牌库中各有一张恶魔。"
    else:
        own.board = [Minion(117_030, card_id, 2, 2, 2, summoned_turn=0)]
        own.hand = [HandCard(117_031, "CORE_BOT_451")]
        action = Action(ActionType.PLAY, 117_031)
        description = "卡德加在场时，我方使用召唤两个火花的《流电爆裂》。"

    before = review_state_from_observation(game.observation(actor))
    game.apply(action)
    after = review_state_from_observation(game.observation(actor))
    own_before = _player(before, "我方")
    own_after = _player(after, "我方")
    opposing_before = _player(before, "敌方")
    opposing_after = _player(after, "敌方")
    assertions = []

    if card_id == "CORE_CFM_790":
        enemy_board = opposing_after["zones"]["board"]
        assertions.extend(
            [
                _assertion(
                    "dirty-rat-body",
                    "我方脏鼠",
                    0,
                    len(own_after["zones"]["board"]),
                    "2/6嘲讽随从先进入我方场上",
                ),
                _assertion(
                    "opponent-hand-summon",
                    "敌方被拉出的随从",
                    [],
                    [
                        [item["card_id"], item["attack"], item["health"]]
                        for item in enemy_board
                    ],
                    "只从敌方手牌的随从候选中随机选择，并保留手牌中的+1/+2加成",
                ),
            ]
        )
        result_cards = [item["card_id"] for item in enemy_board]
        result_entities = [item["entity_id"] for item in enemy_board]
        explanation = "从手牌召唤不是使用该牌，因此被拉出的随从不会触发战吼。"
    elif card_id == "CORE_SCH_181":
        own_board = own_after["zones"]["board"]
        demons = [item for item in own_board if item["card_id"] == "CS2_065"]
        assertions.extend(
            [
                _assertion(
                    "summon-hand-demon",
                    "手牌恶魔",
                    own_before["zones"]["hand"]["count"],
                    own_after["zones"]["hand"]["count"],
                    "从手牌移出并召唤一张随机恶魔，非法术",
                ),
                _assertion(
                    "summon-deck-demon",
                    "牌库恶魔",
                    own_before["zones"]["deck"]["count"],
                    own_after["zones"]["deck"]["count"],
                    "再从牌库移出并召唤一张随机恶魔，非恶魔留在牌库",
                ),
                _assertion(
                    "two-demons",
                    "召唤的虚空行者",
                    0,
                    len(demons),
                    "手牌和牌库各召唤一个1/3嘲讽恶魔",
                ),
            ]
        )
        result_cards = [item["card_id"] for item in own_board]
        result_entities = [item["entity_id"] for item in own_board]
        explanation = "两个区域分别建立候选池；场地不足时，后续区域不会移除卡牌。"
    else:
        sparks = [
            item
            for item in own_after["zones"]["board"]
            if item["card_id"] == "BOT_102t"
        ]
        assertions.extend(
            [
                _assertion(
                    "double-summon",
                    "火花数量",
                    0,
                    len(sparks),
                    "原本召唤两个，卡德加使其翻倍为四个",
                ),
                _assertion(
                    "overload-once",
                    "待锁定法力",
                    own_before["resources"]["overload_pending"],
                    own_after["resources"]["overload_pending"],
                    "只把召唤数量翻倍，法术费用和过载仍结算一次",
                ),
            ]
        )
        result_cards = [item["card_id"] for item in sparks]
        result_entities = [item["entity_id"] for item in sparks]
        explanation = "多个卡德加的翻倍效果相乘，但所有召唤仍受七个场上位置限制。"

    return {
        "scenario_id": "{}-zone-summon-review-v1".format(
            card_id.lower().replace("_", "-")
        ),
        "title_zh": "{}：跨区域召唤核验".format(card.name),
        "purpose_zh": "核对召唤与使用的区别、手牌/牌库移动和召唤数量倍率。",
        "before": before,
        "action": {
            "type": "play_card_with_summon_fixture",
            "actor_player_id": actor,
            "source_entity_id": action.source_id,
            "card_id": card_id,
            "target": None,
            "description_zh": description,
            "engine_action": action.to_dict(),
        },
        "after": after,
        "assertions": assertions,
        "special_cases": [
            {
                "kind": "special_tags",
                "summary_zh": "区域来源和召唤实体单独记录。",
                "details": {
                    "entity_id": result_entities[0] if result_entities else action.source_id,
                    "card_id": result_cards[0] if result_cards else card_id,
                    "tags_before": {
                        "friendly_hand_count": own_before["zones"]["hand"]["count"],
                        "enemy_hand_count": opposing_before["zones"]["hand"]["count"],
                    },
                    "tags_after": {
                        "friendly_hand_count": own_after["zones"]["hand"]["count"],
                        "enemy_hand_count": opposing_after["zones"]["hand"]["count"],
                        "result_card_ids": result_cards,
                        "result_entity_ids": result_entities,
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
    "build_review_scenario",
]
