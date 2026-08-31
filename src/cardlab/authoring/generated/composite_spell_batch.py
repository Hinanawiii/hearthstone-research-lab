from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Tuple

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
GENERATED_BY = "codex-gpt-5.6-core-composite-spell-batch-v1"


@dataclass(frozen=True)
class CompositeSpellContract:
    card_id: str
    name_zh: str
    source_text_zh: str
    cost: int
    target_mode: TargetMode
    effects: Tuple[Effect, ...]
    scenario: str
    expected_zh: str
    lifesteal: bool = False


_CONTRACTS = (
    CompositeSpellContract(
        "CORE_CS1_130",
        "神圣惩击",
        "对一个随从造成3点伤害。",
        1,
        TargetMode.ANY_MINION,
        (Effect("damage", 3),),
        "damage_minion",
        "所选随从受到3点伤害，英雄不能成为目标。",
    ),
    CompositeSpellContract(
        "CORE_BOT_222",
        "灵魂炸弹",
        "对一个随从和你的英雄各造成4点伤害。",
        1,
        TargetMode.ANY_MINION,
        (Effect("damage", 4), Effect("damage", 4, target="owner_hero")),
        "damage_both",
        "所选随从和我方英雄各受到4点伤害。",
    ),
    CompositeSpellContract(
        "CORE_CS2_004",
        "真言术：盾",
        "使一个随从获得+2生命值。 抽一张牌。",
        1,
        TargetMode.ANY_MINION,
        (Effect("buff", health=2), Effect("draw", 1, target="owner")),
        "buff_health_draw",
        "所选随从获得+2生命值和生命上限，然后我方抽一张牌。",
    ),
    CompositeSpellContract(
        "CORE_EX1_302",
        "死亡缠绕",
        "对一个随从造成1点伤害。如果该随从死亡，抽一张牌。",
        1,
        TargetMode.ANY_MINION,
        (Effect("damage", 1), Effect("draw_if_selected_dead", 1, target="owner")),
        "mortal_coil",
        "1点伤害消灭所选1血随从，因此我方抽一张牌。",
    ),
    CompositeSpellContract(
        "CORE_EX1_391",
        "猛击",
        "对一个随从造成2点伤害，如果 它依然存活，则抽一张牌。",
        1,
        TargetMode.ANY_MINION,
        (Effect("damage", 2), Effect("draw_if_selected_survives", 1, target="owner")),
        "slam",
        "所选随从受到2点伤害后仍存活，因此我方抽一张牌。",
    ),
    CompositeSpellContract(
        "CORE_BRM_013",
        "快速射击",
        "造成3点伤害。 如果你没有其他手牌，则抽一张牌。",
        2,
        TargetMode.ANY_CHARACTER,
        (Effect("damage", 3), Effect("draw_if_hand_empty", 1, target="owner")),
        "quick_shot",
        "法术离开手牌后手牌为空，造成3点伤害并抽一张牌。",
    ),
    CompositeSpellContract(
        "CORE_BT_292",
        "阿达尔之手",
        "使一个随从获得+2/+1。 抽一张牌。",
        2,
        TargetMode.ANY_MINION,
        (Effect("buff", attack=2, health=1), Effect("draw", 1, target="owner")),
        "buff_stats_draw",
        "所选随从获得+2/+1，然后我方抽一张牌。",
    ),
    CompositeSpellContract(
        "CORE_EX1_129",
        "刀扇",
        "对所有敌方随从造成1点伤害，抽一张牌。",
        2,
        TargetMode.NONE,
        (Effect("damage_all", 1, target="enemy_minions"), Effect("draw", 1, target="owner")),
        "fan_of_knives",
        "所有敌方随从受到1点伤害，其中1血随从死亡；随后我方抽一张牌。",
    ),
    CompositeSpellContract(
        "CORE_EX1_278",
        "毒刃",
        "造成1点伤害。抽一张牌。",
        2,
        TargetMode.ANY_CHARACTER,
        (Effect("damage", 1), Effect("draw", 1, target="owner")),
        "damage_draw",
        "所选敌方英雄受到1点伤害，然后我方抽一张牌。",
    ),
    CompositeSpellContract(
        "CORE_EX1_606",
        "盾牌格挡",
        "获得5点护甲值。抽一张牌。",
        2,
        TargetMode.NONE,
        (Effect("armor", 5, target="owner_hero"), Effect("draw", 1, target="owner")),
        "armor_draw",
        "我方英雄获得5点护甲，然后抽一张牌。",
    ),
    CompositeSpellContract(
        "CORE_TRL_307",
        "圣光闪现",
        "恢复4点生命值。抽一张牌。",
        2,
        TargetMode.ANY_CHARACTER,
        (Effect("heal", 4), Effect("draw", 1, target="owner")),
        "heal_draw",
        "我方英雄恢复4点生命值，然后抽一张牌。",
    ),
    CompositeSpellContract(
        "CORE_CS2_094",
        "愤怒之锤",
        "造成3点伤害。抽一张牌。",
        3,
        TargetMode.ANY_CHARACTER,
        (Effect("damage", 3), Effect("draw", 1, target="owner")),
        "damage_draw",
        "所选敌方英雄受到3点伤害，然后我方抽一张牌。",
    ),
    CompositeSpellContract(
        "CORE_CFM_604",
        "强效治疗药水",
        "为一个友方角色恢复12点生命值。抽一张牌。",
        4,
        TargetMode.FRIENDLY_CHARACTER,
        (Effect("heal", 12), Effect("draw", 1, target="owner")),
        "friendly_heal_draw",
        "我方英雄恢复12点生命值，然后抽一张牌；敌方角色不能成为目标。",
    ),
    CompositeSpellContract(
        "CORE_ICC_055",
        "吸取灵魂",
        "吸血 对一个随从造成 3点伤害。",
        2,
        TargetMode.ANY_MINION,
        (Effect("lifesteal_damage", 3),),
        "lifesteal_minion",
        "所选随从受到3点伤害，我方英雄因吸血恢复3点生命值。",
        lifesteal=True,
    ),
    CompositeSpellContract(
        "CORE_SW_442",
        "虚空碎片",
        "吸血 造成4点伤害。",
        4,
        TargetMode.ANY_CHARACTER,
        (Effect("lifesteal_damage", 4),),
        "lifesteal_any",
        "所选敌方英雄受到4点伤害，我方英雄因吸血恢复4点生命值。",
        lifesteal=True,
    ),
    CompositeSpellContract(
        "RLK_024",
        "灵界打击",
        "吸血 对一个随从造成6点伤害。",
        4,
        TargetMode.ANY_MINION,
        (Effect("lifesteal_damage", 6),),
        "lifesteal_minion",
        "所选随从受到6点伤害并死亡，我方英雄因吸血恢复6点生命值。",
        lifesteal=True,
    ),
    CompositeSpellContract(
        "CORE_CS2_076",
        "刺杀",
        "消灭一个敌方随从。",
        4,
        TargetMode.ENEMY_MINION,
        (Effect("destroy"),),
        "destroy_enemy",
        "所选敌方随从被消灭，友方随从不能成为目标。",
    ),
    CompositeSpellContract(
        "CORE_CS2_108",
        "斩杀",
        "消灭一个受伤的敌方随从。",
        1,
        TargetMode.DAMAGED_ENEMY_MINION,
        (Effect("destroy"),),
        "execute",
        "所选受伤敌方随从被消灭，未受伤敌方随从不是合法目标。",
    ),
    CompositeSpellContract(
        "CORE_EX1_309",
        "灵魂虹吸",
        "消灭一个随从，为你的英雄恢复3点生命值。",
        4,
        TargetMode.ANY_MINION,
        (Effect("destroy"), Effect("heal", 3, target="owner_hero")),
        "destroy_heal",
        "所选随从被消灭，我方英雄恢复3点生命值。",
    ),
    CompositeSpellContract(
        "CORE_EX1_197",
        "暗言术：毁",
        "消灭所有攻击力大于或等于5的随从。",
        4,
        TargetMode.NONE,
        (Effect("destroy_all_attack_at_least", 5, target="all_minions"),),
        "ruin",
        "双方攻击力不低于5的随从都被消灭，低攻击力随从保留。",
    ),
)

CONTRACTS = {contract.card_id: contract for contract in _CONTRACTS}

CARDS: Dict[str, CardDef] = {
    contract.card_id: CardDef(
        contract.card_id,
        contract.name_zh,
        CardType.SPELL,
        contract.cost,
        target_mode=contract.target_mode,
        effects=contract.effects,
        lifesteal=contract.lifesteal,
    )
    for contract in _CONTRACTS
}

AUTHORING_METADATA: Dict[str, Dict[str, Any]] = {
    contract.card_id: {
        "source_version": SOURCE_VERSION,
        "source_text": contract.source_text_zh,
        "source_text_zh": contract.source_text_zh,
        "name_zh": contract.name_zh,
        "generated_by": GENERATED_BY,
        "review_status": "awaiting_human_scenario_review",
    }
    for contract in _CONTRACTS
}

SCENARIO_CARD_NAMES_ZH = {
    **{card_id: contract.name_zh for card_id, contract in CONTRACTS.items()},
    "CS2_120": "淡水鳄",
    "CS2_172": "血沼迅猛龙",
    "CS2_182": "冰风雪人",
    "CS2_200": "石拳食人魔",
    "CS2_231": "小精灵",
}


def _player(state: Mapping[str, Any], role_zh: str) -> Mapping[str, Any]:
    return next(item for item in state["players"] if item["role_zh"] == role_zh)


def _focus(state: Mapping[str, Any]) -> Dict[str, Any]:
    own = _player(state, "我方")
    enemy = _player(state, "敌方")
    return {
        "我方英雄": {"生命": own["hero"]["health"], "护甲": own["hero"]["armor"]},
        "敌方英雄": {"生命": enemy["hero"]["health"], "护甲": enemy["hero"]["armor"]},
        "我方手牌数": own["zones"]["hand"]["count"],
        "我方牌库数": own["zones"]["deck"]["count"],
        "我方场上": [
            {"card_id": item["card_id"], "attack": item["attack"], "health": item["health"]}
            for item in own["zones"]["board"]
        ],
        "敌方场上": [
            {"card_id": item["card_id"], "attack": item["attack"], "health": item["health"]}
            for item in enemy["zones"]["board"]
        ],
    }


def _target_for_scenario(
    contract: CompositeSpellContract, actor: int, enemy: int
) -> Optional[TargetRef]:
    if contract.scenario in {"buff_health_draw", "buff_stats_draw"}:
        return TargetRef.minion(actor, 108_001)
    if contract.scenario in {"heal_draw", "friendly_heal_draw"}:
        return TargetRef.hero(actor)
    if contract.scenario == "mortal_coil":
        return TargetRef.minion(enemy, 108_003)
    if contract.scenario in {
        "damage_minion",
        "damage_both",
        "slam",
        "lifesteal_minion",
        "destroy_enemy",
        "execute",
        "destroy_heal",
    }:
        return TargetRef.minion(enemy, 108_002)
    if contract.scenario in {"quick_shot", "damage_draw", "lifesteal_any"}:
        return TargetRef.hero(enemy)
    return None


def build_review_scenario(card_id: str, card_registry: Mapping[str, CardDef]) -> Dict[str, Any]:
    if card_id not in CONTRACTS:
        raise ValueError("unknown composite spell batch card: {}".format(card_id))
    contract = CONTRACTS[card_id]
    game = Game(seed=sum(ord(char) for char in card_id), card_registry=card_registry)
    actor = game.state.active_player
    enemy = 1 - actor
    own = game.state.players[actor]
    opposing = game.state.players[enemy]
    own.hero_health = 15
    opposing.hero_health = 25
    own.deck = ["CS2_172"]
    opposing.deck = ["CS2_182"]
    own.hand = [HandCard(108_000, card_id)]
    opposing.hand = []
    own.board = [Minion(108_001, "CS2_120", 2, 1, 3, summoned_turn=0)]
    opposing.board = [
        Minion(108_002, "CS2_182", 4, 6, 6, summoned_turn=0),
        Minion(108_003, "CS2_231", 1, 1, 1, summoned_turn=0),
    ]
    own.mana = own.max_mana = 10
    opposing.mana = opposing.max_mana = 10
    if contract.scenario == "execute":
        opposing.board[0].health = 5
    elif contract.scenario == "ruin":
        own.board.append(Minion(108_004, "CS2_200", 6, 7, 7, summoned_turn=0))
        opposing.board[0].attack = 5

    target = _target_for_scenario(contract, actor, enemy)
    action = Action(ActionType.PLAY, 108_000, target)
    before = review_state_from_observation(game.observation(actor))
    game.apply(action)
    after = review_state_from_observation(game.observation(actor))
    own_before = _player(before, "我方")
    own_after = _player(after, "我方")
    assertions = [
        {
            "assertion_id": "mana",
            "subject_zh": "我方法力",
            "before": own_before["resources"]["mana"],
            "after": own_after["resources"]["mana"],
            "expected_zh": "支付{}点法力".format(contract.cost),
        },
        {
            "assertion_id": "primary-outcome",
            "subject_zh": "效果涉及的英雄、手牌、牌库与场上实体",
            "before": _focus(before),
            "after": _focus(after),
            "expected_zh": contract.expected_zh,
        },
    ]
    special_cases = []
    if contract.scenario in {"mortal_coil", "slam", "quick_shot", "execute"}:
        special_cases.append(
            {
                "kind": "special_tags",
                "summary_zh": "条件分支已在局面中显式满足。",
                "details": {
                    "entity_id": 108_000,
                    "card_id": card_id,
                    "tags_before": {"condition": contract.scenario},
                    "tags_after": {"condition_satisfied": True},
                    "explanation_zh": contract.expected_zh,
                },
            }
        )
    if contract.lifesteal:
        special_cases.append(
            {
                "kind": "special_tags",
                "summary_zh": "吸血治疗量与实际造成的伤害绑定。",
                "details": {
                    "entity_id": 108_000,
                    "card_id": card_id,
                    "tags_before": {"lifesteal": True},
                    "tags_after": {"lifesteal_resolved": True},
                    "explanation_zh": contract.expected_zh,
                },
            }
        )
    return {
        "scenario_id": "{}-composite-spell-review-v1".format(card_id.lower().replace("_", "-")),
        "title_zh": "{}：按卡面顺序结算组合效果".format(contract.name_zh),
        "purpose_zh": "核对目标限制、效果顺序与条件分支，避免只实现卡面的一部分。",
        "before": before,
        "action": {
            "type": "play_card",
            "actor_player_id": actor,
            "source_entity_id": 108_000,
            "card_id": card_id,
            "target": action.to_dict()["target"],
            "description_zh": "我方使用《{}》{}。".format(
                contract.name_zh,
                "并选择一个合法目标" if target is not None else "",
            ),
            "engine_action": action.to_dict(),
        },
        "after": after,
        "assertions": assertions,
        "special_cases": special_cases,
    }


__all__ = [
    "AUTHORING_METADATA",
    "CARDS",
    "CONTRACTS",
    "SCENARIO_CARD_NAMES_ZH",
    "build_review_scenario",
]
