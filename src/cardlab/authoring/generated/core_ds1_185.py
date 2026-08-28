from __future__ import annotations

from typing import Any, Dict

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

CARD = CardDef(
    card_id="CORE_DS1_185",
    name="奥术射击",
    card_type=CardType.SPELL,
    cost=1,
    target_mode=TargetMode.ANY_CHARACTER,
    effects=(Effect("damage", 2),),
)

AUTHORING_METADATA = {
    "source_version": "250339",
    "source_text": "Deal 2 damage.",
    "source_text_zh": "造成2点伤害。",
    "generated_by": "codex-gpt-5.6-sol-pilot-v1",
    "review_status": "awaiting_human_scenario_review",
}

SCENARIO_CARD_NAMES_ZH = {
    "CORE_DS1_185": "奥术射击",
    "CS2_189": "精灵弓箭手",
    "CS2_120": "淡水鳄",
}


def build_review_scenario(card_registry: Dict[str, CardDef]) -> Dict[str, Any]:
    """构造固定局面，供人工核对卡牌实现。"""
    game = Game(seed=185, card_registry=card_registry)
    actor = game.state.active_player
    enemy = 1 - actor
    own = game.state.players[actor]
    opposing = game.state.players[enemy]
    own.hero_health = 30
    own.mana = 1
    own.max_mana = 1
    own.hand = [HandCard(1850, CARD.card_id)]
    own.board = [Minion(1851, "CS2_120", 2, 3, 3)]
    opposing.hero_health = 30
    opposing.board = [Minion(1852, "CS2_189", 1, 1, 1)]

    target = TargetRef.hero(actor)
    action = Action(ActionType.PLAY, source_id=1850, target=target)
    before = review_state_from_observation(game.observation(actor))
    game.apply(action)
    after = review_state_from_observation(game.observation(actor))
    return {
        "scenario_id": "core-ds1-185-friendly-hero-target-v1",
        "title_zh": "奥术射击：选择我方英雄",
        "purpose_zh": "核对该法术可以选择我方英雄，并且只对选中的角色造成2点伤害。",
        "before": before,
        "action": {
            "type": "play_card",
            "actor_player_id": actor,
            "source_entity_id": 1850,
            "card_id": CARD.card_id,
            "target": {
                "player_id": actor,
                "kind": "hero",
                "entity_id": None,
                "description_zh": "我方英雄",
            },
            "description_zh": "我方使用《奥术射击》，选择我方英雄作为目标。",
            "engine_action": action.to_dict(),
        },
        "after": after,
        "assertions": [
            {
                "assertion_id": "friendly-hero-is-legal-target",
                "subject_zh": "我方英雄生命值",
                "before": 30,
                "after": 28,
                "expected_zh": "我方英雄是合法目标，受到2点伤害",
            },
            {
                "assertion_id": "enemy-hero-untouched",
                "subject_zh": "敌方英雄生命值",
                "before": 30,
                "after": 30,
                "expected_zh": "没有被选中，不受到伤害",
            },
            {
                "assertion_id": "friendly-minion-untouched",
                "subject_zh": "我方随从",
                "before": "在场，生命值3",
                "after": "在场，生命值3",
                "expected_zh": "没有被选中，不受到伤害",
            },
            {
                "assertion_id": "enemy-minion-untouched",
                "subject_zh": "敌方随从",
                "before": "在场，生命值1",
                "after": "在场，生命值1",
                "expected_zh": "没有被选中，不受到伤害",
            },
            {
                "assertion_id": "mana-spent",
                "subject_zh": "我方法力值",
                "before": 1,
                "after": 0,
                "expected_zh": "支付1点法力值",
            },
        ],
        "special_cases": [],
    }
