from __future__ import annotations

from dataclasses import dataclass
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
GENERATED_BY = "codex-gpt-5.6-core-dynamic-zone-batch-v1"

TOKEN_CARDS: Dict[str, CardDef] = {
    "EX1_014t": CardDef(
        "EX1_014t",
        "香蕉",
        CardType.SPELL,
        1,
        target_mode=TargetMode.ANY_MINION,
        effects=(Effect("buff", attack=1, health=1),),
        collectible=False,
    ),
    "hexfrog": CardDef(
        "hexfrog",
        "青蛙",
        CardType.MINION,
        0,
        0,
        1,
        taunt=True,
        races=("BEAST",),
        collectible=False,
    ),
    "RLK_063t": CardDef(
        "RLK_063t",
        "冰霜巨龙",
        CardType.MINION,
        5,
        5,
        5,
        races=("UNDEAD", "DRAGON"),
        collectible=False,
    ),
    "SW_108t": CardDef(
        "SW_108t",
        "传承之火",
        CardType.SPELL,
        1,
        target_mode=TargetMode.ANY_MINION,
        effects=(Effect("damage", 2),),
        collectible=False,
        spell_school="FIRE",
    ),
    "TRL_348t": CardDef(
        "TRL_348t",
        "山猫",
        CardType.MINION,
        1,
        1,
        1,
        rush=True,
        races=("BEAST",),
        collectible=False,
    ),
    "TSC_076t": CardDef(
        "TSC_076t",
        "残损的雕像",
        CardType.MINION,
        1,
        1,
        2,
        taunt=True,
        races=("ELEMENTAL",),
        collectible=False,
    ),
    "TSC_076t2": CardDef(
        "TSC_076t2",
        "生动的雕像",
        CardType.MINION,
        3,
        2,
        4,
        taunt=True,
        races=("ELEMENTAL",),
        collectible=False,
    ),
    "TSC_076t3": CardDef(
        "TSC_076t3",
        "光鲜的雕像",
        CardType.MINION,
        5,
        4,
        8,
        taunt=True,
        races=("ELEMENTAL",),
        collectible=False,
    ),
    "UNG_809t1": CardDef(
        "UNG_809t1",
        "烈焰元素",
        CardType.MINION,
        1,
        1,
        2,
        races=("ELEMENTAL",),
        collectible=False,
    ),
}

SUPPORT_CARDS: Dict[str, CardDef] = {
    "CORE_CS2_024": CardDef(
        "CORE_CS2_024",
        "寒冰箭",
        CardType.SPELL,
        2,
        spell_school="FROST",
    )
}


@dataclass(frozen=True)
class DynamicContract:
    card_id: str
    name_zh: str
    source_text_zh: str
    definition: CardDef
    scenario: str
    expected_zh: str


_CONTRACTS = (
    DynamicContract(
        "CORE_RLK_087",
        "窒息",
        "消灭攻击力最高的敌方随从。",
        CardDef(
            "CORE_RLK_087",
            "窒息",
            CardType.SPELL,
            3,
            effects=(Effect("destroy_highest_attack_enemy"),),
            spell_school="SHADOW",
        ),
        "play_no_target",
        "攻击力最高的敌方冰风雪人被消灭，低攻击力随从保留。",
    ),
    DynamicContract(
        "CORE_EX1_198",
        "娜塔莉·塞林",
        "战吼：消灭一个随从并获得其生命值。",
        CardDef(
            "CORE_EX1_198",
            "娜塔莉·塞林",
            CardType.MINION,
            7,
            7,
            1,
            target_mode=TargetMode.ANY_MINION,
            effects=(Effect("destroy_and_gain_health"),),
        ),
        "play_target_minion",
        "消灭6血随从后，娜塔莉的当前生命值和生命上限从1增加到7。",
    ),
    DynamicContract(
        "CORE_ULD_165",
        "裂隙屠夫",
        "战吼：消灭一个随从。你的英雄受到等同于该随从生命值的 伤害。",
        CardDef(
            "CORE_ULD_165",
            "裂隙屠夫",
            CardType.MINION,
            6,
            7,
            5,
            target_mode=TargetMode.ANY_MINION,
            effects=(Effect("destroy_and_damage_owner_by_health"),),
            races=("DEMON",),
        ),
        "play_target_minion",
        "消灭6血随从后，我方英雄受到6点伤害。",
    ),
    DynamicContract(
        "CORE_SCH_512",
        "通窍",
        "对一个随从造成4点伤害。如果该随从死亡，召唤一个新的复制。",
        CardDef(
            "CORE_SCH_512",
            "通窍",
            CardType.SPELL,
            6,
            target_mode=TargetMode.ANY_MINION,
            effects=(
                Effect("damage", 4),
                Effect("summon_copy_if_selected_dead", 1, target="owner"),
            ),
            spell_school="SHADOW",
        ),
        "play_target_small_minion",
        "4点伤害消灭所选小精灵，我方召唤一个全新的1/1小精灵。",
    ),
    DynamicContract(
        "CORE_ICC_214",
        "黑曜石雕像",
        "嘲讽，吸血 亡语：随机消灭一个敌方随从。",
        CardDef(
            "CORE_ICC_214",
            "黑曜石雕像",
            CardType.MINION,
            9,
            4,
            8,
            taunt=True,
            lifesteal=True,
            deathrattle_effects=(Effect("destroy_random_enemy_minion"),),
        ),
        "deathrattle",
        "黑曜石雕像死亡后，唯一的敌方随从被亡语消灭。",
    ),
    DynamicContract(
        "CORE_ULD_280",
        "沙赫柯特工兵",
        "亡语：随机将一个敌方随从移回对手的 手牌。",
        CardDef(
            "CORE_ULD_280",
            "沙赫柯特工兵",
            CardType.MINION,
            4,
            4,
            4,
            races=("PIRATE",),
            deathrattle_effects=(Effect("return_random_enemy_minion_to_hand"),),
        ),
        "deathrattle",
        "沙赫柯特工兵死亡后，唯一的敌方随从离场并回到敌方手牌。",
    ),
    DynamicContract(
        "CORE_AT_123",
        "冰喉",
        "嘲讽，亡语： 如果你的手牌中有龙牌，则对所有随从造成3点伤害。",
        CardDef(
            "CORE_AT_123",
            "冰喉",
            CardType.MINION,
            7,
            6,
            6,
            taunt=True,
            races=("UNDEAD", "DRAGON"),
            deathrattle_effects=(
                Effect("damage_all_if_hand_race", 3, target="all_minions", race="DRAGON"),
            ),
        ),
        "deathrattle_with_dragon",
        "手牌中持有龙牌时，冰喉亡语对双方其余随从各造成3点伤害。",
    ),
    DynamicContract(
        "CS3_024",
        "泰兰·弗丁",
        "嘲讽，圣盾 亡语：抽取你的法力值消耗最高的 随从牌。",
        CardDef(
            "CS3_024",
            "泰兰·弗丁",
            CardType.MINION,
            5,
            3,
            3,
            taunt=True,
            divine_shield=True,
            deathrattle_effects=(Effect("draw_highest_cost_minion", 1, target="owner"),),
        ),
        "deathrattle_draw_highest",
        "泰兰死亡后，从牌库抽取法力值最高的石拳食人魔。",
    ),
    DynamicContract(
        "RLK_511",
        "寒冬先锋",
        "亡语：抽一张冰霜法术牌。",
        CardDef(
            "RLK_511",
            "寒冬先锋",
            CardType.MINION,
            2,
            3,
            2,
            races=("UNDEAD",),
            deathrattle_effects=(Effect("draw_spell_school", 1, target="owner", keyword="FROST"),),
        ),
        "deathrattle_draw_frost",
        "寒冬先锋死亡后，从牌库抽取冰霜法术寒冰箭，并保留非冰霜牌。",
    ),
    DynamicContract(
        "CORE_RLK_063",
        "冰霜巨龙之怒",
        "造成5点伤害。冻结所有敌方随从。召唤一条5/5的冰霜巨龙。",
        CardDef(
            "CORE_RLK_063",
            "冰霜巨龙之怒",
            CardType.SPELL,
            7,
            target_mode=TargetMode.ANY_CHARACTER,
            effects=(
                Effect("damage", 5),
                Effect("freeze_all", target="enemy_minions"),
                Effect("summon", 1, target="owner", card_id="RLK_063t"),
            ),
            spell_school="FROST",
        ),
        "play_target_enemy_hero",
        "敌方英雄受到5点伤害，所有敌方随从被冻结，我方召唤5/5冰霜巨龙。",
    ),
    DynamicContract(
        "CORE_TSC_076",
        "永存石中",
        "召唤具有嘲讽的4/8，2/4，1/2的元素各一个。",
        CardDef(
            "CORE_TSC_076",
            "永存石中",
            CardType.SPELL,
            7,
            effects=(
                Effect(
                    "summon_sequence",
                    target="owner",
                    card_ids=("TSC_076t3", "TSC_076t2", "TSC_076t"),
                ),
            ),
            spell_school="HOLY",
        ),
        "play_no_target_empty_board",
        "依次召唤4/8、2/4、1/2的嘲讽元素，各生成独立实体。",
    ),
    DynamicContract(
        "CORE_EX1_246",
        "妖术",
        "使一个随从变形成为一只0/1并具有嘲讽的青蛙。",
        CardDef(
            "CORE_EX1_246",
            "妖术",
            CardType.SPELL,
            3,
            target_mode=TargetMode.ANY_MINION,
            effects=(Effect("transform", 1, card_id="hexfrog"),),
            spell_school="NATURE",
        ),
        "play_target_minion",
        "所选随从保留实体编号，但卡牌、属性和标签重置为0/1嘲讽野兽青蛙。",
    ),
    DynamicContract(
        "CORE_EX1_310",
        "末日守卫",
        "冲锋，战吼：随机弃两张牌。",
        CardDef(
            "CORE_EX1_310",
            "末日守卫",
            CardType.MINION,
            5,
            5,
            7,
            charge=True,
            races=("DEMON",),
            effects=(Effect("discard_random", 2, target="owner"),),
        ),
        "play_with_extra_hand",
        "末日守卫进场后，从剩余三张手牌中随机弃两张，只保留一张。",
    ),
    DynamicContract(
        "CORE_ICC_407",
        "侏儒吸血鬼",
        "战吼：移除你对手的牌库顶的一张牌。",
        CardDef(
            "CORE_ICC_407",
            "侏儒吸血鬼",
            CardType.MINION,
            2,
            2,
            3,
            races=("UNDEAD",),
            effects=(Effect("remove_enemy_deck_top", 1, target="enemy"),),
        ),
        "play_no_target",
        "移除敌方牌库顶牌，敌方手牌数量不变。",
    ),
    DynamicContract(
        "CORE_EX1_014",
        "穆克拉",
        "战吼：使你的对手获得两根香蕉。",
        CardDef(
            "CORE_EX1_014",
            "穆克拉",
            CardType.MINION,
            3,
            5,
            6,
            races=("BEAST",),
            effects=(Effect("add_to_opponent_hand", 2, card_id="EX1_014t"),),
        ),
        "play_no_target",
        "穆克拉进场后，敌方手牌新增两张可使用的香蕉。",
    ),
    DynamicContract(
        "CORE_UNG_809",
        "火羽精灵",
        "战吼：将一张1/2的元素牌置入你的手牌。",
        CardDef(
            "CORE_UNG_809",
            "火羽精灵",
            CardType.MINION,
            1,
            1,
            2,
            races=("ELEMENTAL",),
            effects=(Effect("add_to_hand", 1, card_id="UNG_809t1"),),
        ),
        "play_no_target",
        "火羽精灵进场后，我方手牌新增一张1/2元素。",
    ),
    DynamicContract(
        "CORE_SW_108",
        "初始之火",
        "对一个随从造成2点伤害。将“传承之火”置入你的手牌。",
        CardDef(
            "CORE_SW_108",
            "初始之火",
            CardType.SPELL,
            1,
            target_mode=TargetMode.ANY_MINION,
            effects=(Effect("damage", 2), Effect("add_to_hand", 1, card_id="SW_108t")),
            spell_school="FIRE",
        ),
        "play_target_minion",
        "所选随从受到2点伤害，我方手牌新增传承之火。",
    ),
    DynamicContract(
        "CORE_TRL_900",
        "哈尔拉兹，山猫之神",
        "突袭。战吼：用1/1并具有突袭的山猫填满你的手牌。",
        CardDef(
            "CORE_TRL_900",
            "哈尔拉兹，山猫之神",
            CardType.MINION,
            4,
            4,
            2,
            rush=True,
            races=("BEAST",),
            effects=(Effect("fill_hand", 1, card_id="TRL_348t"),),
        ),
        "play_no_target",
        "哈尔拉兹进场后，用1/1突袭山猫把我方手牌补到10张。",
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
    "CS2_029": "火球术",
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
        "我方手牌": own["zones"]["hand"],
        "敌方手牌数": enemy["zones"]["hand"]["count"],
        "我方牌库": own["zones"]["deck"],
        "敌方牌库": enemy["zones"]["deck"],
        "我方场上": own["zones"]["board"],
        "敌方场上": enemy["zones"]["board"],
    }


def _deck_special_case(
    before: Mapping[str, Any], after: Mapping[str, Any], role_zh: str
) -> Dict[str, Any]:
    player_before = _player(before, role_zh)
    player_after = _player(after, role_zh)
    before_count = player_before["zones"]["deck"]["count"]
    after_count = player_after["zones"]["deck"]["count"]
    return {
        "kind": "deck_change",
        "summary_zh": "牌库数量变化单独记录。",
        "details": {
            "player_id": player_before["player_id"],
            "before_count": before_count,
            "after_count": after_count,
            "drawn_count": max(0, before_count - after_count),
            "added_count": 0,
            "shuffled_count": 0,
            "order_changed": False,
            "known_top_before": player_before["zones"]["deck"]["known_top_card_ids"],
            "known_top_after": player_after["zones"]["deck"]["known_top_card_ids"],
        },
    }


def build_review_scenario(card_id: str, card_registry: Mapping[str, CardDef]) -> Dict[str, Any]:
    if card_id not in CONTRACTS:
        raise ValueError("unknown dynamic zone batch card: {}".format(card_id))
    contract = CONTRACTS[card_id]
    registry = dict(card_registry)
    registry.update(SUPPORT_CARDS)
    game = Game(seed=sum(ord(char) for char in card_id), card_registry=registry)
    actor = game.state.active_player
    enemy = 1 - actor
    own = game.state.players[actor]
    opposing = game.state.players[enemy]
    own.hero_health = 15
    opposing.hero_health = 25
    own.deck = ["CS2_120", "CS2_200", "CS2_172"]
    opposing.deck = ["CS2_120", "CS2_172", "CS2_182"]
    own.hand = [HandCard(110_000, card_id)]
    opposing.hand = []
    own.board = [Minion(110_001, "CS2_120", 2, 3, 3, summoned_turn=0)]
    opposing.board = [
        Minion(110_002, "CS2_182", 4, 6, 6, summoned_turn=0),
        Minion(110_003, "CS2_231", 1, 1, 1, summoned_turn=0),
    ]
    own.mana = own.max_mana = 10
    opposing.mana = opposing.max_mana = 10

    target: Optional[TargetRef] = None
    action_type = "play_card"
    source_entity_id = 110_000
    if contract.scenario.startswith("deathrattle"):
        card = contract.definition
        own.hand = []
        own.board = [
            Minion(
                110_010,
                card_id,
                card.attack,
                1,
                card.health,
                taunt=card.taunt,
                lifesteal=card.lifesteal,
                races=card.races,
                summoned_turn=0,
            )
        ]
        source_entity_id = 110_010
        target = TargetRef.minion(actor, 110_010)
        action = Action(ActionType.HERO_POWER, target=target)
        action_type = "hero_power_destroy_fixture"
        if contract.scenario == "deathrattle":
            opposing.board = [opposing.board[0]]
        elif contract.scenario == "deathrattle_with_dragon":
            own.hand = [HandCard(110_020, "RLK_063t")]
        elif contract.scenario == "deathrattle_draw_highest":
            own.deck = ["CS2_120", "CS2_200", "CS2_172"]
        elif contract.scenario == "deathrattle_draw_frost":
            own.deck = ["CS2_029", "CORE_CS2_024"]
    else:
        if contract.scenario == "play_target_small_minion":
            target = TargetRef.minion(enemy, 110_003)
        elif contract.scenario == "play_target_enemy_hero":
            target = TargetRef.hero(enemy)
        elif contract.definition.target_mode != TargetMode.NONE:
            target = TargetRef.minion(enemy, 110_002)
        if contract.scenario == "play_with_extra_hand":
            own.hand.extend(
                [
                    HandCard(110_030, "CS2_120"),
                    HandCard(110_031, "CS2_172"),
                    HandCard(110_032, "CS2_200"),
                ]
            )
        elif contract.scenario == "play_no_target_empty_board":
            own.board = []
        action = Action(ActionType.PLAY, 110_000, target)

    before = review_state_from_observation(game.observation(actor))
    game.apply(action)
    after = review_state_from_observation(game.observation(actor))
    own_before = _player(before, "我方")
    own_after = _player(after, "我方")
    assertions = [
        {
            "assertion_id": "primary-outcome",
            "subject_zh": "效果涉及的英雄、手牌、牌库与场上实体",
            "before": _focus(before),
            "after": _focus(after),
            "expected_zh": contract.expected_zh,
        }
    ]
    if action.action_type == ActionType.PLAY:
        assertions.insert(
            0,
            {
                "assertion_id": "mana",
                "subject_zh": "我方法力",
                "before": own_before["resources"]["mana"],
                "after": own_after["resources"]["mana"],
                "expected_zh": "支付{}点法力".format(contract.definition.cost),
            },
        )

    special_cases = []
    if card_id in {"CORE_ICC_407", "CS3_024", "RLK_511"}:
        special_cases.append(
            _deck_special_case(
                before,
                after,
                "敌方" if card_id == "CORE_ICC_407" else "我方",
            )
        )
    if card_id in {
        "CORE_RLK_087",
        "CORE_ICC_214",
        "CORE_ULD_280",
        "CORE_EX1_246",
        "CORE_EX1_310",
        "CORE_AT_123",
    }:
        special_cases.append(
            {
                "kind": "special_tags",
                "summary_zh": "随机、变形或条件标签单独记录。",
                "details": {
                    "entity_id": source_entity_id,
                    "card_id": card_id,
                    "tags_before": {"scenario": contract.scenario},
                    "tags_after": {"resolved": True},
                    "explanation_zh": contract.expected_zh,
                },
            }
        )

    return {
        "scenario_id": "{}-dynamic-zone-review-v1".format(card_id.lower().replace("_", "-")),
        "title_zh": "{}：动态结算与区域变更".format(contract.name_zh),
        "purpose_zh": "核对动态数值、随机选择、牌库检索、变形或生成实体的完整结果。",
        "before": before,
        "action": {
            "type": action_type,
            "actor_player_id": actor,
            "source_entity_id": source_entity_id,
            "card_id": card_id,
            "target": action.to_dict()["target"],
            "description_zh": "执行《{}》的确定性核验局面。".format(contract.name_zh),
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
    "TOKEN_CARDS",
    "build_review_scenario",
]
