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
    TargetMode,
    TargetRef,
)
from ..review_format import review_state_from_observation

SOURCE_VERSION = "250339"
GENERATED_BY = "codex-gpt-5.6-core-composite-unique-batch-v1"

PACK_POOL = (
    "CS2_120",
    "CS2_182",
    "CS2_200",
    "CS2_023",
    "EX1_277",
    "CORE_CS2_029",
    "CORE_CS2_024",
    "CORE_EX1_238",
)

TOKEN_CARDS: Dict[str, CardDef] = {
    "EX1_323w": CardDef(
        "EX1_323w",
        "血怒",
        CardType.WEAPON,
        3,
        3,
        durability=8,
        collectible=False,
    ),
    "EX1_tk34": CardDef(
        "EX1_tk34",
        "地狱火",
        CardType.MINION,
        6,
        6,
        6,
        races=("DEMON",),
        collectible=False,
    ),
}

CARDS: Dict[str, CardDef] = {
    "CORE_BT_156": CardDef(
        "CORE_BT_156",
        "被禁锢的邪犬",
        CardType.MINION,
        2,
        3,
        5,
        races=("DEMON",),
        rarity="COMMON",
        rush=True,
        dormant_turns=2,
    ),
    "CORE_EX1_058": CardDef(
        "CORE_EX1_058",
        "日怒保卫者",
        CardType.MINION,
        2,
        2,
        3,
        rarity="RARE",
        effects=(Effect("grant_taunt_adjacent_to_played"),),
        uses_board_position=True,
        has_battlecry=True,
    ),
    "CORE_SCH_605": CardDef(
        "CORE_SCH_605",
        "止水湖蛇颈龙",
        CardType.MINION,
        5,
        4,
        6,
        races=("BEAST",),
        rarity="COMMON",
        cleaves_adjacent=True,
    ),
    "CORE_ULD_178": CardDef(
        "CORE_ULD_178",
        "希亚玛特",
        CardType.MINION,
        7,
        7,
        7,
        races=("ELEMENTAL",),
        rarity="LEGENDARY",
        choose_two_keywords=("rush", "taunt", "divine_shield", "windfury"),
        has_battlecry=True,
    ),
    "CS3_035": CardDef(
        "CS3_035",
        "永恒者诺兹多姆",
        CardType.MINION,
        7,
        8,
        8,
        races=("DRAGON",),
        rarity="LEGENDARY",
        both_decks_turn_time_limit=15,
    ),
    "CORE_WON_145": CardDef(
        "CORE_WON_145",
        "具象炉石",
        CardType.MINION,
        9,
        5,
        5,
        rarity="LEGENDARY",
        effects=(Effect("play_pack_cards", card_ids=PACK_POOL),),
        has_battlecry=True,
    ),
    "CORE_CATA_004": CardDef(
        "CORE_CATA_004",
        "雷加尔·大地之怒",
        CardType.MINION,
        5,
        3,
        5,
        rarity="LEGENDARY",
        on_self_or_adjacent_attack_effects=(Effect("add_to_hand", 1, card_id="CORE_EX1_238"),),
    ),
    "CORE_EX1_323": CardDef(
        "CORE_EX1_323",
        "加拉克苏斯大王",
        CardType.HERO,
        8,
        rarity="LEGENDARY",
        effects=(
            Effect("armor", 5, target="owner_hero"),
            Effect("equip_weapon", card_id="EX1_323w"),
            Effect("set_hero_power_summon", card_id="EX1_tk34"),
        ),
        has_battlecry=True,
    ),
    "CORE_BT_120": CardDef(
        "CORE_BT_120",
        "战槌挑战者",
        CardType.MINION,
        3,
        1,
        10,
        rarity="EPIC",
        target_mode=TargetMode.ENEMY_MINION,
        effects=(Effect("fight_until_death"),),
        has_battlecry=True,
    ),
}

_SOURCE_TEXTS = {
    "CORE_BT_156": "休眠2回合。 突袭",
    "CORE_EX1_058": "战吼：使相邻的随从获得嘲讽。",
    "CORE_SCH_605": "同时对其攻击目标相邻的随从造成伤害。",
    "CORE_ULD_178": "战吼：从突袭，嘲讽，圣盾或风怒中获得两种效果（由你选择）。",
    "CS3_035": "对战开始时：如果双方玩家的套牌中都有这张随从牌，则每个回合只有15秒。",
    "CORE_WON_145": "战吼：打开一包标准卡牌包，使用其中的所有卡牌。",
    "CORE_CATA_004": "在本随从或相邻的随从攻击后，获取一张闪电箭。",
    "CORE_EX1_323": "战吼：装备一把3/8的血怒。",
    "CORE_BT_120": "战吼： 选择一个敌方随从。与其战斗至死！",
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
    **{card_id: card.name for card_id, card in TOKEN_CARDS.items()},
    "CS2_120": "淡水鳄",
    "CS2_182": "冰风雪人",
    "CS2_200": "石拳食人魔",
    "CS2_023": "奥术智慧",
    "EX1_277": "奥术飞弹",
    "CORE_CS2_029": "火球术",
    "CORE_CS2_024": "寒冰箭",
    "CORE_EX1_238": "闪电箭",
}


def _player(state: Mapping[str, Any], role_zh: str) -> Mapping[str, Any]:
    return next(item for item in state["players"] if item["role_zh"] == role_zh)


def build_review_scenario(card_id: str, card_registry: Mapping[str, CardDef]) -> Dict[str, Any]:
    if card_id not in CARDS:
        raise ValueError("unknown composite card: {}".format(card_id))
    card = CARDS[card_id]
    if card_id == "CS3_035":
        deck = [card_id] + ["CS2_120"] * 10
        game = Game(
            seed=79,
            decks=(list(deck), list(deck)),
            card_registry=card_registry,
        )
    else:
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
    own.deck = ["CS2_120"] * 10
    opposing.deck = ["CS2_120"] * 10
    source_id = 250_000
    actions: list[Action] = []

    if card_id == "CORE_BT_156":
        own.hand = [HandCard(source_id, card_id)]
        actions = [Action(ActionType.PLAY, source_id)]
    elif card_id == "CORE_EX1_058":
        own.board = [
            Minion(250_001, "CS2_120", 2, 3, 3, summoned_turn=0),
            Minion(250_002, "CS2_182", 4, 5, 5, summoned_turn=0),
        ]
        own.hand = [HandCard(source_id, card_id)]
        actions = [Action(ActionType.PLAY, source_id, position=1)]
    elif card_id == "CORE_SCH_605":
        own.board = [Minion(source_id, card_id, 4, 6, 6, summoned_turn=0)]
        opposing.board = [
            Minion(250_003, "CS2_120", 1, 5, 5, summoned_turn=0),
            Minion(250_004, "CS2_120", 1, 5, 5, summoned_turn=0),
            Minion(250_005, "CS2_120", 1, 5, 5, summoned_turn=0),
        ]
        actions = [Action(ActionType.ATTACK, source_id, TargetRef.minion(enemy, 250_004))]
    elif card_id == "CORE_ULD_178":
        own.hand = [HandCard(source_id, card_id)]
        actions = [Action(ActionType.PLAY, source_id, choice=2)]
    elif card_id == "CS3_035":
        actions = []
    elif card_id == "CORE_CATA_004":
        own.board = [
            Minion(250_006, "CS2_120", 2, 3, 3, summoned_turn=0),
            Minion(source_id, card_id, 3, 5, 5, summoned_turn=0),
            Minion(250_007, "CS2_182", 4, 5, 5, summoned_turn=0),
        ]
        actions = [Action(ActionType.ATTACK, 250_006, TargetRef.hero(enemy))]
    elif card_id == "CORE_BT_120":
        own.hand = [HandCard(source_id, card_id)]
        opposing.board = [Minion(250_008, "CS2_120", 2, 3, 3, summoned_turn=0)]
        actions = [Action(ActionType.PLAY, source_id, TargetRef.minion(enemy, 250_008))]
    else:
        own.hand = [HandCard(source_id, card_id)]
        actions = [Action(ActionType.PLAY, source_id)]

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

    tags_before: Dict[str, Any] = {}
    tags_after: Dict[str, Any] = {}
    if card_id == "CS3_035":
        tags_before["both_decks_contain_card"] = True
        tags_after["turn_time_limit_seconds"] = game.state.turn_time_limit_seconds
    elif card_id == "CORE_WON_145":
        tags_after["last_pack_card_ids"] = list(own.last_pack_card_ids)
    elif card_id == "CORE_EX1_323":
        tags_after["hero_power_kind"] = own.hero_power_kind
        tags_after["hero_armor"] = own.hero_armor
    elif card_id == "CORE_EX1_058":
        tags_after["played_position"] = 1
    elif card_id == "CORE_ULD_178":
        tags_after["chosen_keywords"] = ["rush", "windfury"]
    elif card_id == "CORE_BT_156":
        tags_after["dormant_turns_remaining"] = own.board[0].dormant_turns_remaining

    return {
        "scenario_id": "{}-composite-review-v1".format(card_id.lower().replace("_", "-")),
        "title_zh": "{}：复合与独特效果核验".format(card.name),
        "purpose_zh": "核对站位、休眠、多选、强制战斗、开包、英雄替换或开局规则。",
        "before": before,
        "action": {
            "type": "composite_fixture",
            "actor_player_id": actor,
            "source_entity_id": actions[0].source_id if actions else None,
            "card_id": card_id,
            "target": asdict(actions[0].target) if actions and actions[0].target else None,
            "description_zh": "执行能暴露该牌独特状态的最小结算序列。",
            "engine_action": engine_actions,
        },
        "after": after,
        "assertions": [
            {
                "assertion_id": "composite-result",
                "subject_zh": "复合效果结算后的关键状态",
                "before": {
                    "hero": own_before["hero"],
                    "hand": own_before["zones"]["hand"],
                    "board": own_before["zones"]["board"],
                    "enemy_board": enemy_before["zones"]["board"],
                },
                "after": {
                    "hero": own_after["hero"],
                    "hand": own_after["zones"]["hand"],
                    "board": own_after["zones"]["board"],
                    "enemy_board": enemy_after["zones"]["board"],
                },
                "expected_zh": "各子效果按固定时点结算，特殊状态保留在结构化字段中",
            }
        ],
        "special_cases": [
            {
                "kind": "special_tags",
                "summary_zh": "该牌的独特状态单独记录，供人工核对。",
                "details": {
                    "entity_id": source_id,
                    "card_id": card_id,
                    "tags_before": tags_before,
                    "tags_after": tags_after,
                    "explanation_zh": "人工应检查状态时点、站位边界及随机结果是否与卡面一致。",
                },
            }
        ],
    }
