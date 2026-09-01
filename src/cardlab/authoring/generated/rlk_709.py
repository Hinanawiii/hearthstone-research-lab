from __future__ import annotations

from typing import Any, Dict

from ...engine import Game
from ...model import Action, ActionType, CardDef, CardType, Effect, HandCard, Minion
from ..review_format import review_state_from_observation

CARD = CardDef(
    card_id="RLK_709",
    name="冷酷严冬",
    card_type=CardType.SPELL,
    cost=4,
    runes=("FROST",),
    effects=(
        Effect("damage_all", 2, target="enemy_characters"),
        Effect("draw", 1, target="owner"),
    ),
)

AUTHORING_METADATA = {
    "source_version": "250339",
    "source_text": "Deal 2 damage to all enemies. Draw a card.",
    "source_text_zh": "对所有敌人造成2点伤害。抽一张牌。",
    "generated_by": "codex-authoring-v1",
    "review_status": "awaiting_human_scenario_review",
}

SCENARIO_CARD_NAMES_ZH = {
    "RLK_709": "冷酷严冬",
    "CS2_231": "小精灵",
    "CS2_189": "精灵弓箭手",
    "CS2_120": "淡水鳄",
}


def build_review_scenario(card_registry: Dict[str, CardDef]) -> Dict[str, Any]:
    """Return a fixed-format scenario for human implementation review."""
    game = Game(seed=709, card_registry=card_registry)
    actor = game.state.active_player
    enemy = 1 - actor
    own = game.state.players[actor]
    opposing = game.state.players[enemy]
    own.mana = 10
    own.max_mana = 10
    own.hand = [HandCard(7009, CARD.card_id)]
    own.deck = ["CS2_231"]
    own.board = [Minion(7010, "CS2_120", 2, 1, 3)]
    opposing.hero_health = 30
    opposing.board = [
        Minion(7011, "CS2_189", 1, 1, 1),
        Minion(7012, "CS2_120", 2, 3, 3),
    ]

    action = Action(ActionType.PLAY, source_id=7009)
    before = review_state_from_observation(
        game.observation(actor), own_known_deck_top=["CS2_231"]
    )
    game.apply(action)
    after = review_state_from_observation(game.observation(actor))
    return {
        "scenario_id": "rlk-709-basic-resolution-v1",
        "title_zh": "冷酷严冬：群体伤害后抽牌",
        "purpose_zh": "核对所有敌人同时受到2点伤害，友方场面不受影响，并在伤害结算后抽一张牌。",
        "before": before,
        "action": {
            "type": "play_card",
            "actor_player_id": actor,
            "source_entity_id": 7009,
            "card_id": CARD.card_id,
            "target": None,
            "description_zh": "我方使用《冷酷严冬》，不选择目标。",
            "engine_action": action.to_dict(),
        },
        "after": after,
        "assertions": [
            {
                "assertion_id": "enemy-hero-damage",
                "subject_zh": "敌方英雄生命值",
                "before": 30,
                "after": 28,
                "expected_zh": "受到2点伤害",
            },
            {
                "assertion_id": "enemy-one-health-minion",
                "subject_zh": "敌方1血随从",
                "before": "在场，生命值1",
                "after": "离场",
                "expected_zh": "受到2点伤害后死亡",
            },
            {
                "assertion_id": "enemy-three-health-minion",
                "subject_zh": "敌方3血随从",
                "before": "在场，生命值3",
                "after": "在场，生命值1",
                "expected_zh": "受到2点伤害后存活",
            },
            {
                "assertion_id": "friendly-minion-untouched",
                "subject_zh": "友方1血随从",
                "before": "在场，生命值1",
                "after": "在场，生命值1",
                "expected_zh": "不属于敌人，不受到伤害",
            },
            {
                "assertion_id": "mana-spent",
                "subject_zh": "我方法力值",
                "before": 10,
                "after": 6,
                "expected_zh": "支付4点法力值",
            },
            {
                "assertion_id": "card-drawn",
                "subject_zh": "我方抽牌结果",
                "before": "牌库顶为CS2_231",
                "after": "CS2_231进入手牌",
                "expected_zh": "伤害结算后抽一张牌",
            },
        ],
        "special_cases": [
            {
                "kind": "deck_change",
                "summary_zh": "发生牌库变更：我方抽取1张牌，牌库由1张变为0张；没有洗牌，剩余牌序未被重排。",
                "details": {
                    "player_id": actor,
                    "before_count": 1,
                    "after_count": 0,
                    "drawn_count": 1,
                    "added_count": 0,
                    "shuffled_count": 0,
                    "order_changed": False,
                    "known_top_before": ["CS2_231"],
                    "known_top_after": [],
                },
            }
        ],
    }
