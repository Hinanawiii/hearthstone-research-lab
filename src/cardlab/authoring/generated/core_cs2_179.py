from __future__ import annotations

from typing import Any, Dict, List

from ...engine import Game
from ...model import Action, ActionType, CardDef, CardType, HandCard, Minion, TargetRef
from ..review_format import review_state_from_observation

CARD = CardDef(
    card_id="CORE_CS2_179",
    name="森金持盾卫士",
    card_type=CardType.MINION,
    cost=4,
    attack=3,
    health=5,
    taunt=True,
)

AUTHORING_METADATA = {
    "source_version": "250339",
    "source_text": "嘲讽",
    "source_text_zh": "嘲讽",
    "generated_by": "codex-gpt-5.6-sol-pilot-v1",
    "review_status": "awaiting_human_scenario_review",
}

SCENARIO_CARD_NAMES_ZH = {
    "CORE_CS2_179": "森金持盾卫士",
    "CS2_231": "小精灵",
    "CS2_120": "淡水鳄",
}


def _enemy_attack_targets_after_turn_passes(game: Game, enemy: int) -> List[TargetRef]:
    probe = game.clone()
    probe.apply(Action.end_turn())
    return [
        action.target
        for action in probe.legal_actions(enemy)
        if action.action_type == ActionType.ATTACK and action.target is not None
    ]


def build_review_scenario(card_registry: Dict[str, CardDef]) -> Dict[str, Any]:
    """返回供人工核对随从进场状态与嘲讽限制的固定局面。"""
    game = Game(seed=179, card_registry=card_registry)
    actor = game.state.active_player
    enemy = 1 - actor
    own = game.state.players[actor]
    opposing = game.state.players[enemy]
    own.mana = 6
    own.max_mana = 6
    own.hand = [HandCard(17901, CARD.card_id)]
    own.deck = ["CS2_231"]
    own.board = [Minion(17902, "CS2_231", 1, 1, 1)]
    opposing.deck = ["CS2_231"]
    opposing.board = [Minion(17903, "CS2_120", 2, 3, 3)]

    targets_before = _enemy_attack_targets_after_turn_passes(game, enemy)
    action = Action(ActionType.PLAY, source_id=17901)
    before = review_state_from_observation(game.observation(actor))
    game.apply(action)
    after = review_state_from_observation(game.observation(actor))

    summoned = next(minion for minion in own.board if minion.card_id == CARD.card_id)
    immediate_attack_sources = {
        legal.source_id
        for legal in game.legal_actions(actor)
        if legal.action_type == ActionType.ATTACK
    }
    targets_after = _enemy_attack_targets_after_turn_passes(game, enemy)

    expected_targets_before = {
        TargetRef.hero(actor),
        TargetRef.minion(actor, 17902),
    }
    expected_targets_after = {TargetRef.minion(actor, summoned.entity_id)}
    if set(targets_before) != expected_targets_before:
        raise RuntimeError("打出前的攻击目标探针与预期不符")
    if summoned.entity_id in immediate_attack_sources:
        raise RuntimeError("森金持盾卫士在进场回合不应能够攻击")
    if set(targets_after) != expected_targets_after:
        raise RuntimeError("嘲讽生效后的攻击目标探针与预期不符")

    return {
        "scenario_id": "core-cs2-179-taunt-entry-v1",
        "title_zh": "森金持盾卫士：进场状态与嘲讽限制",
        "purpose_zh": (
            "核对支付4点法力后生成一个3攻5血并带有嘲讽的随从；"
            "它在进场回合不能攻击，敌方随从下一回合只能先攻击它。"
        ),
        "before": before,
        "action": {
            "type": "play_card",
            "actor_player_id": actor,
            "source_entity_id": 17901,
            "card_id": CARD.card_id,
            "target": None,
            "description_zh": "我方支付4点法力，打出《森金持盾卫士》，不选择目标。",
            "engine_action": action.to_dict(),
        },
        "after": after,
        "assertions": [
            {
                "assertion_id": "mana-spent",
                "subject_zh": "我方法力值",
                "before": 6,
                "after": 2,
                "expected_zh": "打出这张4费随从牌后消耗4点法力",
            },
            {
                "assertion_id": "minion-entered-board",
                "subject_zh": "森金持盾卫士的场上实体",
                "before": "不在场",
                "after": "在场，3点攻击力、5点生命值",
                "expected_zh": "以完整的3攻5血状态进入我方战场",
            },
            {
                "assertion_id": "taunt-active",
                "subject_zh": "森金持盾卫士的嘲讽",
                "before": "不在场",
                "after": "嘲讽已生效",
                "expected_zh": "进场后立即具有嘲讽",
            },
            {
                "assertion_id": "summoning-sickness",
                "subject_zh": "森金持盾卫士本回合的攻击资格",
                "before": "尚未打出",
                "after": "不能攻击",
                "expected_zh": "没有冲锋，因此进场回合不能攻击",
            },
            {
                "assertion_id": "taunt-target-restriction",
                "subject_zh": "敌方淡水鳄下一回合的攻击目标",
                "before": "可攻击我方英雄或小精灵",
                "after": "只能攻击森金持盾卫士",
                "expected_zh": "存活的嘲讽随从会挡住英雄和其他随从",
            },
        ],
        "special_cases": [],
    }
