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
    Weapon,
)
from ..review_format import review_state_from_observation

SOURCE_VERSION = "250339"
GENERATED_BY = "codex-gpt-5.6-core-conditional-weapon-batch-v1"

CARDS: Dict[str, CardDef] = {
    "CORE_TRL_111": CardDef(
        "CORE_TRL_111",
        "猎头者之斧",
        CardType.WEAPON,
        2,
        attack=2,
        durability=2,
        effects=(
            Effect(
                "weapon_buff_if_friendly_race",
                amount=1,
                target="owner_weapon",
                race="BEAST",
            ),
        ),
    ),
    "CORE_NEW1_018": CardDef(
        "CORE_NEW1_018",
        "血帆袭击者",
        CardType.MINION,
        2,
        2,
        3,
        races=("PIRATE",),
        effects=(Effect("buff_attack_by_weapon", target="played_minion"),),
    ),
    "CS3_022": CardDef(
        "CS3_022",
        "雾帆劫掠者",
        CardType.MINION,
        2,
        2,
        2,
        races=("PIRATE",),
        target_mode=TargetMode.ANY_CHARACTER,
        target_condition="weapon_equipped",
        effects=(Effect("damage_if_weapon", 2),),
    ),
    "CORE_TRL_240": CardDef(
        "CORE_TRL_240",
        "野蛮先锋",
        CardType.MINION,
        2,
        2,
        3,
        target_mode=TargetMode.ENEMY_MINION,
        target_optional_if_unavailable=True,
        effects=(Effect("damage_by_hero_attack"),),
    ),
}

_SOURCE_TEXTS = {
    "CORE_TRL_111": "战吼：如果你控制一个野兽，便获得+1耐久度。",
    "CORE_NEW1_018": "战吼： 获得等同于你的武器攻击力的攻击力。",
    "CS3_022": "战吼：如果你装备着武器，造成2点伤害。",
    "CORE_TRL_240": "战吼：对一个敌方随从造成等同于你的英雄攻击力的伤害。",
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
    "CORE_BT_921": "奥达奇战刃",
    "CS2_120": "淡水鳄",
    "CS2_172": "血沼迅猛龙",
    "CS2_182": "冰风雪人",
}


def _player(state: Mapping[str, Any], role_zh: str) -> Mapping[str, Any]:
    return next(item for item in state["players"] if item["role_zh"] == role_zh)


def _minion(
    state: Mapping[str, Any], role_zh: str, card_id: str
) -> Mapping[str, Any]:
    return next(
        item
        for item in _player(state, role_zh)["zones"]["board"]
        if item["card_id"] == card_id
    )


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
        raise ValueError("unknown conditional weapon batch card: {}".format(card_id))
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
    own.hand = [HandCard(101_000, card_id)]
    opposing.hand = []
    own.board = []
    opposing.board = [Minion(101_002, "CS2_182", 4, 7, 7, summoned_turn=0)]
    own.mana = own.max_mana = 10
    opposing.mana = opposing.max_mana = 10

    target: Optional[TargetRef] = None
    target_description = "无目标"
    if card_id == "CORE_TRL_111":
        own.board = [
            Minion(
                101_001,
                "CS2_120",
                2,
                3,
                3,
                races=("BEAST",),
                summoned_turn=0,
            )
        ]
    elif card_id in {"CORE_NEW1_018", "CS3_022"}:
        own.weapon = Weapon(101_100, "CORE_BT_921", 4, 2, lifesteal=True)
        own.hero_attack = 4
    if card_id == "CS3_022":
        target = TargetRef.hero(actor)
        target_description = "我方英雄"
    elif card_id == "CORE_TRL_240":
        own.weapon = Weapon(101_100, "CORE_BT_921", 2, 2, lifesteal=True)
        own.hero_attack = 4
        target = TargetRef.minion(enemy, 101_002)
        target_description = "敌方冰风雪人"

    action = Action(ActionType.PLAY, 101_000, target)
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
            "支付2点法力",
        )
    ]

    if card_id == "CORE_TRL_111":
        weapon_after = own_after["zones"]["weapon"]
        assertions.append(
            _assertion(
                "beast-durability",
                "猎头者之斧耐久度",
                None,
                weapon_after["durability"],
                "场上有野兽，基础2耐久额外获得1耐久",
            )
        )
        title = "猎头者之斧：由友方野兽触发额外耐久"
        purpose = "核对武器先装备，再由战吼读取友方场上的野兽种族。"
        special_entity_id = weapon_after["entity_id"]
        special_card_id = card_id
        tags_before: Mapping[str, Any] = {"friendly_beast_count": 1}
        tags_after: Mapping[str, Any] = {"weapon_durability": 3}
        explanation = "没有友方野兽时仍会装备2/2的基础武器，但不会获得额外耐久。"
    elif card_id == "CORE_NEW1_018":
        played_after = _minion(after, "我方", card_id)
        assertions.append(
            _assertion(
                "weapon-attack-gain",
                "血帆袭击者攻击力",
                card.attack,
                played_after["attack"],
                "读取当前武器的4点攻击力，成为6攻随从",
            )
        )
        title = "血帆袭击者：读取当前武器攻击力"
        purpose = "核对战吼读取结算时武器的实际攻击力，而不是武器印制值。"
        special_entity_id = played_after["entity_id"]
        special_card_id = card_id
        tags_before = {"weapon_attack": 4, "printed_minion_attack": 2}
        tags_after = {"minion_attack": played_after["attack"]}
        explanation = "没有装备武器时，获得的攻击力为0，随从保持2攻。"
    elif card_id == "CS3_022":
        assertions.append(
            _assertion(
                "conditional-friendly-target",
                "我方英雄生命值",
                own_before["hero"]["health"],
                own_after["hero"]["health"],
                "装备武器后战吼生效，并可选择我方角色承受2点伤害",
            )
        )
        title = "雾帆劫掠者：有武器时才选择伤害目标"
        purpose = "核对条件型目标选择，并显式覆盖友方角色也是合法目标。"
        played_after = _minion(after, "我方", card_id)
        special_entity_id = played_after["entity_id"]
        special_card_id = card_id
        tags_before = {"weapon_equipped": True, "target_required": True}
        tags_after = {"target_zh": target_description, "damage": 2}
        explanation = "没有武器时直接打出随从，不选择目标，也不造成伤害。"
    else:
        enemy_minion_before = _minion(before, "敌方", "CS2_182")
        enemy_minion_after = _minion(after, "敌方", "CS2_182")
        assertions.append(
            _assertion(
                "hero-attack-damage",
                "敌方冰风雪人生命值",
                enemy_minion_before["health"],
                enemy_minion_after["health"],
                "读取英雄当前4点攻击力并造成4点伤害",
            )
        )
        title = "野蛮先锋：按英雄当前攻击力伤害敌方随从"
        purpose = "核对目标只限敌方随从，并读取英雄总攻击力而非武器攻击力。"
        played_after = _minion(after, "我方", card_id)
        special_entity_id = played_after["entity_id"]
        special_card_id = card_id
        tags_before = {"weapon_attack": 2, "hero_attack": 4}
        tags_after = {"damage": 4, "target_zh": target_description}
        explanation = "英雄攻击力为0时造成0点伤害；没有敌方随从时可以打出本牌，战吼落空。"

    return {
        "scenario_id": "{}-conditional-weapon-review-v1".format(
            card_id.lower().replace("_", "-")
        ),
        "title_zh": title,
        "purpose_zh": purpose,
        "before": before,
        "action": {
            "type": "play_card",
            "actor_player_id": actor,
            "source_entity_id": 101_000,
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
                "summary_zh": "条件读取和目标要求单独记录。",
                "details": {
                    "entity_id": special_entity_id,
                    "card_id": special_card_id,
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
