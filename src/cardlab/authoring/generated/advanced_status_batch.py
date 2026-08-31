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
GENERATED_BY = "codex-gpt-5.6-core-advanced-status-batch-v1"

CARDS: Dict[str, CardDef] = {
    "CORE_CS2_024": CardDef(
        "CORE_CS2_024",
        "寒冰箭",
        CardType.SPELL,
        2,
        target_mode=TargetMode.ANY_CHARACTER,
        effects=(Effect("damage", 3), Effect("freeze")),
    ),
    "CORE_CS2_028": CardDef(
        "CORE_CS2_028",
        "暴风雪",
        CardType.SPELL,
        6,
        effects=(
            Effect("damage_all", 2, target="enemy_minions"),
            Effect("freeze_all", target="enemy_minions"),
        ),
    ),
    "CORE_CS2_188": CardDef(
        "CORE_CS2_188",
        "叫嚣的中士",
        CardType.MINION,
        1,
        1,
        1,
        target_mode=TargetMode.ANY_MINION,
        effects=(Effect("temporary_buff", target="selected", attack=2),),
    ),
    "CORE_UNG_205": CardDef(
        "CORE_UNG_205",
        "冰川裂片",
        CardType.MINION,
        1,
        2,
        1,
        target_mode=TargetMode.ENEMY_CHARACTER,
        effects=(Effect("freeze"),),
        races=("ELEMENTAL",),
    ),
    "CORE_EX1_059": CardDef(
        "CORE_EX1_059",
        "疯狂的炼金师",
        CardType.MINION,
        2,
        2,
        2,
        target_mode=TargetMode.ANY_MINION,
        effects=(Effect("swap_stats"),),
        races=("UNDEAD",),
    ),
}

_SOURCE_TEXTS = {
    "CORE_CS2_024": "对一个角色造成3点伤害，并使其冻结。",
    "CORE_CS2_028": "对所有敌方随从造成2点伤害，并使其冻结。",
    "CORE_CS2_188": "战吼：在本回合中，使一个随从获得+2攻击力。",
    "CORE_UNG_205": "战吼： 冻结一个敌人。",
    "CORE_EX1_059": "战吼： 使一个随从的攻击力和生命值互换。",
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
    "CS2_120": "淡水鳄",
    "CS2_172": "血沼迅猛龙",
    "CS2_182": "冰风雪人",
}


def _player(state: Mapping[str, Any], role_zh: str) -> Mapping[str, Any]:
    return next(item for item in state["players"] if item["role_zh"] == role_zh)


def _minion(state: Mapping[str, Any], role_zh: str, card_id: str) -> Mapping[str, Any]:
    player = _player(state, role_zh)
    return next(item for item in player["zones"]["board"] if item["card_id"] == card_id)


def _card_present(state: Mapping[str, Any], role_zh: str, card_id: str) -> bool:
    player = _player(state, role_zh)
    return any(item["card_id"] == card_id for item in player["zones"]["board"])


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
    *,
    entity_id: int,
    card_id: str,
    summary_zh: str,
    tags_before: Mapping[str, Any],
    tags_after: Mapping[str, Any],
    explanation_zh: str,
) -> Dict[str, Any]:
    return {
        "kind": "special_tags",
        "summary_zh": summary_zh,
        "details": {
            "entity_id": entity_id,
            "card_id": card_id,
            "tags_before": dict(tags_before),
            "tags_after": dict(tags_after),
            "explanation_zh": explanation_zh,
        },
    }


def build_review_scenario(
    card_id: str, card_registry: Mapping[str, CardDef]
) -> Dict[str, Any]:
    if card_id not in CARDS:
        raise ValueError("unknown advanced status batch card: {}".format(card_id))
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
    own.hand = [HandCard(97_000, card_id)]
    opposing.hand = []
    own.board = [Minion(97_001, "CS2_120", 2, 3, 3, summoned_turn=0)]
    opposing.board = [
        Minion(97_002, "CS2_182", 4, 5, 5, summoned_turn=0),
        Minion(97_003, "CS2_172", 3, 2, 2, summoned_turn=0),
    ]
    own.mana = own.max_mana = 10
    opposing.mana = opposing.max_mana = 10

    target: Optional[TargetRef] = None
    target_description = "无目标"
    if card_id == "CORE_CS2_024":
        target = TargetRef.hero(actor)
        target_description = "我方英雄"
    elif card_id in {"CORE_CS2_188", "CORE_EX1_059"}:
        target = TargetRef.minion(enemy, 97_002)
        target_description = "敌方冰风雪人"
    elif card_id == "CORE_UNG_205":
        target = TargetRef.hero(enemy)
        target_description = "敌方英雄"
    if card_id == "CORE_EX1_059":
        opposing.board[0].health = 3

    action = Action(ActionType.PLAY, 97_000, target)
    before = review_state_from_observation(game.observation(actor))
    game.apply(action)
    after = review_state_from_observation(game.observation(actor))
    own_before = _player(before, "我方")
    own_after = _player(after, "我方")
    enemy_before = _player(before, "敌方")
    enemy_after = _player(after, "敌方")
    assertions = [
        _assertion(
            "mana",
            "我方法力",
            own_before["resources"]["mana"],
            own_after["resources"]["mana"],
            "支付{}点法力".format(card.cost),
        )
    ]
    special_cases = []

    if card_id == "CORE_CS2_024":
        assertions.extend(
            [
                _assertion(
                    "friendly-hero-is-valid",
                    "我方英雄生命值",
                    own_before["hero"]["health"],
                    own_after["hero"]["health"],
                    "我方英雄也是合法角色目标并受到3点伤害",
                ),
                _assertion(
                    "friendly-hero-frozen",
                    "我方英雄标签",
                    own_before["hero"]["tags"],
                    own_after["hero"]["tags"],
                    "伤害结算后获得冻结标签",
                ),
            ]
        )
        special_cases.append(
            _special_tags(
                entity_id=actor,
                card_id="HERO_{}".format(actor),
                summary_zh="寒冰箭可以选择并冻结使用者自己的英雄。",
                tags_before={"frozen": False},
                tags_after={"frozen": True},
                explanation_zh="冻结阻止角色下一次原本可用的攻击，不按固定回合数简单倒计时。",
            )
        )
        title = "寒冰箭：可以伤害并冻结自己"
        purpose = "核对任意角色目标范围、伤害与冻结的结算顺序。"
    elif card_id == "CORE_CS2_028":
        before_yeti = _minion(before, "敌方", "CS2_182")
        after_yeti = _minion(after, "敌方", "CS2_182")
        assertions.extend(
            [
                _assertion(
                    "survivor-damaged",
                    "敌方冰风雪人生命值",
                    before_yeti["health"],
                    after_yeti["health"],
                    "受到2点伤害后存活",
                ),
                _assertion(
                    "survivor-frozen",
                    "敌方冰风雪人关键词",
                    before_yeti["mechanics_zh"],
                    after_yeti["mechanics_zh"],
                    "存活的敌方随从被冻结",
                ),
                _assertion(
                    "lethal-damage-removes-minion",
                    "敌方血沼迅猛龙是否在场",
                    _card_present(before, "敌方", "CS2_172"),
                    _card_present(after, "敌方", "CS2_172"),
                    "受到致命伤害后离场，不保留无意义的冻结实体",
                ),
            ]
        )
        special_cases.append(
            _special_tags(
                entity_id=97_002,
                card_id="CS2_182",
                summary_zh="群体伤害完成死亡清理后，存活的敌方随从获得冻结。",
                tags_before={"frozen": False},
                tags_after={"frozen": True},
                explanation_zh="死亡随从先从场上移除；冻结状态只需保留在存活实体上。",
            )
        )
        title = "暴风雪：先造成群体伤害，再冻结存活随从"
        purpose = "核对群体范围、致死清理和冻结状态写入。"
    elif card_id == "CORE_CS2_188":
        before_yeti = _minion(before, "敌方", "CS2_182")
        after_yeti = _minion(after, "敌方", "CS2_182")
        assertions.append(
            _assertion(
                "enemy-minion-temporary-buff",
                "敌方冰风雪人攻击力",
                before_yeti["attack"],
                after_yeti["attack"],
                "敌方随从也是合法目标，本回合获得+2攻击力",
            )
        )
        special_cases.append(
            _special_tags(
                entity_id=97_002,
                card_id="CS2_182",
                summary_zh="攻击力增益带有当前回合结束时失效的期限。",
                tags_before={},
                tags_after={
                    "temporary_attack": 2,
                    "temporary_attack_expires_turn": before["turn"],
                },
                explanation_zh="回合结束时仅移除临时攻击力；如果之后发生属性互换，则按互换规则固化结果。",
            )
        )
        title = "叫嚣的中士：可以临时强化敌方随从"
        purpose = "核对任意随从目标范围和本回合攻击力期限。"
    elif card_id == "CORE_UNG_205":
        assertions.append(
            _assertion(
                "enemy-hero-frozen",
                "敌方英雄标签",
                enemy_before["hero"]["tags"],
                enemy_after["hero"]["tags"],
                "敌方英雄属于敌人并获得冻结标签",
            )
        )
        special_cases.append(
            _special_tags(
                entity_id=enemy,
                card_id="HERO_{}".format(enemy),
                summary_zh="冰川裂片可以冻结敌方英雄，不限于敌方随从。",
                tags_before={"frozen": False},
                tags_after={"frozen": True},
                explanation_zh="英雄当前没有攻击力时仍保存冻结状态，待其获得攻击机会后消耗。",
            )
        )
        title = "冰川裂片：敌方英雄也是合法目标"
        purpose = "核对“一个敌人”包含敌方英雄，并正确写入冻结状态。"
    else:
        before_yeti = _minion(before, "敌方", "CS2_182")
        after_yeti = _minion(after, "敌方", "CS2_182")
        assertions.append(
            _assertion(
                "damaged-current-health-swap",
                "敌方冰风雪人攻击力/当前生命值/生命值上限",
                [
                    before_yeti["attack"],
                    before_yeti["health"],
                    before_yeti["max_health"],
                ],
                [
                    after_yeti["attack"],
                    after_yeti["health"],
                    after_yeti["max_health"],
                ],
                "使用受伤后的当前生命值作为新攻击力，并以原攻击力作为新生命值和上限",
            )
        )
        special_cases.append(
            _special_tags(
                entity_id=97_002,
                card_id="CS2_182",
                summary_zh="受伤随从使用当前生命值参与属性互换，互换后不再处于受伤状态。",
                tags_before={"damaged": True},
                tags_after={"damaged": False},
                explanation_zh="4攻、5点上限但只剩3点生命的随从，互换后成为3/4，而不是5/4。",
            )
        )
        title = "疯狂的炼金师：互换受伤随从的当前属性"
        purpose = "核对当前生命值而非生命值上限参与互换，并重置受伤状态。"

    description = "我方使用《{}》".format(card.name)
    if target is not None:
        description += "，选择{}".format(target_description)
    description += "。"
    return {
        "scenario_id": "{}-advanced-status-review-v1".format(
            card_id.lower().replace("_", "-")
        ),
        "title_zh": title,
        "purpose_zh": purpose,
        "before": before,
        "action": {
            "type": "play_card",
            "actor_player_id": actor,
            "source_entity_id": 97_000,
            "card_id": card_id,
            "target": asdict(target) if target else None,
            "description_zh": description,
            "engine_action": action.to_dict(),
        },
        "after": after,
        "assertions": assertions,
        "special_cases": special_cases,
    }


__all__ = [
    "AUTHORING_METADATA",
    "CARDS",
    "SCENARIO_CARD_NAMES_ZH",
    "build_review_scenario",
]
