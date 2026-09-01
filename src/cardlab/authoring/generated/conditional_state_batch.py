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
GENERATED_BY = "codex-gpt-5.6-core-conditional-state-batch-v1"

TOKEN_CARDS: Dict[str, CardDef] = {
    "BAR_878t": CardDef(
        "BAR_878t",
        "战地医师",
        CardType.MINION,
        2,
        2,
        2,
        lifesteal=True,
        collectible=False,
    ),
    "CS2_033": CardDef(
        "CS2_033",
        "水元素",
        CardType.MINION,
        4,
        3,
        6,
        races=("ELEMENTAL",),
        freezes_damaged_characters=True,
        collectible=False,
    ),
    "CS2_101t": CardDef(
        "CS2_101t",
        "白银之手新兵",
        CardType.MINION,
        1,
        1,
        1,
        collectible=False,
    ),
    "CS2_091": CardDef(
        "CS2_091",
        "圣光的正义",
        CardType.WEAPON,
        1,
        1,
        durability=4,
        collectible=False,
    ),
}

SUPPORT_CARDS: Dict[str, CardDef] = {
    "STATE_TEST_MINION": CardDef(
        "STATE_TEST_MINION", "测试随从", CardType.MINION, 1, 2, 4, collectible=False
    ),
    "STATE_TEST_MURLOC": CardDef(
        "STATE_TEST_MURLOC",
        "测试鱼人",
        CardType.MINION,
        1,
        2,
        2,
        races=("MURLOC",),
        collectible=False,
    ),
    "STATE_TEST_BEAST": CardDef(
        "STATE_TEST_BEAST",
        "测试野兽",
        CardType.MINION,
        1,
        2,
        2,
        races=("BEAST",),
        collectible=False,
    ),
    "STATE_TEST_DRAGON": CardDef(
        "STATE_TEST_DRAGON",
        "测试龙",
        CardType.MINION,
        1,
        2,
        2,
        races=("DRAGON",),
        collectible=False,
    ),
    "STATE_TEST_DRAW": CardDef(
        "STATE_TEST_DRAW", "测试牌库牌", CardType.MINION, 1, 1, 1, collectible=False
    ),
    "STATE_TEST_HOLY": CardDef(
        "STATE_TEST_HOLY",
        "测试神圣法术",
        CardType.SPELL,
        0,
        spell_school="HOLY",
        collectible=False,
    ),
    "STATE_TEST_SHADOW": CardDef(
        "STATE_TEST_SHADOW",
        "测试暗影法术",
        CardType.SPELL,
        1,
        spell_school="SHADOW",
        collectible=False,
    ),
    "STATE_TEST_WEAPON": CardDef(
        "STATE_TEST_WEAPON",
        "测试武器",
        CardType.WEAPON,
        1,
        2,
        durability=2,
        collectible=False,
    ),
}


@dataclass(frozen=True)
class ConditionalContract:
    card_id: str
    name_zh: str
    source_text_zh: str
    definition: CardDef
    scenario: str
    expected_zh: str


_CONTRACTS = (
    ConditionalContract(
        "CORE_BAR_878",
        "战地医师老兵",
        "在你施放一个神圣法术后，召唤一个2/2并具有吸血的医师。",
        CardDef(
            "CORE_BAR_878",
            "战地医师老兵",
            CardType.MINION,
            4,
            3,
            5,
            on_owner_spell_cast_effects=(Effect("summon", 1, card_id="BAR_878t"),),
            on_owner_spell_cast_school="HOLY",
        ),
        "cast_holy_spell",
        "施放神圣法术后，召唤一个2/2并具有吸血的战地医师。",
    ),
    ConditionalContract(
        "CORE_BT_035",
        "混乱打击",
        "在本回合中，使你的英雄获得+2攻击力。抽一张牌。",
        CardDef(
            "CORE_BT_035",
            "混乱打击",
            CardType.SPELL,
            2,
            effects=(Effect("temporary_hero_attack", attack=2), Effect("draw", 1)),
            spell_school="FEL",
        ),
        "play_spell",
        "我方英雄在本回合获得2点攻击力，并从牌库抽一张牌。",
    ),
    ConditionalContract(
        "CORE_BT_072",
        "深度冻结",
        "冻结一个敌人。召唤两个3/6的水元素。",
        CardDef(
            "CORE_BT_072",
            "深度冻结",
            CardType.SPELL,
            7,
            target_mode=TargetMode.ENEMY_CHARACTER,
            effects=(
                Effect("freeze"),
                Effect("summon", 2, card_id="CS2_033"),
            ),
            spell_school="FROST",
        ),
        "freeze_enemy",
        "敌方英雄被冻结，我方召唤两个3/6的水元素。",
    ),
    ConditionalContract(
        "CORE_CS2_072",
        "背刺",
        "对一个未受伤的随从造成2点 伤害。",
        CardDef(
            "CORE_CS2_072",
            "背刺",
            CardType.SPELL,
            0,
            target_mode=TargetMode.UNDAMAGED_MINION,
            effects=(Effect("damage", 2),),
        ),
        "backstab",
        "完整生命值的敌方随从是合法目标，并受到2点伤害。",
    ),
    ConditionalContract(
        "CORE_EX1_043",
        "暮光幼龙",
        "战吼： 你每有一张手牌，便获得+1生命值。",
        CardDef(
            "CORE_EX1_043",
            "暮光幼龙",
            CardType.MINION,
            4,
            4,
            1,
            races=("DRAGON",),
            effects=(Effect("buff_health_by_hand_count", health=1),),
        ),
        "play_with_three_cards",
        "使用暮光幼龙后手牌还剩三张，因此它由4/1变为4/4。",
    ),
    ConditionalContract(
        "CORE_EX1_103",
        "寒光先知",
        "战吼：使你的其他鱼人获得+2生命值。",
        CardDef(
            "CORE_EX1_103",
            "寒光先知",
            CardType.MINION,
            3,
            2,
            3,
            races=("MURLOC",),
            effects=(Effect("buff_other_friendly_race", health=2, race="MURLOC"),),
        ),
        "play_with_murloc",
        "另一个友方鱼人获得+2生命值，寒光先知自身不获得该战吼增益。",
    ),
    ConditionalContract(
        "CORE_EX1_193",
        "心灵咒术师",
        "战吼：复制你对手的牌库中的一张牌，并将其置入你的手牌。",
        CardDef(
            "CORE_EX1_193",
            "心灵咒术师",
            CardType.MINION,
            1,
            1,
            2,
            races=("UNDEAD",),
            effects=(Effect("copy_random_enemy_deck", 1),),
        ),
        "copy_enemy_deck",
        "敌方牌库只有一张测试牌；我方获得其复制，敌方牌库数量不变。",
    ),
    ConditionalContract(
        "CORE_GIL_534",
        "荆棘帮暴徒",
        "在你的英雄攻击后，使本随从获得+1/+1。",
        CardDef(
            "CORE_GIL_534",
            "荆棘帮暴徒",
            CardType.MINION,
            3,
            3,
            3,
            races=("QUILBOAR",),
            on_owner_hero_attack_effects=(
                Effect("buff", attack=1, health=1, target="played_minion"),
            ),
        ),
        "hero_attack",
        "我方英雄攻击后，荆棘帮暴徒由3/3变为4/4。",
    ),
    ConditionalContract(
        "CORE_GIL_623",
        "女巫森林灰熊",
        "嘲讽。战吼： 你的对手每有一张手牌，本随从便失去1点生命值。",
        CardDef(
            "CORE_GIL_623",
            "女巫森林灰熊",
            CardType.MINION,
            5,
            3,
            12,
            taunt=True,
            races=("BEAST",),
            effects=(Effect("lose_health_by_enemy_hand_count", 1),),
        ),
        "play_against_three_cards",
        "敌方有三张手牌，女巫森林灰熊进场后由3/12变为3/9。",
    ),
    ConditionalContract(
        "CORE_GVG_061",
        "作战动员",
        "召唤三个{0}的白银之手新兵，装备一把1/4的武器。",
        CardDef(
            "CORE_GVG_061",
            "作战动员",
            CardType.SPELL,
            3,
            effects=(
                Effect("summon", 3, card_id="CS2_101t"),
                Effect("equip_weapon", 1, card_id="CS2_091"),
            ),
        ),
        "play_spell",
        "我方召唤三个1/1白银之手新兵，并装备一把1/4的圣光的正义。",
    ),
    ConditionalContract(
        "CORE_KAR_061",
        "馆长",
        "嘲讽。战吼：抽取野兽牌，龙牌和鱼人牌各一张。",
        CardDef(
            "CORE_KAR_061",
            "馆长",
            CardType.MINION,
            5,
            4,
            6,
            taunt=True,
            races=("MECHANICAL",),
            effects=(
                Effect("draw_race", 1, race="BEAST"),
                Effect("draw_race", 1, race="DRAGON"),
                Effect("draw_race", 1, race="MURLOC"),
            ),
        ),
        "draw_three_races",
        "牌库中的野兽、龙和鱼人各有一张，战吼将三张全部抽入手牌。",
    ),
    ConditionalContract(
        "CORE_NEW1_021",
        "末日预言者",
        "在你的回合开始时，消灭所有随从。",
        CardDef(
            "CORE_NEW1_021",
            "末日预言者",
            CardType.MINION,
            2,
            0,
            7,
            on_owner_turn_start_effects=(Effect("destroy_all", target="all_minions"),),
        ),
        "owner_turn_start",
        "进入末日预言者拥有者的回合时，双方所有随从均被消灭。",
    ),
    ConditionalContract(
        "CORE_OG_218",
        "血蹄勇士",
        "嘲讽 受伤时拥有+3攻 击力。",
        CardDef(
            "CORE_OG_218",
            "血蹄勇士",
            CardType.MINION,
            4,
            2,
            6,
            taunt=True,
            damaged_attack_bonus=3,
        ),
        "damage_self",
        "血蹄勇士受到1点伤害后处于受伤状态，攻击力由2变为5。",
    ),
    ConditionalContract(
        "CORE_RLK_814",
        "异教水晶工匠",
        "战吼：如果你的手牌中有暗影法术牌，获得+1/+1。",
        CardDef(
            "CORE_RLK_814",
            "异教水晶工匠",
            CardType.MINION,
            1,
            1,
            2,
            effects=(
                Effect(
                    "buff_if_hand_spell_school",
                    attack=1,
                    health=1,
                    keyword="SHADOW",
                    target="played_minion",
                ),
            ),
        ),
        "play_with_shadow_spell",
        "使用后手牌中仍有暗影法术，异教水晶工匠由1/2变为2/3。",
    ),
    ConditionalContract(
        "CORE_UNG_928",
        "焦油爬行者",
        "嘲讽 在你对手的回合拥有+2攻击力。",
        CardDef(
            "CORE_UNG_928",
            "焦油爬行者",
            CardType.MINION,
            3,
            1,
            5,
            taunt=True,
            races=("ELEMENTAL",),
            opponent_turn_attack_bonus=2,
        ),
        "opponent_turn",
        "我方结束回合后进入对手回合，焦油爬行者的攻击力由1变为3。",
    ),
    ConditionalContract(
        "CORE_WON_351",
        "蹩脚海盗",
        "如果你装备着武器，本随从拥有 +2攻击力。",
        CardDef(
            "CORE_WON_351",
            "蹩脚海盗",
            CardType.MINION,
            1,
            1,
            2,
            races=("PIRATE",),
            weapon_attack_bonus=2,
        ),
        "play_with_weapon",
        "我方装备着武器，蹩脚海盗进场后攻击力由1变为3。",
    ),
    ConditionalContract(
        "CORE_EX1_414",
        "格罗玛什·地狱咆哮",
        "冲锋 受伤时拥有+6攻 击力。",
        CardDef(
            "CORE_EX1_414",
            "格罗玛什·地狱咆哮",
            CardType.MINION,
            8,
            4,
            9,
            charge=True,
            damaged_attack_bonus=6,
        ),
        "damage_self",
        "格罗玛什受到1点伤害后处于受伤状态，攻击力由4变为10。",
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
        "我方手牌": own["zones"]["hand"],
        "敌方手牌数": enemy["zones"]["hand"]["count"],
        "我方牌库": own["zones"]["deck"],
        "敌方牌库": enemy["zones"]["deck"],
        "我方场上": own["zones"]["board"],
        "敌方场上": enemy["zones"]["board"],
        "我方武器": own["zones"]["weapon"],
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
        charge=card.charge,
        races=card.races,
        summoned_turn=0,
    )


def build_review_scenario(card_id: str, card_registry: Mapping[str, CardDef]) -> Dict[str, Any]:
    if card_id not in CONTRACTS:
        raise ValueError("unknown conditional state batch card: {}".format(card_id))
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
    own.deck = ["STATE_TEST_DRAW"]
    opposing.deck = ["STATE_TEST_DRAW"]
    own.hand = []
    opposing.hand = []
    own.board = []
    opposing.board = []
    source_entity_id = 130_000

    if contract.scenario in {
        "cast_holy_spell",
        "hero_attack",
        "owner_turn_start",
        "damage_self",
        "opponent_turn",
    }:
        own.board = [_minion(card_id, 130_001, registry)]
        source_entity_id = 130_001

    if contract.scenario == "cast_holy_spell":
        own.hand = [HandCard(130_010, "STATE_TEST_HOLY")]
        source_entity_id = 130_010
        action = Action(ActionType.PLAY, 130_010)
    elif contract.scenario == "hero_attack":
        own.weapon = Weapon(130_020, "STATE_TEST_WEAPON", 2, 2)
        own.hero_attack = 2
        action = Action(ActionType.HERO_ATTACK, 130_020, TargetRef.hero(enemy))
    elif contract.scenario == "owner_turn_start":
        opposing.board = [_minion("STATE_TEST_MINION", 130_021, registry)]
        game.state.active_player = enemy
        action = Action.end_turn()
    elif contract.scenario == "damage_self":
        action = Action(ActionType.HERO_POWER, target=TargetRef.minion(owner, 130_001))
    elif contract.scenario == "opponent_turn":
        action = Action.end_turn()
    else:
        own.hand = [HandCard(130_000, card_id)]
        action = Action(ActionType.PLAY, 130_000)
        if contract.scenario == "freeze_enemy":
            action = Action(ActionType.PLAY, 130_000, TargetRef.hero(enemy))
        elif contract.scenario == "backstab":
            opposing.board = [_minion("STATE_TEST_MINION", 130_030, registry)]
            action = Action(ActionType.PLAY, 130_000, TargetRef.minion(enemy, 130_030))
        elif contract.scenario == "play_with_three_cards":
            own.hand.extend(HandCard(130_031 + index, "STATE_TEST_MINION") for index in range(3))
        elif contract.scenario == "play_with_murloc":
            own.board = [_minion("STATE_TEST_MURLOC", 130_040, registry)]
        elif contract.scenario == "copy_enemy_deck":
            opposing.deck = ["STATE_TEST_DRAGON"]
        elif contract.scenario == "play_against_three_cards":
            opposing.hand = [HandCard(130_050 + index, "STATE_TEST_MINION") for index in range(3)]
        elif contract.scenario == "draw_three_races":
            own.deck = [
                "STATE_TEST_BEAST",
                "STATE_TEST_DRAGON",
                "STATE_TEST_MURLOC",
            ]
        elif contract.scenario == "play_with_shadow_spell":
            own.hand.append(HandCard(130_060, "STATE_TEST_SHADOW"))
        elif contract.scenario == "play_with_weapon":
            own.weapon = Weapon(130_070, "STATE_TEST_WEAPON", 2, 2)
            own.hero_attack = 2

    before = review_state_from_observation(game.observation(owner))
    acting_player = game.state.active_player
    game.apply(action)
    after = review_state_from_observation(game.observation(owner))
    return {
        "scenario_id": "{}-conditional-state-review-v1".format(card_id.lower().replace("_", "-")),
        "title_zh": "{}：条件与状态核验".format(contract.name_zh),
        "purpose_zh": "核对条件目标、动态属性、手牌牌库和回合边界的完整结算。",
        "before": before,
        "action": {
            "type": action.action_type.value,
            "actor_player_id": acting_player,
            "source_entity_id": source_entity_id,
            "card_id": card_id,
            "target": action.to_dict()["target"],
            "description_zh": "执行《{}》的确定性条件测试。".format(contract.name_zh),
            "engine_action": action.to_dict(),
        },
        "after": after,
        "assertions": [
            {
                "assertion_id": "conditional-outcome",
                "subject_zh": "条件相关的英雄、手牌、牌库、场面与武器",
                "before": _focus(before),
                "after": _focus(after),
                "expected_zh": contract.expected_zh,
            }
        ],
        "special_cases": [
            {
                "kind": "special_tags",
                "summary_zh": "条件、持续时间或动态状态单独记录。",
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
