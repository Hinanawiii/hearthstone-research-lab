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
    Location,
    Minion,
    TargetMode,
    TargetRef,
)
from ..review_format import review_state_from_observation

SOURCE_VERSION = "250339"
GENERATED_BY = "codex-gpt-5.6-core-special-zone-mechanics-batch-v1"

OUTCAST_POOL = ("CORE_BT_491", "CORE_BT_801")
MINION_POOL = ("CS2_120", "CS2_182", "CS2_200")
SPELL_POOL = ("CS2_029", "CS2_023", "EX1_277")
BATTLECRY_POOL = ("CORE_BT_416", "CORE_REV_308", "CORE_WON_096")
ONE_COST_POOL = ("CS2_189", "CS1_042", "EX1_277")
EIGHT_COST_POOL = ("CORE_EX1_383",)
DARK_GIFT_BEAST_POOL = ("CS2_120", "CORE_EX1_162", "CORE_SW_072")

CARDS: Dict[str, CardDef] = {
    "CORE_ETC_523": CardDef(
        "CORE_ETC_523",
        "死亡金属骑士",
        CardType.MINION,
        3,
        3,
        4,
        taunt=True,
        rarity="RARE",
        pays_health_if_healed=True,
        has_battlecry=False,
    ),
    "CORE_BT_416": CardDef(
        "CORE_BT_416",
        "暴怒邪吼者",
        CardType.MINION,
        4,
        4,
        4,
        rarity="RARE",
        effects=(Effect("grant_next_demon_discount", 2),),
        has_battlecry=True,
    ),
    "CORE_CATA_001": CardDef(
        "CORE_CATA_001",
        "提克迪奥斯",
        CardType.MINION,
        9,
        9,
        8,
        races=("DEMON",),
        rarity="LEGENDARY",
        effects=(Effect("grant_next_demon_cost_zero_this_turn"),),
        grants_hero_immunity=True,
        has_battlecry=True,
    ),
    "CORE_YOP_001": CardDef(
        "CORE_YOP_001",
        "伊利达雷研习",
        CardType.SPELL,
        1,
        rarity="COMMON",
        effects=(
            Effect("discover_from_pool", card_ids=OUTCAST_POOL),
            Effect("grant_next_outcast_discount", 1),
        ),
    ),
    "CORE_OG_044": CardDef(
        "CORE_OG_044",
        "范达尔·鹿盔",
        CardType.MINION,
        4,
        3,
        6,
        rarity="LEGENDARY",
        choose_both_for_friendly=True,
    ),
    "CORE_ONY_018": CardDef(
        "CORE_ONY_018",
        "暴烈枭兽",
        CardType.MINION,
        5,
        4,
        5,
        rarity="RARE",
        choose_one_effects=(
            (Effect("heal", 8, target="owner_hero"),),
            (Effect("damage", 4),),
        ),
        choose_one_target_modes=(TargetMode.NONE, TargetMode.ANY_CHARACTER),
        has_battlecry=True,
    ),
    "Core_LOE_115": CardDef(
        "Core_LOE_115",
        "乌鸦神像",
        CardType.SPELL,
        1,
        rarity="COMMON",
        choose_one_effects=(
            (Effect("discover_from_pool", card_ids=MINION_POOL),),
            (Effect("discover_from_pool", card_ids=SPELL_POOL),),
        ),
        choose_one_target_modes=(TargetMode.NONE, TargetMode.NONE),
    ),
    "CORE_REV_308": CardDef(
        "CORE_REV_308",
        "迷宫向导",
        CardType.MINION,
        2,
        1,
        1,
        rarity="COMMON",
        effects=(Effect("summon_random_cost", 1, attack=2),),
        has_battlecry=True,
    ),
    "CORE_SCH_713": CardDef(
        "CORE_SCH_713",
        "异教低阶牧师",
        CardType.MINION,
        2,
        3,
        2,
        rarity="RARE",
        effects=(Effect("tax_opponent_spells", 1),),
        has_battlecry=True,
    ),
    "CORE_DRG_403": CardDef(
        "CORE_DRG_403",
        "喷灯破坏者",
        CardType.MINION,
        3,
        3,
        3,
        rarity="EPIC",
        effects=(Effect("tax_opponent_next_hero_power", 2),),
        has_battlecry=True,
    ),
    "CORE_EDR_004_2026": CardDef(
        "CORE_EDR_004_2026",
        "迅猛龙先锋",
        CardType.MINION,
        3,
        4,
        2,
        races=("BEAST",),
        rarity="EPIC",
        effects=(
            Effect(
                "discover_beast_with_dark_gift_kindred",
                card_ids=DARK_GIFT_BEAST_POOL,
            ),
        ),
        has_battlecry=True,
    ),
    "CORE_REV_023": CardDef(
        "CORE_REV_023",
        "拆迁修理工",
        CardType.MINION,
        3,
        3,
        3,
        tradeable=True,
        rarity="EPIC",
        target_mode=TargetMode.ENEMY_LOCATION,
        target_optional_if_unavailable=True,
        effects=(Effect("destroy_location"),),
        has_battlecry=True,
    ),
    "CORE_SW_066": CardDef(
        "CORE_SW_066",
        "王室图书管理员",
        CardType.MINION,
        4,
        4,
        4,
        tradeable=True,
        rarity="COMMON",
        target_mode=TargetMode.ANY_MINION,
        effects=(Effect("silence"),),
        has_battlecry=True,
    ),
    "TTN_851": CardDef(
        "TTN_851",
        "抗性光环",
        CardType.SPELL,
        2,
        rarity="COMMON",
        effects=(Effect("tax_opponent_spells", 2),),
    ),
    "CORE_KAR_077": CardDef(
        "CORE_KAR_077",
        "银月城传送门",
        CardType.SPELL,
        3,
        rarity="COMMON",
        target_mode=TargetMode.ANY_MINION,
        effects=(Effect("buff", attack=2, health=2), Effect("summon_random_cost", 1, attack=2)),
    ),
    "CORE_DMF_511": CardDef(
        "CORE_DMF_511",
        "狐人老千",
        CardType.MINION,
        2,
        3,
        2,
        rarity="COMMON",
        effects=(Effect("grant_next_combo_discount_this_turn", 2),),
        has_battlecry=True,
    ),
    "CORE_EX1_145": CardDef(
        "CORE_EX1_145",
        "伺机待发",
        CardType.SPELL,
        0,
        rarity="EPIC",
        effects=(Effect("grant_next_spell_discount_this_turn", 2),),
    ),
    "CORE_GIL_836": CardDef(
        "CORE_GIL_836",
        "炽焰祈咒",
        CardType.SPELL,
        1,
        rarity="RARE",
        effects=(Effect("discover_from_pool_cost_discount", 1, card_ids=BATTLECRY_POOL),),
    ),
    "CORE_CS2_053": CardDef(
        "CORE_CS2_053",
        "视界术",
        CardType.SPELL,
        3,
        rarity="EPIC",
        effects=(Effect("draw_with_cost_discount", 3),),
    ),
    "CORE_AV_107": CardDef(
        "CORE_AV_107",
        "冰川急冻",
        CardType.SPELL,
        6,
        rarity="RARE",
        spell_school="FROST",
        effects=(Effect("discover_from_pool_summon_frozen", card_ids=EIGHT_COST_POOL),),
    ),
    "CORE_WON_096": CardDef(
        "CORE_WON_096",
        "黑市摊贩",
        CardType.MINION,
        2,
        2,
        3,
        races=("UNDEAD",),
        rarity="COMMON",
        effects=(Effect("discover_from_pool", card_ids=ONE_COST_POOL),),
        has_battlecry=True,
    ),
    "CORE_REV_990": CardDef(
        "CORE_REV_990",
        "赤红深渊",
        CardType.LOCATION,
        1,
        health=3,
        durability=3,
        rarity="RARE",
        target_mode=TargetMode.ANY_MINION,
        effects=(Effect("damage", 1), Effect("buff", attack=2)),
    ),
    "CORE_WON_337": CardDef(
        "CORE_WON_337",
        "铁炉堡传送门",
        CardType.SPELL,
        4,
        rarity="COMMON",
        effects=(
            Effect("armor", 4, target="owner_hero"),
            Effect("summon_random_cost", 1, attack=4),
        ),
    ),
}

_SOURCE_TEXTS = {
    "CORE_ETC_523": "嘲讽。在本回合中，如果你的英雄受到治疗，本牌改为消耗生命值而非法力值。",
    "CORE_BT_416": "战吼：你的下一张恶魔牌的法力值消耗减少（2）点。",
    "CORE_CATA_001": "你的英雄免疫。战吼：在本回合中，你的下一张恶魔牌的法力值消耗为（0）。",
    "CORE_YOP_001": "发现一张流放牌。你的下一张流放牌法力值消耗减少（1）点。",
    "CORE_OG_044": "你的抉择牌和英雄技能可以同时拥有两种效果。",
    "CORE_ONY_018": "抉择：为你的英雄恢复8点生命值；或者造成4点伤害。",
    "Core_LOE_115": "抉择： 发现一张随从牌；或者发现一张法术牌。",
    "CORE_REV_308": "战吼：随机召唤一个法力值消耗为（2）的随从。",
    "CORE_SCH_713": "战吼：下个回合你的对手法术的法力值消耗增加（1）点。",
    "CORE_DRG_403": "战吼：你对手的下一个英雄技能的法力值消耗增加（2）点。",
    "CORE_EDR_004_2026": "回溯。战吼：发现一张具有黑暗之赐的野兽牌。延系：其法力值消耗减少（1）点。",
    "CORE_REV_023": "可交易 战吼：摧毁一个敌方地标。",
    "CORE_SW_066": "可交易 战吼：沉默一个 随从。",
    "TTN_851": "你对手法术的法力值消耗增加（1）点。持续2个敌方回合。",
    "CORE_KAR_077": "使一个随从获得+2/+2。随机召唤一个法力值消耗为（2）的随从。",
    "CORE_DMF_511": "战吼： 在本回合中，你的下一张连击牌法力值消耗减少（2）点。",
    "CORE_EX1_145": "在本回合中，你所施放的下一个法术的法力值消耗减少（2）点。",
    "CORE_GIL_836": "发现一张战吼随从牌，其法力值消耗减少（1）点。",
    "CORE_CS2_053": "抽一张牌，该牌的法力值消耗减少（3）点。",
    "CORE_AV_107": "发现一张法力值消耗为（8）的随从牌。召唤并冻结该随从。",
    "CORE_WON_096": "战吼：发现一张 法力值消耗为（1）的卡牌。",
    "CORE_REV_990": "对一个随从造成1点伤害，并使其获得+2攻击力。",
    "CORE_WON_337": "获得4点护甲值。随机召唤一个法力值消耗为（4）的 随从。",
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
    "CS2_182": "冰风雪人",
    "CS2_200": "石拳食人魔",
    "CS2_029": "火球术",
    "CS2_023": "奥术智慧",
    "EX1_277": "奥术飞弹",
    "CORE_BT_491": "幽灵视觉",
    "CORE_BT_801": "眼棱",
    "CORE_EX1_383": "提里奥·弗丁",
}


def _player(state: Mapping[str, Any], role_zh: str) -> Mapping[str, Any]:
    return next(item for item in state["players"] if item["role_zh"] == role_zh)


def build_review_scenario(card_id: str, card_registry: Mapping[str, CardDef]) -> Dict[str, Any]:
    if card_id not in CARDS:
        raise ValueError("unknown special-zone card: {}".format(card_id))
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
    source_id = 210_000
    target = TargetRef.minion(actor, 210_001)
    actions: list[Action]

    if card_id == "CORE_ETC_523":
        own.hero_health = 25
        own.healed_this_turn = True
        own.hand = [HandCard(source_id, card_id)]
        actions = [Action(ActionType.PLAY, source_id)]
    elif card_id == "CORE_OG_044":
        own.hand = [HandCard(source_id, card_id)]
        actions = [Action(ActionType.PLAY, source_id)]
    elif card_id == "CORE_ONY_018":
        own.hero_health = 20
        own.hand = [HandCard(source_id, card_id)]
        actions = [Action(ActionType.PLAY, source_id, choice=0)]
    elif card_id == "Core_LOE_115":
        own.hand = [HandCard(source_id, card_id)]
        actions = [
            Action(ActionType.PLAY, source_id, choice=0),
            Action(ActionType.DISCOVER, choice=0),
        ]
    elif card_id == "CORE_REV_023":
        opposing.locations = [Location(210_002, "CORE_REV_990", 2)]
        own.hand = [HandCard(source_id, card_id)]
        actions = [Action(ActionType.PLAY, source_id, TargetRef(enemy, "location", 210_002))]
    elif card_id == "CORE_SW_066":
        own.board = [Minion(210_001, "CS2_120", 5, 6, 6, taunt=True, summoned_turn=0)]
        own.hand = [HandCard(source_id, card_id)]
        actions = [Action(ActionType.PLAY, source_id, target)]
    elif card_id == "CORE_KAR_077":
        own.board = [Minion(210_001, "CS2_120", 2, 3, 3, summoned_turn=0)]
        own.hand = [HandCard(source_id, card_id)]
        actions = [Action(ActionType.PLAY, source_id, target)]
    elif card_id == "CORE_CS2_053":
        own.deck = ["CS2_200"]
        own.hand = [HandCard(source_id, card_id)]
        actions = [Action(ActionType.PLAY, source_id)]
    elif card_id == "CORE_REV_990":
        own.board = [Minion(210_001, "CS2_120", 2, 3, 3, summoned_turn=0)]
        own.locations = [Location(source_id, card_id, 3)]
        actions = [Action(ActionType.LOCATION, source_id, target)]
    else:
        own.hand = [HandCard(source_id, card_id)]
        actions = [Action(ActionType.PLAY, source_id)]
        if card_id in {
            "CORE_YOP_001",
            "CORE_EDR_004_2026",
            "CORE_GIL_836",
            "CORE_AV_107",
            "CORE_WON_096",
        }:
            if card_id == "CORE_EDR_004_2026":
                own.minion_types_played_previous_turn = ["BEAST"]
            actions.append(Action(ActionType.DISCOVER, choice=0))

    before = review_state_from_observation(game.observation(actor))
    engine_actions = []
    for action in actions:
        game.apply(action)
        engine_actions.append(action.to_dict())
    after = review_state_from_observation(game.observation(actor))
    own_before = _player(before, "我方")
    own_after = _player(after, "我方")
    enemy_before = _player(before, "敌方")
    enemy_after = _player(after, "敌方")
    summary_before: Any = {
        "hero": own_before["hero"],
        "resources": own_before["resources"],
        "hand": own_before["zones"]["hand"],
        "board": own_before["zones"]["board"],
        "locations": own_before["zones"]["locations"],
        "enemy_locations": enemy_before["zones"]["locations"],
    }
    summary_after: Any = {
        "hero": own_after["hero"],
        "resources": own_after["resources"],
        "hand": own_after["zones"]["hand"],
        "board": own_after["zones"]["board"],
        "locations": own_after["zones"]["locations"],
        "enemy_locations": enemy_after["zones"]["locations"],
    }
    special_cases = [
        {
            "kind": "special_tags",
            "summary_zh": "减费、发现、地标或持续回合状态使用独立字段记录。",
            "details": {
                "entity_id": source_id,
                "card_id": card_id,
                "tags_before": {},
                "tags_after": {"special_state_resolved": True},
                "explanation_zh": "人工应核对目标范围、状态消费时点以及跨回合清零边界。",
            },
        }
    ]
    if card_id == "CORE_EDR_004_2026":
        special_cases.append(
            {
                "kind": "special_tags",
                "summary_zh": "回溯、黑暗之赐和延系需要单独核验。",
                "details": {
                    "entity_id": source_id,
                    "card_id": card_id,
                    "tags_before": {"kindred_previous_type": "BEAST"},
                    "tags_after": {
                        "dark_gift_tag": "dark_gift",
                        "rewind_tag": "rewind_eligible",
                    },
                    "explanation_zh": "当前产物记录黑暗之赐与回溯资格，并执行延系减费；回溯重投的交互时点需人工专项验证。",
                },
            }
        )

    return {
        "scenario_id": "{}-special-zone-review-v1".format(card_id.lower().replace("_", "-")),
        "title_zh": "{}：特殊动作与区域核验".format(card.name),
        "purpose_zh": "核对特殊支付、发现、减费、地标及跨回合状态。",
        "before": before,
        "action": {
            "type": "special_zone_fixture",
            "actor_player_id": actor,
            "source_entity_id": actions[0].source_id,
            "card_id": card_id,
            "target": asdict(actions[0].target) if actions[0].target else None,
            "description_zh": "执行卡面所需的最小可复现结算序列。",
            "engine_action": engine_actions,
        },
        "after": after,
        "assertions": [
            {
                "assertion_id": "special-zone-result",
                "subject_zh": "特殊动作结算后的关键状态",
                "before": summary_before,
                "after": summary_after,
                "expected_zh": "卡面状态只在规定时点生效，并保存在可检查字段中",
            }
        ],
        "special_cases": special_cases,
    }
