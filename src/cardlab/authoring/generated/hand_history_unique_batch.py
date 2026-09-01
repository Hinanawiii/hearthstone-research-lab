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
    TargetRef,
)
from ..review_format import review_state_from_observation

SOURCE_VERSION = "250339"
GENERATED_BY = "codex-gpt-5.6-core-hand-history-unique-batch-v1"

CARDS: Dict[str, CardDef] = {
    "CORE_WON_141": CardDef(
        "CORE_WON_141",
        "展馆茶杯",
        CardType.MINION,
        3,
        3,
        3,
        rarity="COMMON",
        effects=(Effect("random_buff_distinct_races", 3, attack=1, health=1),),
    ),
    "CORE_REV_946": CardDef(
        "CORE_REV_946",
        "蒸汽清洁器",
        CardType.MINION,
        5,
        5,
        5,
        races=("MECHANICAL",),
        rarity="RARE",
        effects=(Effect("destroy_outside_starting_deck"),),
    ),
    "CORE_CFM_670": CardDef(
        "CORE_CFM_670",
        "诺格弗格市长",
        CardType.MINION,
        9,
        5,
        4,
        rarity="LEGENDARY",
        randomizes_character_targets=True,
    ),
    "CORE_TRL_345": CardDef(
        "CORE_TRL_345",
        "卡格瓦，青蛙之神",
        CardType.MINION,
        6,
        4,
        6,
        races=("BEAST",),
        rarity="LEGENDARY",
        effects=(Effect("return_previous_turn_spells"),),
    ),
}

_SOURCE_TEXTS = {
    "CORE_WON_141": "战吼：随机使三个不同类型的友方随从获得+1/+1。",
    "CORE_REV_946": "战吼：摧毁双方玩家牌库中所有套牌之外的牌。",
    "CORE_CFM_670": "所有角色都会随机选择目标。",
    "CORE_TRL_345": "战吼：将你上回合使用的所有法术牌移回你的手牌。",
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
    "CS2_029": "火球术",
    "CS2_023": "奥术智慧",
    "CS2_120": "淡水鳄",
    "CORE_NEW1_022": "恐怖海盗",
    "CORE_GVG_085": "吵吵机器人",
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


def _special_tags(
    card_id: str,
    entity_id: int,
    tags_before: Mapping[str, Any],
    tags_after: Mapping[str, Any],
    explanation_zh: str,
) -> list[Dict[str, Any]]:
    return [
        {
            "kind": "special_tags",
            "summary_zh": "记录跨区域或全局规则需要的隐藏状态。",
            "details": {
                "entity_id": entity_id,
                "card_id": card_id,
                "tags_before": dict(tags_before),
                "tags_after": dict(tags_after),
                "explanation_zh": explanation_zh,
            },
        }
    ]


def build_review_scenario(
    card_id: str, card_registry: Mapping[str, CardDef]
) -> Dict[str, Any]:
    if card_id not in CARDS:
        raise ValueError("unknown hand history unique card: {}".format(card_id))
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
    source_entity_id = 170_000

    if card_id == "CORE_WON_141":
        own.hand = [HandCard(source_entity_id, card_id)]
        own.board = [
            Minion(170_001, "CS2_120", 2, 3, 3, races=("BEAST",), summoned_turn=0),
            Minion(
                170_002,
                "CORE_NEW1_022",
                3,
                3,
                3,
                taunt=True,
                races=("PIRATE",),
                summoned_turn=0,
            ),
            Minion(
                170_003,
                "CORE_GVG_085",
                1,
                2,
                2,
                races=("MECHANICAL",),
                summoned_turn=0,
            ),
        ]
        action = Action(ActionType.PLAY, source_entity_id)
        description = "三个友方随从分别为野兽、海盗和机械，随后打出展馆茶杯。"
    elif card_id == "CORE_REV_946":
        own.hand = [HandCard(source_entity_id, card_id)]
        own.deck = ["CS2_120", "CS2_029"]
        own.deck_outside_starting = [False, True]
        opposing.deck = ["CS2_120", "CS2_023"]
        opposing.deck_outside_starting = [False, True]
        action = Action(ActionType.PLAY, source_entity_id)
        description = "双方牌库各有一张初始牌和一张套牌外生成牌，随后打出蒸汽清洁器。"
    elif card_id == "CORE_CFM_670":
        own.board = [
            Minion(source_entity_id, card_id, 5, 4, 4, summoned_turn=0)
        ]
        own.hand = [HandCard(170_004, "CS2_029")]
        action = Action(ActionType.PLAY, 170_004, TargetRef.hero(enemy))
        description = "诺格弗格市长在场时，声明用火球术攻击敌方英雄。"
    else:
        own.hand = [HandCard(source_entity_id, card_id)]
        own.spells_played_previous_turn = ["CS2_029", "CS2_023"]
        action = Action(ActionType.PLAY, source_entity_id)
        description = "记录显示我方上回合使用过火球术和奥术智慧，随后打出卡格瓦。"

    before = review_state_from_observation(game.observation(actor))
    game.apply(action)
    after = review_state_from_observation(game.observation(actor))
    own_before = _player(before, "我方")
    own_after = _player(after, "我方")
    enemy_before = _player(before, "敌方")
    enemy_after = _player(after, "敌方")

    if card_id == "CORE_WON_141":
        before_stats = [
            [item["attack"], item["health"]]
            for item in own_before["zones"]["board"]
        ]
        after_stats = [
            [item["attack"], item["health"]]
            for item in own_after["zones"]["board"]
            if item["card_id"] != card_id
        ]
        assertions = [
            _assertion(
                "three-distinct-races",
                "三个不同类型随从的属性",
                before_stats,
                after_stats,
                "三个类型各随机选择一个实例，并分别获得+1/+1",
            )
        ]
        special_cases = _special_tags(
            card_id,
            source_entity_id,
            {"eligible_races": ["BEAST", "PIRATE", "MECHANICAL"]},
            {"buffed_count": 3},
            "同一个随从不会被重复选中，同一个类型也不会被重复消费。",
        )
    elif card_id == "CORE_REV_946":
        assertions = [
            _assertion(
                "clean-both-decks",
                "双方牌库数量",
                [
                    own_before["zones"]["deck"]["count"],
                    enemy_before["zones"]["deck"]["count"],
                ],
                [
                    own_after["zones"]["deck"]["count"],
                    enemy_after["zones"]["deck"]["count"],
                ],
                "双方各移除一张套牌创建后加入的牌，保留初始牌",
            )
        ]
        special_cases = [
            {
                "kind": "deck_change",
                "summary_zh": "牌库中的每个卡牌实例单独记录是否来自初始套牌。",
                "details": {
                    "player_id": actor,
                    "before_count": own_before["zones"]["deck"]["count"],
                    "after_count": own_after["zones"]["deck"]["count"],
                    "drawn_count": 0,
                    "added_count": 0,
                    "shuffled_count": 0,
                    "order_changed": False,
                    "known_top_before": [],
                    "known_top_after": [],
                },
            }
        ]
    elif card_id == "CORE_CFM_670":
        resolved_target = game.history[-1]["action"]["target"]
        assertions = [
            _assertion(
                "mayor-random-target",
                "火球术实际目标",
                asdict(TargetRef.hero(enemy)),
                resolved_target,
                "声明合法目标后，由市长从当前可选角色中重新随机选择实际目标",
            )
        ]
        special_cases = _special_tags(
            card_id,
            source_entity_id,
            {"declared_target": asdict(TargetRef.hero(enemy))},
            {"resolved_target": resolved_target},
            "随机目标在动作合法性检查之后、伤害结算之前确定，并写入可复现历史。",
        )
    else:
        returned_ids = [
            item["card_id"] for item in own_after["zones"]["hand"]["cards"]
        ]
        assertions = [
            _assertion(
                "kragwa-return-spells",
                "我方手牌",
                [],
                returned_ids,
                "按上一个我方回合的公开施法历史，将两个法术各生成一张手牌副本",
            )
        ]
        special_cases = _special_tags(
            card_id,
            source_entity_id,
            {"previous_turn_spell_ids": ["CS2_029", "CS2_023"]},
            {"returned_card_ids": returned_ids},
            "历史在每个玩家自己的回合结束时滚动，不会被对手回合覆盖。",
        )

    return {
        "scenario_id": "{}-hand-history-unique-review-v1".format(
            card_id.lower().replace("_", "-")
        ),
        "title_zh": "{}：跨区域状态核验".format(card.name),
        "purpose_zh": "核对套牌来源、回合历史、全局目标改写和不同随从类型。",
        "before": before,
        "action": {
            "type": "play_card_with_state_fixture",
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
