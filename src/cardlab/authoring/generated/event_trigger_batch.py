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
    Weapon,
)
from ..review_format import review_state_from_observation

SOURCE_VERSION = "250339"
GENERATED_BY = "codex-gpt-5.6-core-event-trigger-batch-v1"

TOKEN_CARDS: Dict[str, CardDef] = {
    "TTN_843t1": CardDef(
        "TTN_843t1",
        "入侵的魔蝠",
        CardType.MINION,
        1,
        1,
        1,
        rush=True,
        races=("DEMON",),
        collectible=False,
    ),
}

SUPPORT_CARDS: Dict[str, CardDef] = {
    "EVENT_TEST_SPELL": CardDef(
        "EVENT_TEST_SPELL",
        "测试法术",
        CardType.SPELL,
        0,
        collectible=False,
    ),
    "EVENT_DRAW_SPELL": CardDef(
        "EVENT_DRAW_SPELL",
        "测试抽牌法术",
        CardType.SPELL,
        0,
        effects=(Effect("draw", 1),),
        collectible=False,
    ),
    "EVENT_TEST_ELEMENTAL": CardDef(
        "EVENT_TEST_ELEMENTAL",
        "测试元素",
        CardType.MINION,
        1,
        2,
        2,
        races=("ELEMENTAL",),
        collectible=False,
    ),
    "EVENT_TEST_MURLOC": CardDef(
        "EVENT_TEST_MURLOC",
        "测试鱼人",
        CardType.MINION,
        1,
        2,
        1,
        races=("MURLOC",),
        collectible=False,
    ),
    "EVENT_TEST_MINION": CardDef(
        "EVENT_TEST_MINION",
        "测试随从",
        CardType.MINION,
        1,
        1,
        6,
        collectible=False,
    ),
    "EVENT_TEST_DRAW": CardDef(
        "EVENT_TEST_DRAW",
        "测试牌库牌",
        CardType.MINION,
        1,
        1,
        1,
        collectible=False,
    ),
    "EVENT_TEST_WEAPON": CardDef(
        "EVENT_TEST_WEAPON",
        "测试武器",
        CardType.WEAPON,
        1,
        2,
        durability=2,
        collectible=False,
    ),
    "CS2_029": CardDef(
        "CS2_029",
        "火球术",
        CardType.SPELL,
        4,
        collectible=False,
    ),
}


@dataclass(frozen=True)
class EventContract:
    card_id: str
    name_zh: str
    source_text_zh: str
    definition: CardDef
    scenario: str
    expected_zh: str


_CONTRACTS = (
    EventContract(
        "CORE_EX1_007",
        "苦痛侍僧",
        "每当本随从受到伤害，抽一张牌。",
        CardDef(
            "CORE_EX1_007",
            "苦痛侍僧",
            CardType.MINION,
            3,
            1,
            4,
            on_damage_effects=(Effect("draw", 1),),
        ),
        "take_damage",
        "苦痛侍僧受到1点伤害，我方从牌库抽一张牌。",
    ),
    EventContract(
        "CORE_EX1_604",
        "暴乱狂战士",
        "每当一个随从 受到伤害，便获得+1攻击力。",
        CardDef(
            "CORE_EX1_604",
            "暴乱狂战士",
            CardType.MINION,
            3,
            2,
            4,
            on_any_minion_damaged_effects=(Effect("buff", attack=1, target="played_minion"),),
        ),
        "other_minion_damaged",
        "敌方随从受到1点伤害后，暴乱狂战士的攻击力从2变为3。",
    ),
    EventContract(
        "CORE_BT_351",
        "战斗邪犬",
        "在你的英雄攻击后，获得+1攻击力。",
        CardDef(
            "CORE_BT_351",
            "战斗邪犬",
            CardType.MINION,
            1,
            1,
            2,
            races=("DEMON",),
            on_owner_hero_attack_effects=(Effect("buff", attack=1, target="played_minion"),),
        ),
        "hero_attack",
        "我方英雄完成攻击后，战斗邪犬的攻击力从1变为2。",
    ),
    EventContract(
        "CORE_NX2_028",
        "钩拳-3000型",
        "在你的英雄攻击后，获得4点护甲值并抽一张牌。",
        CardDef(
            "CORE_NX2_028",
            "钩拳-3000型",
            CardType.MINION,
            3,
            4,
            3,
            races=("MECHANICAL", "PIRATE"),
            on_owner_hero_attack_effects=(
                Effect("armor", 4, target="owner_hero"),
                Effect("draw", 1),
            ),
        ),
        "hero_attack",
        "我方英雄完成攻击后获得4点护甲，并从牌库抽一张牌。",
    ),
    EventContract(
        "CORE_BT_510",
        "怒刺蛮兵",
        "嘲讽 在本随从被攻击后，对所有敌人造成1点伤害。",
        CardDef(
            "CORE_BT_510",
            "怒刺蛮兵",
            CardType.MINION,
            5,
            3,
            6,
            taunt=True,
            races=("DEMON",),
            on_attacked_effects=(Effect("damage_all", 1, target="enemy_characters"),),
        ),
        "attacked",
        "怒刺蛮兵承受攻击并存活后，对其所有敌人造成1点伤害。",
    ),
    EventContract(
        "CORE_EX1_509",
        "鱼人招潮者",
        "每当你召唤一个鱼人，便获得 +1攻击力。",
        CardDef(
            "CORE_EX1_509",
            "鱼人招潮者",
            CardType.MINION,
            1,
            1,
            2,
            races=("MURLOC",),
            on_friendly_summon_effects=(Effect("buff", attack=1, target="played_minion"),),
            on_friendly_summon_race="MURLOC",
        ),
        "play_murloc",
        "另一个鱼人被召唤后，鱼人招潮者的攻击力从1变为2。",
    ),
    EventContract(
        "CORE_WC_042",
        "哀嚎蒸汽",
        "在你使用一张元素牌后，获得+1攻击力。",
        CardDef(
            "CORE_WC_042",
            "哀嚎蒸汽",
            CardType.MINION,
            1,
            1,
            3,
            races=("ELEMENTAL",),
            on_friendly_play_effects=(Effect("buff", attack=1, target="played_minion"),),
            on_friendly_play_race="ELEMENTAL",
        ),
        "play_elemental",
        "我方使用另一张元素随从牌后，哀嚎蒸汽的攻击力从1变为2。",
    ),
    EventContract(
        "CORE_GVG_103",
        "微型战斗机甲",
        "在每个回合开始时，获得+1攻击力。",
        CardDef(
            "CORE_GVG_103",
            "微型战斗机甲",
            CardType.MINION,
            2,
            1,
            2,
            races=("MECHANICAL",),
            on_each_turn_start_effects=(Effect("buff", attack=1, target="played_minion"),),
        ),
        "next_turn",
        "进入对手回合时，微型战斗机甲的攻击力从1变为2。",
    ),
    EventContract(
        "CORE_ICC_210",
        "暗影升腾者",
        "在你的回合结束时，随机使另一个友方随从获得+1/+1。",
        CardDef(
            "CORE_ICC_210",
            "暗影升腾者",
            CardType.MINION,
            2,
            2,
            3,
            races=("UNDEAD",),
            on_owner_turn_end_effects=(Effect("random_buff_other_friendly", attack=1, health=1),),
        ),
        "end_turn_with_friend",
        "回合结束时唯一的另一名友方随从获得+1/+1。",
    ),
    EventContract(
        "CORE_ULD_133",
        "水晶商人",
        "在你的回合结束时，如果你有未使用的法力水晶，抽一张牌。",
        CardDef(
            "CORE_ULD_133",
            "水晶商人",
            CardType.MINION,
            2,
            1,
            4,
            on_owner_turn_end_effects=(Effect("draw_if_unused_mana", 1),),
        ),
        "end_turn_unused_mana",
        "我方带着未使用的法力结束回合，因此从牌库抽一张牌。",
    ),
    EventContract(
        "CORE_YOP_034",
        "窜逃的黑翼龙",
        "在你的回合结束时，随机对一个敌方随从造成10点伤害。",
        CardDef(
            "CORE_YOP_034",
            "窜逃的黑翼龙",
            CardType.MINION,
            10,
            10,
            10,
            races=("DRAGON",),
            on_owner_turn_end_effects=(Effect("random_damage_minion", 10),),
        ),
        "end_turn_enemy_minion",
        "回合结束时唯一的敌方随从受到10点伤害并死亡。",
    ),
    EventContract(
        "CORE_BT_493",
        "愤怒的女祭司",
        "在你的回合结束时，造成6点伤害，随机分配到所有敌人身上。",
        CardDef(
            "CORE_BT_493",
            "愤怒的女祭司",
            CardType.MINION,
            7,
            6,
            7,
            races=("DEMON",),
            on_owner_turn_end_effects=(Effect("random_damage", 1, repeats=6),),
        ),
        "end_turn_enemy_hero",
        "敌方没有随从，回合结束时6点随机伤害全部命中敌方英雄。",
    ),
    EventContract(
        "CORE_DRG_256",
        "灭龙弩炮",
        "在你使用你的英雄技能后，随机对一个敌人造成5点伤害。",
        CardDef(
            "CORE_DRG_256",
            "灭龙弩炮",
            CardType.MINION,
            4,
            3,
            5,
            races=("MECHANICAL",),
            on_owner_hero_power_effects=(Effect("random_damage", 5),),
        ),
        "hero_power",
        "敌方没有随从，英雄技能及弩炮的5点伤害均命中敌方英雄。",
    ),
    EventContract(
        "CORE_EX1_559",
        "大法师安东尼达斯",
        "每当你施放一个法术，将一张“火球术”法术牌置入你的手牌。",
        CardDef(
            "CORE_EX1_559",
            "大法师安东尼达斯",
            CardType.MINION,
            7,
            5,
            7,
            on_owner_spell_cast_effects=(Effect("add_to_hand", 1, card_id="CS2_029"),),
        ),
        "cast_spell",
        "施放测试法术后，我方手牌新增一张火球术。",
    ),
    EventContract(
        "CORE_NEW1_020",
        "狂野炎术师",
        "在你施放一个法术后，对所有随从造成1点伤害。",
        CardDef(
            "CORE_NEW1_020",
            "狂野炎术师",
            CardType.MINION,
            2,
            3,
            2,
            races=("UNDEAD",),
            on_owner_spell_cast_effects=(Effect("damage_all", 1, target="all_minions"),),
        ),
        "cast_spell_with_minions",
        "施放测试法术后，双方场上的所有随从各受到1点伤害。",
    ),
    EventContract(
        "CORE_RLK_083",
        "死亡寒冰",
        "在你施放一个法术后，随机对两个敌人造成1点伤害。",
        CardDef(
            "CORE_RLK_083",
            "死亡寒冰",
            CardType.MINION,
            2,
            2,
            3,
            races=("ELEMENTAL",),
            on_owner_spell_cast_effects=(Effect("random_damage_distinct", 1, repeats=2),),
        ),
        "cast_spell_two_enemies",
        "敌方只有英雄和一个随从；施法后两个不同敌人各受到1点伤害。",
    ),
    EventContract(
        "CORE_TTN_843",
        "艾瑞达欺诈者",
        "每当你抽一张牌时，召唤一个1/1并具有突袭的恶魔。",
        CardDef(
            "CORE_TTN_843",
            "艾瑞达欺诈者",
            CardType.MINION,
            4,
            3,
            5,
            races=("DEMON",),
            on_owner_draw_effects=(Effect("summon", 1, card_id="TTN_843t1"),),
        ),
        "draw_card",
        "测试法术抽一张牌时，艾瑞达欺诈者召唤一个1/1突袭恶魔。",
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
        raise ValueError("unknown event trigger batch card: {}".format(card_id))
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
    own.hero_armor = opposing.hero_armor = 0
    own.mana = own.max_mana = 10
    opposing.mana = opposing.max_mana = 10
    own.hand = []
    opposing.hand = []
    own.deck = ["EVENT_TEST_DRAW"]
    opposing.deck = ["EVENT_TEST_DRAW"]
    own.board = [_minion(card_id, 120_000, registry)]
    opposing.board = []
    source_entity_id = 120_000

    if contract.scenario == "take_damage":
        action = Action(ActionType.HERO_POWER, target=TargetRef.minion(owner, 120_000))
    elif contract.scenario == "other_minion_damaged":
        opposing.board = [_minion("EVENT_TEST_MINION", 120_010, registry)]
        action = Action(ActionType.HERO_POWER, target=TargetRef.minion(enemy, 120_010))
    elif contract.scenario == "hero_attack":
        own.weapon = Weapon(120_020, "EVENT_TEST_WEAPON", 2, 2)
        own.hero_attack = 2
        action = Action(ActionType.HERO_ATTACK, 120_020, TargetRef.hero(enemy))
    elif contract.scenario == "attacked":
        own.board = [_minion("EVENT_TEST_MINION", 120_030, registry)]
        opposing.board = [_minion(card_id, 120_000, registry)]
        source_entity_id = 120_030
        action = Action(ActionType.ATTACK, 120_030, TargetRef.minion(enemy, 120_000))
    elif contract.scenario in {"play_murloc", "play_elemental"}:
        played_id = (
            "EVENT_TEST_MURLOC" if contract.scenario == "play_murloc" else "EVENT_TEST_ELEMENTAL"
        )
        own.hand = [HandCard(120_040, played_id)]
        source_entity_id = 120_040
        action = Action(ActionType.PLAY, 120_040)
    elif contract.scenario == "next_turn":
        action = Action.end_turn()
    elif contract.scenario.startswith("end_turn"):
        action = Action.end_turn()
        if contract.scenario == "end_turn_with_friend":
            own.board.append(_minion("EVENT_TEST_MINION", 120_050, registry))
        elif contract.scenario == "end_turn_unused_mana":
            own.mana = 1
        elif contract.scenario == "end_turn_enemy_minion":
            opposing.board = [_minion("EVENT_TEST_MINION", 120_060, registry)]
    elif contract.scenario == "hero_power":
        action = Action(ActionType.HERO_POWER, target=TargetRef.hero(enemy))
    elif contract.scenario.startswith("cast_spell"):
        own.hand = [HandCard(120_070, "EVENT_TEST_SPELL")]
        source_entity_id = 120_070
        action = Action(ActionType.PLAY, 120_070)
        if contract.scenario == "cast_spell_with_minions":
            own.board.append(_minion("EVENT_TEST_MINION", 120_071, registry))
            opposing.board = [_minion("EVENT_TEST_MINION", 120_072, registry)]
        elif contract.scenario == "cast_spell_two_enemies":
            opposing.board = [_minion("EVENT_TEST_MINION", 120_073, registry)]
    elif contract.scenario == "draw_card":
        own.hand = [HandCard(120_080, "EVENT_DRAW_SPELL")]
        source_entity_id = 120_080
        action = Action(ActionType.PLAY, 120_080)
    else:
        raise RuntimeError("unsupported event scenario: {}".format(contract.scenario))

    before = review_state_from_observation(game.observation(owner))
    game.apply(action)
    after = review_state_from_observation(game.observation(owner))
    return {
        "scenario_id": "{}-event-trigger-review-v1".format(card_id.lower().replace("_", "-")),
        "title_zh": "{}：事件触发核验".format(contract.name_zh),
        "purpose_zh": "核对触发时机、触发来源与结算后的英雄及区域状态。",
        "before": before,
        "action": {
            "type": action.action_type.value,
            "actor_player_id": owner,
            "source_entity_id": source_entity_id,
            "card_id": card_id,
            "target": action.to_dict()["target"],
            "description_zh": "执行会触发《{}》的确定性测试动作。".format(contract.name_zh),
            "engine_action": action.to_dict(),
        },
        "after": after,
        "assertions": [
            {
                "assertion_id": "event-outcome",
                "subject_zh": "触发随从及其影响的英雄、手牌、牌库和场面",
                "before": _focus(before),
                "after": _focus(after),
                "expected_zh": contract.expected_zh,
            }
        ],
        "special_cases": [
            {
                "kind": "special_tags",
                "summary_zh": "事件类型与触发条件单独记录。",
                "details": {
                    "entity_id": 120_000,
                    "card_id": card_id,
                    "tags_before": {"scenario": contract.scenario},
                    "tags_after": {"trigger_resolved": True},
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
