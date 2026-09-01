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
GENERATED_BY = "codex-gpt-5.6-core-hero-weapon-mechanics-batch-v1"

CARDS: Dict[str, CardDef] = {
    "CORE_RLK_086": CardDef(
        "CORE_RLK_086",
        "霜之哀伤",
        CardType.WEAPON,
        6,
        attack=4,
        durability=3,
        rarity="LEGENDARY",
        resummon_killed_minions_on_death=True,
    ),
    "CS3_020": CardDef(
        "CS3_020",
        "伊利达雷审判官",
        CardType.MINION,
        8,
        8,
        8,
        rush=True,
        races=("DEMON",),
        rarity="RARE",
        on_owner_hero_attack_effects=(Effect("source_attacks_selected"),),
    ),
    "CORE_NEW1_022": CardDef(
        "CORE_NEW1_022",
        "恐怖海盗",
        CardType.MINION,
        4,
        3,
        3,
        taunt=True,
        races=("PIRATE",),
        rarity="COMMON",
        cost_reduction_by_weapon_attack=True,
    ),
    "CORE_GVG_059": CardDef(
        "CORE_GVG_059",
        "齿轮光锤",
        CardType.WEAPON,
        3,
        attack=2,
        durability=3,
        rarity="EPIC",
        effects=(
            Effect(
                "random_grant_keywords_friendly",
                keywords=("divine_shield", "taunt"),
            ),
        ),
    ),
    "CORE_DAL_720": CardDef(
        "CORE_DAL_720",
        "摇摆矿锄",
        CardType.WEAPON,
        4,
        attack=4,
        durability=2,
        rarity="EPIC",
        deathrattle_effects=(
            Effect("return_random_friendly_minion_to_hand_discount", 2),
        ),
    ),
    "CORE_LOOT_044": CardDef(
        "CORE_LOOT_044",
        "铁刃护手",
        CardType.WEAPON,
        2,
        durability=2,
        rarity="EPIC",
        weapon_attack_equals_armor=True,
        weapon_cannot_attack_heroes=True,
    ),
    "CORE_BT_781": CardDef(
        "CORE_BT_781",
        "埃辛诺斯壁垒",
        CardType.WEAPON,
        3,
        attack=1,
        durability=4,
        rarity="LEGENDARY",
        prevents_hero_damage_by_losing_durability=True,
    ),
}

_SOURCE_TEXTS = {
    "CORE_RLK_086": "亡语：召唤被该武器消灭的所有 随从。",
    "CS3_020": "突袭 在你的英雄攻击一个敌人后，本随从也会攻击该敌人。",
    "CORE_NEW1_022": "嘲讽 你的武器每有1点攻击力，本牌的法力值消耗便减少（1）点。",
    "CORE_GVG_059": "战吼：随机使一个友方随从获得圣盾和嘲讽。",
    "CORE_DAL_720": "亡语：随机将一个友方随从移回你的手牌。它的法力值消耗减少（2）点。",
    "CORE_LOOT_044": "攻击力等同于你的 护甲值。无法攻击英雄。",
    "CORE_BT_781": "每当你的英雄即将受到伤害，改为埃辛诺斯壁垒失去1点耐久度。",
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
    "CS2_120": "淡水鳄",
    "CS2_182": "冰风雪人",
    "fixture_weapon": "测试武器",
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
            "summary_zh": "记录这张牌无法只靠基础属性表达的结算状态。",
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
        raise ValueError("unknown hero weapon mechanics card: {}".format(card_id))
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
    source_entity_id = 130_000

    if card_id == "CORE_RLK_086":
        own.weapon = Weapon(
            source_entity_id,
            card_id,
            4,
            1,
            killed_minion_card_ids=("CS2_120",),
        )
        own.hero_attack = 4
        opposing.board = [Minion(130_001, "CS2_182", 4, 4, 5, summoned_turn=0)]
        action = Action(
            ActionType.HERO_ATTACK,
            source_entity_id,
            TargetRef.minion(enemy, 130_001),
        )
        description = "霜之哀伤已消灭过淡水鳄；以最后1点耐久消灭冰风雪人。"
    elif card_id == "CS3_020":
        own.board = [
            Minion(
                source_entity_id,
                card_id,
                8,
                8,
                8,
                rush=True,
                races=("DEMON",),
                summoned_turn=0,
            )
        ]
        own.weapon = Weapon(130_002, "fixture_weapon", 1, 2)
        own.hero_attack = 1
        action = Action(ActionType.HERO_ATTACK, 130_002, TargetRef.hero(enemy))
        description = "我方英雄攻击敌方英雄，观察审判官是否追击同一目标。"
    elif card_id == "CORE_NEW1_022":
        own.weapon = Weapon(130_003, "fixture_weapon", 3, 2)
        own.hero_attack = 3
        own.hand = [HandCard(source_entity_id, card_id)]
        action = Action(ActionType.PLAY, source_entity_id)
        description = "我方装备3攻武器后使用恐怖海盗。"
    elif card_id == "CORE_GVG_059":
        own.hand = [HandCard(source_entity_id, card_id)]
        own.board = [Minion(130_004, "CS2_120", 2, 3, 3, summoned_turn=0)]
        action = Action(ActionType.PLAY, source_entity_id)
        description = "场上只有一个友方随从时装备齿轮光锤。"
    elif card_id == "CORE_DAL_720":
        own.weapon = Weapon(source_entity_id, card_id, 4, 1)
        own.hero_attack = 4
        own.board = [Minion(130_005, "CS2_182", 4, 5, 5, summoned_turn=0)]
        action = Action(ActionType.HERO_ATTACK, source_entity_id, TargetRef.hero(enemy))
        description = "摇摆矿锄以最后1点耐久攻击，触发亡语回手。"
    elif card_id == "CORE_LOOT_044":
        own.hero_armor = 5
        own.weapon = Weapon(
            source_entity_id,
            card_id,
            5,
            2,
            cannot_attack_heroes=True,
        )
        own.hero_attack = 5
        opposing.board = [Minion(130_006, "CS2_120", 2, 3, 3, summoned_turn=0)]
        action = Action(
            ActionType.HERO_ATTACK,
            source_entity_id,
            TargetRef.minion(enemy, 130_006),
        )
        description = "5点护甲时，铁刃护手只能攻击敌方淡水鳄。"
    else:
        own.weapon = Weapon(source_entity_id, card_id, 1, 1)
        own.hero_attack = 1
        own.hand = [HandCard(130_007, "CS2_029")]
        action = Action(ActionType.PLAY, 130_007, TargetRef.hero(actor))
        description = "对我方英雄使用火球术，壁垒仅剩1点耐久。"

    before = review_state_from_observation(game.observation(actor))
    legal_before = game.legal_actions()
    game.apply(action)
    after = review_state_from_observation(game.observation(actor))
    own_before = _player(before, "我方")
    own_after = _player(after, "我方")
    enemy_before = _player(before, "敌方")
    enemy_after = _player(after, "敌方")

    if card_id == "CORE_RLK_086":
        board_after = [item["card_id"] for item in own_after["zones"]["board"]]
        assertions = [
            _assertion(
                "frostmourne-resummon",
                "我方场上随从",
                [],
                board_after,
                "武器摧毁后召唤此前由它消灭的淡水鳄和本次消灭的冰风雪人",
            )
        ]
        special_cases = _special_tags(
            card_id,
            source_entity_id,
            {"killed_minion_card_ids": ["CS2_120"]},
            {"summoned_card_ids": board_after},
            "消灭记录绑定武器实例，并在替换或耐久归零时一次性结算。",
        )
    elif card_id == "CS3_020":
        assertions = [
            _assertion(
                "inquisitor-follow-up",
                "敌方英雄生命值",
                enemy_before["hero"]["health"],
                enemy_after["hero"]["health"],
                "先承受英雄1点伤害，再承受审判官8点追击伤害",
            )
        ]
        special_cases = _special_tags(
            card_id,
            source_entity_id,
            {"hero_attack_target": None},
            {"hero_attack_target": "敌方英雄", "triggered_attack": True},
            "触发攻击复用英雄刚刚攻击的目标；目标已离场时不再攻击。",
        )
    elif card_id == "CORE_NEW1_022":
        assertions = [
            _assertion(
                "dread-corsair-cost",
                "我方法力",
                own_before["resources"]["mana"],
                own_after["resources"]["mana"],
                "3攻武器将4费降低为1费",
            )
        ]
        special_cases = [
            {
                "kind": "cost_modification",
                "summary_zh": "费用随当前武器攻击力动态变化。",
                "details": {
                    "entity_id": source_entity_id,
                    "card_id": card_id,
                    "printed_cost": 4,
                    "effective_cost_before": 1,
                    "effective_cost_after": 1,
                    "reason_zh": "当前武器有3点攻击力",
                    "duration_zh": "仅在手牌中且武器仍装备时生效",
                },
            }
        ]
    elif card_id == "CORE_GVG_059":
        target_after = own_after["zones"]["board"][0]
        assertions = [
            _assertion(
                "coghammer-keywords",
                "淡水鳄关键词",
                own_before["zones"]["board"][0]["mechanics_zh"],
                target_after["mechanics_zh"],
                "同一个随机友方随从同时获得圣盾和嘲讽",
            )
        ]
        special_cases = _special_tags(
            card_id,
            target_after["entity_id"],
            {},
            {"divine_shield": True, "taunt": True},
            "两个关键词共用一次随机选择，不各自重新选择目标。",
        )
    elif card_id == "CORE_DAL_720":
        returned = own_after["zones"]["hand"]["cards"][0]
        assertions = [
            _assertion(
                "pickaxe-return",
                "我方手牌",
                [],
                [returned],
                "矿锄摧毁后将唯一友方随从移回手牌并赋予-2费用修正",
            )
        ]
        special_cases = [
            {
                "kind": "cost_modification",
                "summary_zh": "回手随从获得持续的2点减费。",
                "details": {
                    "entity_id": returned["entity_id"],
                    "card_id": returned["card_id"],
                    "printed_cost": 4,
                    "effective_cost_before": 4,
                    "effective_cost_after": 2,
                    "reason_zh": "摇摆矿锄亡语",
                    "duration_zh": "该手牌实例离开手牌前",
                },
            }
        ]
    elif card_id == "CORE_LOOT_044":
        hero_targets = [
            item
            for item in legal_before
            if item.action_type == ActionType.HERO_ATTACK
            and item.target is not None
            and item.target.kind == "hero"
        ]
        assertions = [
            _assertion(
                "gauntlet-no-hero-target",
                "可攻击的敌方英雄目标数",
                len(hero_targets),
                len(hero_targets),
                "铁刃护手不会生成攻击英雄的合法动作",
            ),
            _assertion(
                "gauntlet-dynamic-attack",
                "铁刃护手攻击力",
                own_before["zones"]["weapon"]["attack"],
                own_after["zones"]["weapon"]["attack"],
                "反击消耗2点护甲后，攻击力同步从5降为3",
            ),
        ]
        special_cases = _special_tags(
            card_id,
            source_entity_id,
            {"armor": 5, "attack": 5, "cannot_attack_heroes": True},
            {"armor": 3, "attack": 3, "cannot_attack_heroes": True},
            "武器攻击力实时读取护甲，目标过滤独立于嘲讽规则。",
        )
    else:
        assertions = [
            _assertion(
                "bulwark-prevent-damage",
                "我方英雄生命值",
                own_before["hero"]["health"],
                own_after["hero"]["health"],
                "火球术的整次6点伤害被替代，英雄不受伤",
            ),
            _assertion(
                "bulwark-loses-durability",
                "我方武器",
                own_before["zones"]["weapon"],
                own_after["zones"]["weapon"],
                "壁垒失去最后1点耐久并被摧毁",
            ),
        ]
        special_cases = _special_tags(
            card_id,
            source_entity_id,
            {"durability": 1, "incoming_damage": 6},
            {"durability": 0, "damage_taken": 0},
            "每个伤害事件分别替代；最后1点耐久仍能防止当前整次伤害。",
        )

    return {
        "scenario_id": "{}-hero-weapon-review-v1".format(
            card_id.lower().replace("_", "-")
        ),
        "title_zh": "{}：英雄与武器结算核验".format(card.name),
        "purpose_zh": "核对动态费用、武器实例状态、预伤害替代和攻击后触发。",
        "before": before,
        "action": {
            "type": "play_or_attack_fixture",
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
