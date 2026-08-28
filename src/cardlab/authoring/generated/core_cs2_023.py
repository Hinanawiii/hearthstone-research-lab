from __future__ import annotations

from typing import Any, Dict

from ...engine import Game
from ...model import Action, ActionType, CardDef, CardType, Effect, HandCard
from ..review_format import review_state_from_observation

CARD = CardDef(
    card_id="CORE_CS2_023",
    name="奥术智慧",
    card_type=CardType.SPELL,
    cost=3,
    effects=(Effect("draw", 2, target="owner"),),
)

AUTHORING_METADATA = {
    "source_version": "250339",
    "source_text": "抽两张牌。",
    "source_text_zh": "抽两张牌。",
    "generated_by": "codex-gpt-5.6-sol-pilot-v1",
    "review_status": "awaiting_human_scenario_review",
}

SCENARIO_CARD_NAMES_ZH = {
    "CORE_CS2_023": "奥术智慧",
    "CS2_120": "淡水鳄",
    "CS2_231": "小精灵",
    "CS2_189": "精灵弓箭手",
    "CS1_042": "闪金镇步兵",
}


def build_review_scenario(card_registry: Dict[str, CardDef]) -> Dict[str, Any]:
    """构造一个可人工核对连续抽牌顺序的固定局面。"""
    game = Game(seed=23, card_registry=card_registry)
    actor = game.state.active_player
    own = game.state.players[actor]
    own.mana = 5
    own.max_mana = 5
    own.hand = [
        HandCard(2300, CARD.card_id),
        HandCard(2301, "CS2_120"),
    ]
    # 引擎从列表尾端抽牌，因此实际牌库顶依次为小精灵、精灵弓箭手、闪金镇步兵。
    own.deck = ["CS1_042", "CS2_189", "CS2_231"]

    action = Action(ActionType.PLAY, source_id=2300)
    before = review_state_from_observation(
        game.observation(actor),
        own_known_deck_top=["CS2_231", "CS2_189", "CS1_042"],
    )
    game.apply(action)
    after = review_state_from_observation(
        game.observation(actor),
        own_known_deck_top=["CS1_042"],
    )
    return {
        "scenario_id": "core-cs2-023-ordered-double-draw-v1",
        "title_zh": "奥术智慧：连续抽取两张已知牌",
        "purpose_zh": (
            "核对两次抽牌的先后顺序：先抽小精灵，再抽精灵弓箭手；"
            "闪金镇步兵不应被抽走，结算后仍是牌库顶。"
        ),
        "before": before,
        "action": {
            "type": "play_card",
            "actor_player_id": actor,
            "source_entity_id": 2300,
            "card_id": CARD.card_id,
            "target": None,
            "description_zh": "我方使用《奥术智慧》，不选择目标。",
            "engine_action": action.to_dict(),
        },
        "after": after,
        "assertions": [
            {
                "assertion_id": "mana-spent",
                "subject_zh": "我方法力值",
                "before": 5,
                "after": 2,
                "expected_zh": "支付3点法力值",
            },
            {
                "assertion_id": "first-card-drawn",
                "subject_zh": "第一次抽牌",
                "before": "牌库顶是CS2_231",
                "after": "CS2_231先进入手牌",
                "expected_zh": "先抽到小精灵",
            },
            {
                "assertion_id": "second-card-drawn",
                "subject_zh": "第二次抽牌",
                "before": "第一张抽走后，牌库顶是CS2_189",
                "after": "CS2_189随后进入手牌",
                "expected_zh": "再抽到精灵弓箭手",
            },
            {
                "assertion_id": "hand-order-and-count",
                "subject_zh": "我方手牌结果",
                "before": "淡水鳄、奥术智慧，共2张",
                "after": "淡水鳄、小精灵、精灵弓箭手，共3张",
                "expected_zh": "奥术智慧离开手牌，两张抽到的牌按抽取顺序追加，手牌净增加1张",
            },
            {
                "assertion_id": "remaining-deck-top",
                "subject_zh": "结算后的牌库顶",
                "before": "第三张已知牌是CS1_042",
                "after": "牌库顶是CS1_042",
                "expected_zh": "闪金镇步兵未被抽取，仍在牌库顶",
            },
        ],
        "special_cases": [
            {
                "kind": "deck_change",
                "summary_zh": (
                    "我方先抽小精灵，再抽精灵弓箭手，牌库由3张变为1张。"
                    "没有卡牌洗入，牌序也没有重排；剩下的闪金镇步兵成为牌库顶。"
                ),
                "details": {
                    "player_id": actor,
                    "before_count": 3,
                    "after_count": 1,
                    "drawn_count": 2,
                    "added_count": 0,
                    "shuffled_count": 0,
                    "order_changed": False,
                    "known_top_before": ["CS2_231", "CS2_189", "CS1_042"],
                    "known_top_after": ["CS1_042"],
                },
            }
        ],
    }
