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
    TargetMode,
    TargetRef,
    Weapon,
)
from ..review_format import review_state_from_observation

SOURCE_VERSION = "250339"
GENERATED_BY = "codex-gpt-5.6-core-special-action-batch-v1"

TOKEN_CARDS: Dict[str, CardDef] = {
    "EX1_131t": CardDef(
        "EX1_131t",
        "迪菲亚强盗",
        CardType.MINION,
        1,
        2,
        1,
        collectible=False,
    ),
    "SW_429t": CardDef(
        "SW_429t",
        "金壳龟",
        CardType.MINION,
        4,
        2,
        7,
        taunt=True,
        races=("BEAST",),
        collectible=False,
    ),
}

SUPPORT_CARDS: Dict[str, CardDef] = {
    "SPECIAL_TEST_MINION": CardDef(
        "SPECIAL_TEST_MINION",
        "测试随从",
        CardType.MINION,
        1,
        2,
        4,
        collectible=False,
    ),
    "SPECIAL_TEST_TAUNT": CardDef(
        "SPECIAL_TEST_TAUNT",
        "测试嘲讽随从",
        CardType.MINION,
        1,
        3,
        5,
        taunt=True,
        collectible=False,
    ),
    "SPECIAL_TEST_LARGE": CardDef(
        "SPECIAL_TEST_LARGE",
        "测试高攻随从",
        CardType.MINION,
        8,
        8,
        8,
        collectible=False,
    ),
    "SPECIAL_TEST_DRAW": CardDef(
        "SPECIAL_TEST_DRAW",
        "测试牌库牌",
        CardType.MINION,
        1,
        1,
        1,
        collectible=False,
    ),
    "SPECIAL_TEST_WEAPON": CardDef(
        "SPECIAL_TEST_WEAPON",
        "测试武器",
        CardType.WEAPON,
        2,
        3,
        durability=2,
        collectible=False,
    ),
}


@dataclass(frozen=True)
class SpecialContract:
    card_id: str
    name_zh: str
    source_text_zh: str
    definition: CardDef
    scenario: str
    expected_zh: str


_CONTRACTS = (
    SpecialContract(
        "CORE_SW_072",
        "锈烂蝰蛇",
        "可交易 战吼：摧毁对手的武器。",
        CardDef(
            "CORE_SW_072",
            "锈烂蝰蛇",
            CardType.MINION,
            3,
            3,
            4,
            races=("BEAST",),
            tradeable=True,
            effects=(Effect("destroy_enemy_weapon"),),
        ),
        "destroy_weapon",
        "使用锈烂蝰蛇后，对手装备的测试武器被摧毁。",
    ),
    SpecialContract(
        "CORE_SW_429",
        "紧壳商品",
        "可交易 召唤两只2/7并具有嘲讽的龟。",
        CardDef(
            "CORE_SW_429",
            "紧壳商品",
            CardType.SPELL,
            6,
            tradeable=True,
            effects=(Effect("summon", 2, card_id="SW_429t"),),
        ),
        "summon_turtles",
        "使用紧壳商品后，我方召唤两只2/7并具有嘲讽的金壳龟。",
    ),
    SpecialContract(
        "CORE_EX1_002",
        "黑骑士",
        "可交易 战吼：消灭一个具有嘲讽的敌方随从。",
        CardDef(
            "CORE_EX1_002",
            "黑骑士",
            CardType.MINION,
            4,
            4,
            4,
            races=("UNDEAD",),
            tradeable=True,
            target_mode=TargetMode.ENEMY_TAUNT_MINION,
            target_optional_if_unavailable=True,
            effects=(Effect("destroy"),),
        ),
        "destroy_taunt",
        "黑骑士的战吼消灭唯一的敌方嘲讽随从。",
    ),
    SpecialContract(
        "CORE_EX1_005",
        "王牌猎人",
        "可交易 战吼：消灭一个攻击力大于或等于7的随从。",
        CardDef(
            "CORE_EX1_005",
            "王牌猎人",
            CardType.MINION,
            4,
            4,
            2,
            tradeable=True,
            target_mode=TargetMode.HIGH_ATTACK_MINION,
            target_optional_if_unavailable=True,
            effects=(Effect("destroy"),),
        ),
        "destroy_high_attack",
        "王牌猎人的战吼消灭唯一的8攻随从。",
    ),
    SpecialContract(
        "CORE_BT_480",
        "火色魔印奔行者",
        "流放：抽一张牌。",
        CardDef(
            "CORE_BT_480",
            "火色魔印奔行者",
            CardType.MINION,
            1,
            1,
            1,
            outcast_effects=(Effect("draw", 1),),
        ),
        "outcast_draw_one",
        "火色魔印奔行者位于手牌最左侧，使用后触发流放并抽一张牌。",
    ),
    SpecialContract(
        "CORE_BT_491",
        "幽灵视觉",
        "抽一张牌。流放：再抽一张。",
        CardDef(
            "CORE_BT_491",
            "幽灵视觉",
            CardType.SPELL,
            2,
            effects=(Effect("draw", 1),),
            outcast_effects=(Effect("draw", 1),),
        ),
        "outcast_draw_two",
        "幽灵视觉位于手牌最左侧，基础效果和流放效果合计抽两张牌。",
    ),
    SpecialContract(
        "CORE_BT_801",
        "眼棱",
        "吸血。 对一个随从造成3点伤害。流放：法力值消耗为（1）点。",
        CardDef(
            "CORE_BT_801",
            "眼棱",
            CardType.SPELL,
            3,
            target_mode=TargetMode.ANY_MINION,
            effects=(Effect("lifesteal_damage", 3),),
            spell_school="FEL",
            outcast_cost=1,
        ),
        "outcast_cost",
        "眼棱位于手牌最左侧，只支付1点法力，对随从造成3点伤害并恢复3点生命。",
    ),
    SpecialContract(
        "CORE_EX1_131",
        "迪菲亚头目",
        "连击：召唤一个2/1的迪菲亚强盗。",
        CardDef(
            "CORE_EX1_131",
            "迪菲亚头目",
            CardType.MINION,
            2,
            3,
            2,
            combo_effects=(Effect("summon", 1, card_id="EX1_131t"),),
        ),
        "combo_summon",
        "本回合已使用过一张牌，迪菲亚头目触发连击并召唤2/1强盗。",
    ),
    SpecialContract(
        "CORE_EX1_134",
        "军情七处特工",
        "连击：造成3点伤害。",
        CardDef(
            "CORE_EX1_134",
            "军情七处特工",
            CardType.MINION,
            3,
            3,
            3,
            target_mode=TargetMode.ANY_CHARACTER,
            target_condition="combo_active",
            combo_effects=(Effect("damage", 3),),
        ),
        "combo_damage",
        "本回合已使用过一张牌，军情七处特工的连击对敌方英雄造成3点伤害。",
    ),
    SpecialContract(
        "CORE_BOT_576",
        "疯狂的药剂师",
        "连击：使一个友方随从获得+4攻击力。",
        CardDef(
            "CORE_BOT_576",
            "疯狂的药剂师",
            CardType.MINION,
            5,
            4,
            4,
            target_mode=TargetMode.FRIENDLY_MINION,
            target_condition="combo_active",
            target_optional_if_unavailable=True,
            combo_effects=(Effect("buff", attack=4),),
        ),
        "combo_buff",
        "本回合已使用过一张牌，疯狂的药剂师使所选友方随从获得+4攻击力。",
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
    **{card_id: card.name for card_id, card in TOKEN_CARDS.items()},
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
        "我方法力": own["resources"]["mana"],
        "我方手牌": own["zones"]["hand"],
        "我方牌库": own["zones"]["deck"],
        "我方场上": own["zones"]["board"],
        "敌方场上": enemy["zones"]["board"],
        "敌方武器": enemy["zones"]["weapon"],
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
        races=card.races,
        summoned_turn=0,
    )


def build_review_scenario(card_id: str, card_registry: Mapping[str, CardDef]) -> Dict[str, Any]:
    if card_id not in CONTRACTS:
        raise ValueError("unknown special action batch card: {}".format(card_id))
    contract = CONTRACTS[card_id]
    registry = dict(card_registry)
    registry.update(TOKEN_CARDS)
    registry.update(SUPPORT_CARDS)
    game = Game(seed=sum(ord(char) for char in card_id), card_registry=registry)
    owner = game.state.active_player
    enemy = 1 - owner
    own = game.state.players[owner]
    opposing = game.state.players[enemy]
    own.hero_health = opposing.hero_health = 30
    own.mana = own.max_mana = 10
    opposing.mana = opposing.max_mana = 10
    own.deck = ["SPECIAL_TEST_DRAW", "SPECIAL_TEST_DRAW"]
    opposing.deck = ["SPECIAL_TEST_DRAW"]
    own.hand = [
        HandCard(170_000, card_id),
        HandCard(170_001, "SPECIAL_TEST_MINION"),
    ]
    opposing.hand = []
    own.board = []
    opposing.board = []
    source_entity_id = 170_000
    action = Action(ActionType.PLAY, 170_000)

    if contract.scenario == "destroy_weapon":
        opposing.weapon = Weapon(170_010, "SPECIAL_TEST_WEAPON", 3, 2)
        opposing.hero_attack = 3
    elif contract.scenario == "destroy_taunt":
        opposing.board = [_minion("SPECIAL_TEST_TAUNT", 170_020, registry)]
        action = Action(ActionType.PLAY, 170_000, TargetRef.minion(enemy, 170_020))
    elif contract.scenario == "destroy_high_attack":
        opposing.board = [_minion("SPECIAL_TEST_LARGE", 170_021, registry)]
        action = Action(ActionType.PLAY, 170_000, TargetRef.minion(enemy, 170_021))
    elif contract.scenario.startswith("outcast"):
        own.hero_health = 25
        if contract.scenario == "outcast_cost":
            own.mana = 3
            opposing.board = [_minion("SPECIAL_TEST_MINION", 170_030, registry)]
            action = Action(ActionType.PLAY, 170_000, TargetRef.minion(enemy, 170_030))
    elif contract.scenario.startswith("combo"):
        own.cards_played_this_turn = 1
        if contract.scenario == "combo_damage":
            action = Action(ActionType.PLAY, 170_000, TargetRef.hero(enemy))
        elif contract.scenario == "combo_buff":
            own.board = [_minion("SPECIAL_TEST_MINION", 170_040, registry)]
            action = Action(ActionType.PLAY, 170_000, TargetRef.minion(owner, 170_040))

    before = review_state_from_observation(game.observation(owner))
    game.apply(action)
    after = review_state_from_observation(game.observation(owner))
    return {
        "scenario_id": "{}-special-action-review-v1".format(card_id.lower().replace("_", "-")),
        "title_zh": "{}：可交易、流放或连击核验".format(contract.name_zh),
        "purpose_zh": "核对特殊动作、手牌边缘位置、本回合出牌历史与条件目标。",
        "before": before,
        "action": {
            "type": action.action_type.value,
            "actor_player_id": owner,
            "source_entity_id": source_entity_id,
            "card_id": card_id,
            "target": action.to_dict()["target"],
            "description_zh": "执行《{}》的特殊机制测试。".format(contract.name_zh),
            "engine_action": action.to_dict(),
        },
        "after": after,
        "assertions": [
            {
                "assertion_id": "special-action-outcome",
                "subject_zh": "特殊动作或条件结算影响的资源与实体",
                "before": _focus(before),
                "after": _focus(after),
                "expected_zh": contract.expected_zh,
            }
        ],
        "special_cases": [
            {
                "kind": "special_tags",
                "summary_zh": "可交易、流放位置或连击历史单独记录。",
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
    "TOKEN_CARDS",
    "build_review_scenario",
]
