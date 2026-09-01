from __future__ import annotations

from typing import Any, Dict, Mapping

from ...engine import Game
from ...model import Action, ActionType, CardDef, CardType, Effect, HandCard
from ..review_format import review_state_from_observation

SOURCE_VERSION = "250339"
GENERATED_BY = "codex-gpt-5.6-core-random-summon-batch-v1"

TOKEN_CARDS: Dict[str, CardDef] = {
    "CORE_FP1_011": CardDef(
        "CORE_FP1_011",
        "结网蛛",
        CardType.MINION,
        1,
        1,
        1,
        races=("BEAST",),
        deathrattle_effects=(Effect("add_random_race_to_hand", 1, race="BEAST"),),
        collectible=False,
    ),
    "NEW1_032": CardDef(
        "NEW1_032",
        "米莎",
        CardType.MINION,
        3,
        4,
        4,
        taunt=True,
        races=("BEAST",),
        collectible=False,
    ),
    "NEW1_033": CardDef(
        "NEW1_033",
        "雷欧克",
        CardType.MINION,
        3,
        2,
        4,
        races=("BEAST",),
        aura_attack=1,
        collectible=False,
    ),
    "NEW1_034": CardDef(
        "NEW1_034",
        "霍弗",
        CardType.MINION,
        3,
        4,
        2,
        charge=True,
        races=("BEAST",),
        collectible=False,
    ),
}

_ANIMAL_COMPANIONS = ("NEW1_032", "NEW1_033", "NEW1_034")

CARDS: Dict[str, CardDef] = {
    "CORE_AT_062": CardDef(
        "CORE_AT_062",
        "天降蛛群",
        CardType.SPELL,
        3,
        effects=(Effect("summon", 3, card_id="CORE_FP1_011"),),
    ),
    "CORE_NEW1_031": CardDef(
        "CORE_NEW1_031",
        "动物伙伴",
        CardType.SPELL,
        3,
        effects=(Effect("summon_random", 1, card_ids=_ANIMAL_COMPANIONS),),
    ),
    "CORE_OG_211": CardDef(
        "CORE_OG_211",
        "兽群呼唤",
        CardType.SPELL,
        8,
        effects=(Effect("summon_sequence", card_ids=_ANIMAL_COMPANIONS),),
    ),
    "CORE_BOT_256": CardDef(
        "CORE_BOT_256",
        "星术师",
        CardType.MINION,
        7,
        5,
        5,
        effects=(Effect("summon_random_hand_cost", 1),),
    ),
    "CORE_WW_374": CardDef(
        "CORE_WW_374",
        "凉心农场",
        CardType.SPELL,
        3,
        runes=("UNHOLY",),
        spends_corpses=True,
        effects=(Effect("summon_random_cost_spend_corpses", 8),),
    ),
    "CORE_LOOT_309": CardDef(
        "CORE_LOOT_309",
        "橡树的召唤",
        CardType.SPELL,
        4,
        effects=(
            Effect("armor", 6, target="owner_hero"),
            Effect("summon_random_deck_minion_cost_at_most", 4),
        ),
    ),
}

_SOURCE_TEXTS = {
    "CORE_AT_062": "召唤三只1/1并具有“亡语：随机获取一张野兽牌”的 结网蛛。",
    "CORE_NEW1_031": "随机召唤一个野兽伙伴。",
    "CORE_OG_211": "召唤全部三个动物伙伴。",
    "CORE_BOT_256": "战吼：随机召唤一个法力值消耗等同于你手牌数量的随从。",
    "CORE_WW_374": "消耗最多 8份残骸，随机召唤一个法力值消耗相同的随从。",
    "CORE_LOOT_309": "获得6点护甲值。从你的牌库中召唤一个法力值消耗小于或等于（4）点的随从。",
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
    "CS2_182": "冰风雪人",
    "CS2_200": "石拳食人魔",
    "CS2_231": "小精灵",
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
        raise ValueError("unknown random summon batch card: {}".format(card_id))
    card = CARDS[card_id]
    game = Game(seed=sum(ord(char) for char in card_id), card_registry=card_registry)
    actor = game.state.active_player
    own = game.state.players[actor]
    opposing = game.state.players[1 - actor]
    own.mana = own.max_mana = 10
    opposing.mana = opposing.max_mana = 10
    own.hand = [HandCard(115_000, card_id)]
    opposing.hand = []
    own.board = []
    opposing.board = []
    own.deck = ["CS2_182"]
    opposing.deck = ["CS2_120"]
    own.corpses = 0

    if card_id == "CORE_BOT_256":
        own.hand.extend(HandCard(115_010 + index, "CS2_231") for index in range(6))
    elif card_id == "CORE_WW_374":
        own.corpses = 4
    elif card_id == "CORE_LOOT_309":
        own.deck = ["CS2_200", "CS2_120"]

    action = Action(ActionType.PLAY, 115_000)
    before = review_state_from_observation(game.observation(actor))
    game.apply(action)
    after = review_state_from_observation(game.observation(actor))
    own_before = _player(before, "我方")
    own_after = _player(after, "我方")
    board_before = own_before["zones"]["board"]
    board_after = own_after["zones"]["board"]
    result_cards = [item["card_id"] for item in board_after]
    result_entities = [item["entity_id"] for item in board_after]
    assertions = [
        _assertion(
            "mana",
            "我方法力",
            own_before["resources"]["mana"],
            own_after["resources"]["mana"],
            "支付{}点法力".format(card.cost),
        )
    ]

    if card_id == "CORE_AT_062":
        webspinners = [item for item in board_after if item["card_id"] == "CORE_FP1_011"]
        assertions.append(
            _assertion(
                "three-webspinners",
                "结网蛛数量",
                0,
                len(webspinners),
                "召唤三只各自带亡语的1/1野兽",
            )
        )
        explanation = "每只结网蛛分别保存亡语；死亡时从当前已实现的可收集野兽池随机置入一张牌。"
    elif card_id == "CORE_NEW1_031":
        assertions.append(
            _assertion(
                "one-animal-companion",
                "野兽伙伴",
                [],
                result_cards,
                "米莎、雷欧克和霍弗中随机召唤一个",
            )
        )
        explanation = "随机池固定为三个野兽伙伴，使用场景种子复现实测结果。"
    elif card_id == "CORE_OG_211":
        assertions.append(
            _assertion(
                "all-animal-companions",
                "三个野兽伙伴",
                [],
                result_cards,
                "按米莎、雷欧克、霍弗各召唤一个",
            )
        )
        explanation = "雷欧克只为其他随从提供+1攻击力；米莎保留嘲讽，霍弗保留冲锋。"
    elif card_id == "CORE_BOT_256":
        summoned = [item for item in board_after if item["card_id"] != card_id]
        assertions.append(
            _assertion(
                "summon-hand-count-cost",
                "战吼召唤的随从",
                [],
                [item["card_id"] for item in summoned],
                "星术师离开手牌后剩6张牌，因此随机召唤一个6费随从",
            )
        )
        explanation = "手牌数量在星术师被使用并离开手牌后读取；随机池只含当前注册的可收集随从。"
    elif card_id == "CORE_WW_374":
        assertions.extend(
            [
                _assertion(
                    "spend-four-corpses",
                    "我方残骸",
                    own_before["resources"]["corpses"],
                    own_after["resources"]["corpses"],
                    "当前只有4份残骸，因此全部消耗",
                ),
                _assertion(
                    "summon-four-cost",
                    "召唤结果",
                    [],
                    result_cards,
                    "随机召唤一个4费可收集随从",
                ),
            ]
        )
        explanation = "先锁定最多8份残骸的实际消耗量，再从相同费用的随从池随机选择。"
    else:
        assertions.extend(
            [
                _assertion(
                    "gain-six-armor",
                    "我方英雄护甲",
                    own_before["hero"]["armor"],
                    own_after["hero"]["armor"],
                    "获得6点护甲",
                ),
                _assertion(
                    "summon-low-cost-from-deck",
                    "牌库与场上",
                    [own_before["zones"]["deck"]["count"], []],
                    [own_after["zones"]["deck"]["count"], result_cards],
                    "从牌库移出并召唤唯一符合条件的2费淡水鳄，6费牌留在牌库",
                ),
            ]
        )
        explanation = "候选只来自我方牌库中的随从；场上已满时不会移除牌库中的牌。"

    return {
        "scenario_id": "{}-random-summon-review-v1".format(
            card_id.lower().replace("_", "-")
        ),
        "title_zh": "{}：召唤来源与随机池核验".format(card.name),
        "purpose_zh": "核对召唤数量、候选池、费用读取时点及区域移动。",
        "before": before,
        "action": {
            "type": "play_card",
            "actor_player_id": actor,
            "source_entity_id": 115_000,
            "card_id": card_id,
            "target": None,
            "description_zh": "我方使用《{}》。".format(card.name),
            "engine_action": action.to_dict(),
        },
        "after": after,
        "assertions": assertions,
        "special_cases": [
            {
                "kind": "special_tags",
                "summary_zh": "随机池和召唤实体使用固定种子记录。",
                "details": {
                    "entity_id": result_entities[-1] if result_entities else 115_000,
                    "card_id": result_cards[-1] if result_cards else card_id,
                    "tags_before": {
                        "friendly_board_count": len(board_before),
                        "corpses": own_before["resources"]["corpses"],
                    },
                    "tags_after": {
                        "friendly_board_count": len(board_after),
                        "result_card_ids": result_cards,
                        "result_entity_ids": result_entities,
                        "corpses": own_after["resources"]["corpses"],
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
