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
    Weapon,
)
from ..review_format import review_state_from_observation

SOURCE_VERSION = "250339"
GENERATED_BY = "codex-gpt-5.6-core-weapon-foundation-batch-v1"

CARDS: Dict[str, CardDef] = {
    "RLK_067": CardDef(
        "RLK_067",
        "堕落的灰烬使者",
        CardType.WEAPON,
        6,
        attack=5,
        durability=2,
        lifesteal=True,
    ),
    "CORE_BT_921": CardDef(
        "CORE_BT_921",
        "奥达奇战刃",
        CardType.WEAPON,
        3,
        attack=2,
        durability=2,
        lifesteal=True,
    ),
    "CORE_CS2_074": CardDef(
        "CORE_CS2_074",
        "致命药膏",
        CardType.SPELL,
        1,
        effects=(Effect("weapon_buff", target="owner_weapon", attack=2),),
        requires_weapon=True,
    ),
}

_SOURCE_TEXTS = {
    "RLK_067": "吸血",
    "CORE_BT_921": "吸血",
    "CORE_CS2_074": "使你的武器获得+2攻击力。",
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
        raise ValueError("unknown weapon batch card: {}".format(card_id))
    card = CARDS[card_id]
    game = Game(seed=sum(ord(char) for char in card_id), card_registry=card_registry)
    actor = game.state.active_player
    enemy = 1 - actor
    own = game.state.players[actor]
    opposing = game.state.players[enemy]
    own.hero_health = 20
    opposing.hero_health = 25
    own.deck = ["CS2_120"]
    opposing.deck = ["CS2_172"]
    own.hand = [HandCard(99_000, card_id)]
    opposing.hand = []
    own.board = []
    opposing.board = [Minion(99_001, "CS2_182", 4, 8, 8, summoned_turn=0)]
    own.mana = own.max_mana = 10
    opposing.mana = opposing.max_mana = 10

    before = review_state_from_observation(game.observation(actor))
    play_action = Action(ActionType.PLAY, 99_000)
    engine_actions = [play_action.to_dict()]
    if card.card_type == CardType.WEAPON:
        game.apply(play_action)
        assert own.weapon is not None
        attack_action = Action(
            ActionType.HERO_ATTACK,
            own.weapon.entity_id,
            TargetRef.minion(enemy, 99_001),
        )
        game.apply(attack_action)
        engine_actions.append(attack_action.to_dict())
    else:
        own.weapon = Weapon(99_100, "CORE_BT_921", 2, 2, lifesteal=True)
        own.hero_attack = 2
        before = review_state_from_observation(game.observation(actor))
        game.apply(play_action)
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

    if card.card_type == CardType.WEAPON:
        before_weapon = own_before["zones"]["weapon"]
        after_weapon = own_after["zones"]["weapon"]
        enemy_minion_before = enemy_before["zones"]["board"][0]
        enemy_minion_after = enemy_after["zones"]["board"][0]
        assertions.extend(
            [
                _assertion(
                    "weapon-equipped",
                    "我方武器",
                    before_weapon,
                    after_weapon,
                    "装备{}攻/2耐久并具有吸血的武器".format(card.attack),
                ),
                _assertion(
                    "weapon-damage",
                    "敌方冰风雪人生命值",
                    enemy_minion_before["health"],
                    enemy_minion_after["health"],
                    "英雄攻击造成{}点武器伤害".format(card.attack),
                ),
                _assertion(
                    "lifesteal-after-retaliation",
                    "我方英雄生命值",
                    own_before["hero"]["health"],
                    own_after["hero"]["health"],
                    "先承受随从反击，再按实际武器伤害吸血",
                ),
                _assertion(
                    "durability-consumed",
                    "武器耐久度",
                    card.durability,
                    after_weapon["durability"],
                    "英雄完成一次攻击后消耗1点耐久度",
                ),
            ]
        )
        title = "{}：装备后由英雄攻击并触发吸血".format(card.name)
        purpose = "核对武器区、英雄攻击、反击伤害、吸血和耐久消耗。"
        action_type = "play_card_then_hero_attack"
        description = "我方装备《{}》，随后攻击敌方冰风雪人。".format(card.name)
        special_case_card_id = card_id
        special_case_entity_id = after_weapon["entity_id"]
        tags_before: Mapping[str, Any] = {}
        tags_after: Mapping[str, Any] = {
            "lifesteal": True,
            "durability_after_attack": after_weapon["durability"],
        }
        explanation = "武器只在持有者主动完成英雄攻击后消耗耐久；吸血恢复本次造成的伤害。"
    else:
        before_weapon = own_before["zones"]["weapon"]
        after_weapon = own_after["zones"]["weapon"]
        assertions.extend(
            [
                _assertion(
                    "weapon-attack-buffed",
                    "奥达奇战刃攻击力",
                    before_weapon["attack"],
                    after_weapon["attack"],
                    "已装备武器永久获得+2攻击力",
                ),
                _assertion(
                    "durability-unchanged",
                    "奥达奇战刃耐久度",
                    before_weapon["durability"],
                    after_weapon["durability"],
                    "增益不改变武器耐久度",
                ),
            ]
        )
        title = "致命药膏：强化已装备的武器"
        purpose = "核对无武器时不可使用，并只修改当前武器攻击力。"
        action_type = "play_card"
        description = "我方已装备奥达奇战刃，随后使用《致命药膏》。"
        special_case_card_id = "CORE_BT_921"
        special_case_entity_id = 99_100
        tags_before = {"attack": before_weapon["attack"]}
        tags_after = {"attack": after_weapon["attack"]}
        explanation = "增益绑定当前武器；武器被替换或摧毁后不会保留给下一把武器。"

    return {
        "scenario_id": "{}-weapon-review-v1".format(
            card_id.lower().replace("_", "-")
        ),
        "title_zh": title,
        "purpose_zh": purpose,
        "before": before,
        "action": {
            "type": action_type,
            "actor_player_id": actor,
            "source_entity_id": 99_000,
            "card_id": card_id,
            "target": asdict(TargetRef.minion(enemy, 99_001))
            if card.card_type == CardType.WEAPON
            else None,
            "description_zh": description,
            "engine_action": engine_actions,
        },
        "after": after,
        "assertions": assertions,
        "special_cases": [
            {
                "kind": "special_tags",
                "summary_zh": "武器区状态和武器专属标签单独记录。",
                "details": {
                    "entity_id": special_case_entity_id,
                    "card_id": special_case_card_id,
                    "tags_before": dict(tags_before),
                    "tags_after": dict(tags_after),
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
