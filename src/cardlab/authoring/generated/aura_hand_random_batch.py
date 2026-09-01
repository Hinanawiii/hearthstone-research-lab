from __future__ import annotations

from dataclasses import dataclass
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
)
from ..review_format import review_state_from_observation

SOURCE_VERSION = "250339"
GENERATED_BY = "codex-gpt-5.6-core-aura-hand-random-batch-v1"

SUPPORT_CARDS: Dict[str, CardDef] = {
    "AURA_TEST_MINION": CardDef(
        "AURA_TEST_MINION", "测试随从", CardType.MINION, 1, 2, 4, collectible=False
    ),
    "AURA_TEST_TAUNT": CardDef(
        "AURA_TEST_TAUNT",
        "测试嘲讽随从",
        CardType.MINION,
        1,
        2,
        3,
        taunt=True,
        collectible=False,
    ),
    "AURA_TEST_MURLOC": CardDef(
        "AURA_TEST_MURLOC",
        "测试鱼人",
        CardType.MINION,
        1,
        2,
        3,
        races=("MURLOC",),
        collectible=False,
    ),
    "AURA_TEST_PIRATE": CardDef(
        "AURA_TEST_PIRATE",
        "测试海盗",
        CardType.MINION,
        1,
        2,
        3,
        races=("PIRATE",),
        collectible=False,
    ),
    "AURA_TEST_DRAW": CardDef(
        "AURA_TEST_DRAW", "测试牌库牌", CardType.MINION, 1, 1, 1, collectible=False
    ),
}


@dataclass(frozen=True)
class AuraContract:
    card_id: str
    name_zh: str
    source_text_zh: str
    definition: CardDef
    scenario: str
    expected_zh: str


_CONTRACTS = (
    AuraContract(
        "CORE_CFM_753",
        "污手街供货商",
        "战吼：使你手牌中的所有随从牌获得+1/+1。",
        CardDef(
            "CORE_CFM_753",
            "污手街供货商",
            CardType.MINION,
            2,
            2,
            2,
            effects=(Effect("buff_hand_minions", attack=1, health=1),),
        ),
        "buff_hand",
        "供货商离开手牌后，手牌中另一个随从获得+1/+1。",
    ),
    AuraContract(
        "CORE_WW_329",
        "机甲爆王",
        "嘲讽。战吼：使你手牌中的嘲讽随从牌获得+2/+2。",
        CardDef(
            "CORE_WW_329",
            "机甲爆王",
            CardType.MINION,
            4,
            3,
            4,
            taunt=True,
            races=("MECHANICAL",),
            effects=(Effect("buff_hand_minions", attack=2, health=2, keyword="TAUNT"),),
        ),
        "buff_taunt_hand",
        "手牌中的嘲讽随从获得+2/+2，非嘲讽随从保持原值。",
    ),
    AuraContract(
        "CS3_025",
        "伦萨克大王",
        "突袭 每当本随从攻击时，使你手牌中的所有随从牌获得+1/+1。",
        CardDef(
            "CS3_025",
            "伦萨克大王",
            CardType.MINION,
            5,
            3,
            6,
            rush=True,
            on_attack_effects=(Effect("buff_hand_minions", attack=1, health=1),),
        ),
        "attack_with_hand",
        "伦萨克宣告攻击时，手牌中的随从牌获得+1/+1。",
    ),
    AuraContract(
        "CORE_EX1_082",
        "疯狂投弹者",
        "战吼：造成3点伤害，随机分配到所有其他角色身上。",
        CardDef(
            "CORE_EX1_082",
            "疯狂投弹者",
            CardType.MINION,
            2,
            3,
            2,
            effects=(Effect("random_damage_other_characters", 1, repeats=3),),
        ),
        "random_other_characters",
        "三次1点伤害只会在投弹者以外的角色之间随机分配。",
    ),
    AuraContract(
        "CORE_BAR_311",
        "噬灵疫病",
        "吸血 造成4点伤害，随机分配到所有敌方随从 身上。",
        CardDef(
            "CORE_BAR_311",
            "噬灵疫病",
            CardType.SPELL,
            3,
            effects=(Effect("random_lifesteal_damage_minions", 1, repeats=4),),
            spell_school="SHADOW",
        ),
        "lifesteal_split",
        "四次1点伤害消灭两个2血敌方随从，我方英雄恢复4点生命值。",
    ),
    AuraContract(
        "CORE_LOOT_373",
        "治疗之雨",
        "恢复12点生命值，随机分配到所有友方角色上。",
        CardDef(
            "CORE_LOOT_373",
            "治疗之雨",
            CardType.SPELL,
            3,
            effects=(Effect("random_heal_friendly", 1, repeats=12),),
            spell_school="NATURE",
        ),
        "heal_split",
        "我方只有英雄受伤，12次治疗全部落到英雄身上，使其由18血回到30血。",
    ),
    AuraContract(
        "CORE_CATA_007",
        "吞噬",
        "随机对两个敌方随从造成3点伤害。每有一个随从死亡，抽一张牌。",
        CardDef(
            "CORE_CATA_007",
            "吞噬",
            CardType.SPELL,
            4,
            effects=(Effect("damage_two_random_enemy_minions_draw_deaths", 3),),
        ),
        "two_kills_draw",
        "两个3血敌方随从均被消灭，因此我方抽两张牌。",
    ),
    AuraContract(
        "CORE_CS2_122",
        "团队领袖",
        "你的其他随从拥有+1攻击力。",
        CardDef(
            "CORE_CS2_122",
            "团队领袖",
            CardType.MINION,
            3,
            2,
            3,
            aura_attack=1,
        ),
        "generic_aura",
        "团队领袖进场后，另一个友方随从获得+1攻击力，领袖自身不受影响。",
    ),
    AuraContract(
        "CORE_EX1_507",
        "鱼人领军",
        "你的其他鱼人拥有+2攻击力。",
        CardDef(
            "CORE_EX1_507",
            "鱼人领军",
            CardType.MINION,
            3,
            3,
            3,
            races=("MURLOC",),
            aura_attack=2,
            aura_race="MURLOC",
        ),
        "murloc_aura",
        "鱼人领军进场后，另一个友方鱼人获得+2攻击力。",
    ),
    AuraContract(
        "CORE_NEW1_027",
        "南海船长",
        "你的其他海盗拥有+1/+1。",
        CardDef(
            "CORE_NEW1_027",
            "南海船长",
            CardType.MINION,
            3,
            3,
            3,
            races=("PIRATE",),
            aura_attack=1,
            aura_health=1,
            aura_race="PIRATE",
        ),
        "pirate_aura",
        "南海船长进场后，另一个友方海盗获得+1/+1。",
    ),
    AuraContract(
        "CORE_CS2_222",
        "暴风城勇士",
        "你的其他随从拥有+1/+1。",
        CardDef(
            "CORE_CS2_222",
            "暴风城勇士",
            CardType.MINION,
            7,
            7,
            7,
            aura_attack=1,
            aura_health=1,
        ),
        "generic_aura",
        "暴风城勇士进场后，另一个友方随从获得+1/+1。",
    ),
    AuraContract(
        "CORE_EX1_162",
        "恐狼前锋",
        "相邻的随从拥有+1攻击力。",
        CardDef(
            "CORE_EX1_162",
            "恐狼前锋",
            CardType.MINION,
            2,
            2,
            2,
            races=("BEAST",),
            aura_attack=1,
            aura_adjacent_only=True,
        ),
        "adjacent_aura",
        "恐狼前锋在最右侧进场后，其左侧相邻随从获得+1攻击力。",
    ),
)

CONTRACTS = {contract.card_id: contract for contract in _CONTRACTS}
CARDS = {contract.card_id: contract.definition for contract in _CONTRACTS}

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
    **{card_id: card.name for card_id, card in SUPPORT_CARDS.items()},
}


def _player(state: Mapping[str, Any], role_zh: str) -> Mapping[str, Any]:
    return next(item for item in state["players"] if item["role_zh"] == role_zh)


def _focus(state: Mapping[str, Any]) -> Dict[str, Any]:
    own = _player(state, "我方")
    enemy = _player(state, "敌方")
    return {
        "我方英雄": own["hero"],
        "敌方英雄": enemy["hero"],
        "我方手牌": own["zones"]["hand"],
        "我方牌库": own["zones"]["deck"],
        "我方场上": own["zones"]["board"],
        "敌方场上": enemy["zones"]["board"],
    }


def _minion(card_id: str, entity_id: int, registry: Mapping[str, CardDef]) -> Minion:
    card = registry[card_id]
    return Minion(
        entity_id,
        card_id,
        card.attack,
        card.health,
        card.health,
        taunt=card.taunt,
        rush=card.rush,
        races=card.races,
        summoned_turn=0,
    )


def build_review_scenario(card_id: str, card_registry: Mapping[str, CardDef]) -> Dict[str, Any]:
    if card_id not in CONTRACTS:
        raise ValueError("unknown aura hand random batch card: {}".format(card_id))
    contract = CONTRACTS[card_id]
    registry = dict(card_registry)
    registry.update(SUPPORT_CARDS)
    game = Game(seed=sum(ord(char) for char in card_id), card_registry=registry)
    owner = game.state.active_player
    enemy = 1 - owner
    own = game.state.players[owner]
    opposing = game.state.players[enemy]
    own.hero_health = opposing.hero_health = 30
    own.mana = own.max_mana = 10
    opposing.mana = opposing.max_mana = 10
    own.deck = ["AURA_TEST_DRAW", "AURA_TEST_DRAW"]
    opposing.deck = ["AURA_TEST_DRAW"]
    own.hand = []
    opposing.hand = []
    own.board = []
    opposing.board = []
    source_entity_id = 150_000

    if contract.scenario == "attack_with_hand":
        own.board = [_minion(card_id, 150_001, registry)]
        opposing.board = [_minion("AURA_TEST_MINION", 150_002, registry)]
        own.hand = [HandCard(150_003, "AURA_TEST_MINION")]
        source_entity_id = 150_001
        action = Action(ActionType.ATTACK, 150_001, TargetRef.minion(enemy, 150_002))
    else:
        own.hand = [HandCard(150_000, card_id)]
        action = Action(ActionType.PLAY, 150_000)
        if contract.scenario == "buff_hand":
            own.hand.append(HandCard(150_010, "AURA_TEST_MINION"))
        elif contract.scenario == "buff_taunt_hand":
            own.hand.extend(
                [
                    HandCard(150_011, "AURA_TEST_TAUNT"),
                    HandCard(150_012, "AURA_TEST_MINION"),
                ]
            )
        elif contract.scenario == "random_other_characters":
            own.hero_health = opposing.hero_health = 30
        elif contract.scenario == "lifesteal_split":
            own.hero_health = 20
            opposing.board = [
                Minion(150_020, "AURA_TEST_MINION", 2, 2, 4, summoned_turn=0),
                Minion(150_021, "AURA_TEST_MINION", 2, 2, 4, summoned_turn=0),
            ]
        elif contract.scenario == "heal_split":
            own.hero_health = 18
        elif contract.scenario == "two_kills_draw":
            opposing.board = [
                Minion(150_030, "AURA_TEST_MINION", 2, 3, 4, summoned_turn=0),
                Minion(150_031, "AURA_TEST_MINION", 2, 3, 4, summoned_turn=0),
            ]
        elif contract.scenario in {
            "generic_aura",
            "murloc_aura",
            "pirate_aura",
            "adjacent_aura",
        }:
            support_id = {
                "generic_aura": "AURA_TEST_MINION",
                "murloc_aura": "AURA_TEST_MURLOC",
                "pirate_aura": "AURA_TEST_PIRATE",
                "adjacent_aura": "AURA_TEST_MINION",
            }[contract.scenario]
            own.board = [_minion(support_id, 150_040, registry)]

    before = review_state_from_observation(game.observation(owner))
    game.apply(action)
    after = review_state_from_observation(game.observation(owner))
    return {
        "scenario_id": "{}-aura-hand-random-review-v1".format(card_id.lower().replace("_", "-")),
        "title_zh": "{}：光环、手牌或随机分配核验".format(contract.name_zh),
        "purpose_zh": "核对持续光环、手牌附加属性和随机分配效果的总量与边界。",
        "before": before,
        "action": {
            "type": action.action_type.value,
            "actor_player_id": owner,
            "source_entity_id": source_entity_id,
            "card_id": card_id,
            "target": action.to_dict()["target"],
            "description_zh": "执行《{}》的确定性受限局面。".format(contract.name_zh),
            "engine_action": action.to_dict(),
        },
        "after": after,
        "assertions": [
            {
                "assertion_id": "aura-hand-random-outcome",
                "subject_zh": "受影响的英雄、手牌、牌库和场上实体",
                "before": _focus(before),
                "after": _focus(after),
                "expected_zh": contract.expected_zh,
            }
        ],
        "special_cases": [
            {
                "kind": "special_tags",
                "summary_zh": "光环范围、手牌附魔或随机总量单独记录。",
                "details": {
                    "entity_id": source_entity_id,
                    "card_id": card_id,
                    "tags_before": {"scenario": contract.scenario},
                    "tags_after": {"resolved": True},
                    "explanation_zh": contract.expected_zh,
                },
            }
        ],
    }


__all__ = [
    "AUTHORING_METADATA",
    "CARDS",
    "CONTRACTS",
    "SCENARIO_CARD_NAMES_ZH",
    "build_review_scenario",
]
