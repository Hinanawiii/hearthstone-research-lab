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
GENERATED_BY = "codex-gpt-5.6-core-discovery-generation-batch-v1"

SPELL_POOL = ("CORE_CS2_029", "CORE_CS2_024", "CORE_EX1_238")
DEMON_POOL = ("CORE_LOOT_013", "CORE_SW_068", "CORE_EX1_310")
MAGE_SPELL_POOL = ("CORE_CS2_029", "CORE_CS2_024", "CORE_CS2_032")
LEGENDARY_MINION_POOL = ("CORE_EX1_110", "CORE_CATA_002", "CORE_EDR_003")
DRAGON_POOL = ("CORE_EX1_043", "CORE_AT_123", "CORE_YOP_034")
MECHANICAL_POOL = ("CORE_GVG_085", "CORE_GVG_103", "CORE_DRG_256")
TAUNT_POOL = ("CORE_EX1_250", "CORE_UNG_928", "CORE_GIL_623")
HOLY_SPELL_POOL = ("CORE_TSC_076", "CORE_TRL_307", "CORE_CS1_112")
OTHER_CLASS_POOL = ("CORE_CS2_029", "CORE_EX1_238", "CORE_CS2_093")
HIGH_COST_OTHER_CLASS_SPELL_POOL = (
    "CORE_EX1_312",
    "CORE_OG_211",
    "CORE_CS2_032",
)
SHAMAN_SPELL_POOL = ("CORE_EX1_238", "CORE_EX1_259", "CORE_LOOT_373")

CARDS: Dict[str, CardDef] = {
    "CORE_CATA_009": CardDef(
        "CORE_CATA_009",
        "死亡脚步",
        CardType.SPELL,
        2,
        target_mode=TargetMode.ANY_CHARACTER,
        effects=(Effect("freeze"), Effect("discover_from_pool", card_ids=SPELL_POOL)),
        rarity="COMMON",
        spell_school="FROST",
    ),
    "CORE_BT_321": CardDef(
        "CORE_BT_321",
        "虚无行者",
        CardType.MINION,
        2,
        2,
        2,
        rarity="COMMON",
        effects=(Effect("discover_from_pool", card_ids=DEMON_POOL),),
    ),
    "CORE_UNG_912": CardDef(
        "CORE_UNG_912",
        "宝石鹦鹉",
        CardType.MINION,
        1,
        1,
        2,
        races=("BEAST",),
        rarity="COMMON",
        effects=(Effect("add_random_race_to_hand", 1, race="BEAST"),),
    ),
    "CORE_DS1_184": CardDef(
        "CORE_DS1_184",
        "追踪术",
        CardType.SPELL,
        1,
        rarity="RARE",
        effects=(Effect("discover_from_deck"),),
    ),
    "CORE_EDR_001": CardDef(
        "CORE_EDR_001",
        "呓语魔橱",
        CardType.MINION,
        3,
        2,
        4,
        rarity="RARE",
        effects=(Effect("add_random_from_pool", 2, card_ids=MAGE_SPELL_POOL),),
    ),
    "CORE_BAR_541": CardDef(
        "CORE_BAR_541",
        "符文宝珠",
        CardType.SPELL,
        2,
        target_mode=TargetMode.ANY_CHARACTER,
        rarity="COMMON",
        spell_school="ARCANE",
        effects=(
            Effect("damage", 2),
            Effect("discover_from_pool", card_ids=SPELL_POOL),
        ),
    ),
    "CORE_EX1_189": CardDef(
        "CORE_EX1_189",
        "光明之翼",
        CardType.MINION,
        2,
        3,
        2,
        races=("DRAGON",),
        rarity="LEGENDARY",
        effects=(
            Effect("add_random_from_pool", 1, card_ids=LEGENDARY_MINION_POOL),
        ),
    ),
    "CORE_KAR_062": CardDef(
        "CORE_KAR_062",
        "虚空幽龙史学家",
        CardType.MINION,
        2,
        2,
        3,
        rarity="COMMON",
        effects=(
            Effect(
                "discover_from_pool_if_hand_race",
                race="DRAGON",
                card_ids=DRAGON_POOL,
            ),
        ),
    ),
    "CORE_LOE_039": CardDef(
        "CORE_LOE_039",
        "A3型机械金刚",
        CardType.MINION,
        3,
        3,
        4,
        races=("MECHANICAL", "BEAST"),
        rarity="COMMON",
        effects=(
            Effect(
                "discover_from_pool_if_other_friendly_race",
                race="MECHANICAL",
                card_ids=MECHANICAL_POOL,
            ),
        ),
    ),
    "Core_UNG_072": CardDef(
        "Core_UNG_072",
        "石丘防御者",
        CardType.MINION,
        3,
        1,
        5,
        taunt=True,
        rarity="RARE",
        effects=(Effect("discover_from_pool", card_ids=TAUNT_POOL),),
    ),
    "CORE_ONY_022": CardDef(
        "CORE_ONY_022",
        "武装教士",
        CardType.MINION,
        2,
        1,
        3,
        races=("DRAENEI",),
        rarity="RARE",
        effects=(Effect("discover_from_pool", card_ids=HOLY_SPELL_POOL),),
    ),
    "CORE_KAR_057": CardDef(
        "CORE_KAR_057",
        "象牙骑士",
        CardType.MINION,
        4,
        4,
        4,
        rarity="RARE",
        effects=(
            Effect("discover_from_pool_heal_by_cost", card_ids=SPELL_POOL),
        ),
    ),
    "CORE_KAR_069": CardDef(
        "CORE_KAR_069",
        "吹嘘海盗",
        CardType.MINION,
        1,
        1,
        2,
        races=("PIRATE",),
        rarity="COMMON",
        effects=(Effect("add_random_from_pool", 1, card_ids=OTHER_CLASS_POOL),),
    ),
    "CORE_TID_931": CardDef(
        "CORE_TID_931",
        "头等大奖",
        CardType.SPELL,
        2,
        rarity="COMMON",
        effects=(
            Effect(
                "add_random_from_pool",
                2,
                card_ids=HIGH_COST_OTHER_CLASS_SPELL_POOL,
            ),
        ),
    ),
    "CORE_GIL_531": CardDef(
        "CORE_GIL_531",
        "女巫的学徒",
        CardType.MINION,
        0,
        0,
        1,
        taunt=True,
        races=("BEAST",),
        rarity="COMMON",
        effects=(Effect("add_random_from_pool", 1, card_ids=SHAMAN_SPELL_POOL),),
    ),
    "CORE_DRG_024": CardDef(
        "CORE_DRG_024",
        "空中悍匪",
        CardType.MINION,
        1,
        1,
        2,
        races=("PIRATE",),
        rarity="COMMON",
        effects=(Effect("add_random_race_to_hand", 1, race="PIRATE"),),
    ),
    "CORE_WON_350": CardDef(
        "CORE_WON_350",
        "盛气凌人",
        CardType.SPELL,
        1,
        rarity="COMMON",
        effects=(
            Effect(
                "discover_from_pool_buff",
                attack=1,
                health=2,
                card_ids=TAUNT_POOL,
            ),
        ),
    ),
}

_SOURCE_TEXTS = {
    "CORE_CATA_009": "冻结一个角色。发现一张法术牌。",
    "CORE_BT_321": "战吼： 发现一张恶魔牌。",
    "CORE_UNG_912": "战吼：随机将一张野兽牌置入你的手牌。",
    "CORE_DS1_184": "从你的牌库中发现一张牌。",
    "CORE_EDR_001": "战吼：随机 将2张法师法术牌置入你的手牌。",
    "CORE_BAR_541": "造成2点伤害。发现一张法术牌。",
    "CORE_EX1_189": "战吼：随机将一张传说随从牌置入你的 手牌。",
    "CORE_KAR_062": "战吼：如果你的手牌中有龙牌，便发现一张龙牌。",
    "CORE_LOE_039": "战吼：如果你控制着其他机械，发现一张机械牌。",
    "Core_UNG_072": "嘲讽，战吼： 发现一张具有嘲讽的随从牌。",
    "CORE_ONY_022": "战吼：发现一张神圣法术牌。",
    "CORE_KAR_057": "战吼：发现一张法术牌。为你的英雄恢复等同于其法力值消耗的生命值。",
    "CORE_KAR_069": "战吼：随机将一张另一职业的卡牌置入你的手牌。",
    "CORE_TID_931": "将两张其他职业的法力值消耗大于或等于（5）点的法术牌置入你的手牌。",
    "CORE_GIL_531": "嘲讽，战吼：随机将一张萨满祭司法术牌置入你的手牌。",
    "CORE_DRG_024": "战吼：随机将一张海盗牌置入你的手牌。",
    "CORE_WON_350": "发现一张嘲讽随从牌。使其获得+1/+2。",
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
    "CORE_CS2_029": "火球术",
    "CORE_CS2_024": "寒冰箭",
    "CORE_EX1_238": "闪电箭",
    "CORE_EX1_043": "暮光幼龙",
    "CORE_GVG_085": "吵吵机器人",
    "CORE_NEW1_022": "恐怖海盗",
}

_RANDOM_GENERATION_IDS = {
    "CORE_UNG_912",
    "CORE_EDR_001",
    "CORE_EX1_189",
    "CORE_KAR_069",
    "CORE_TID_931",
    "CORE_GIL_531",
    "CORE_DRG_024",
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


def build_review_scenario(
    card_id: str, card_registry: Mapping[str, CardDef]
) -> Dict[str, Any]:
    if card_id not in CARDS:
        raise ValueError("unknown discovery generation card: {}".format(card_id))
    card = CARDS[card_id]
    game = Game(seed=sum(ord(char) for char in card_id), card_registry=card_registry)
    actor = game.state.active_player
    enemy = 1 - actor
    own = game.state.players[actor]
    opposing = game.state.players[enemy]
    own.mana = own.max_mana = 10
    opposing.mana = opposing.max_mana = 10
    own.hand = [HandCard(150_000, card_id)]
    opposing.hand = []
    own.board = []
    opposing.board = []
    own.deck = ["CS2_120"]
    opposing.deck = ["CS2_120"]
    target = None

    if card_id == "CORE_DS1_184":
        own.deck = ["CS2_029", "CS2_023", "EX1_277"]
    elif card_id == "CORE_KAR_062":
        own.hand.append(HandCard(150_001, "CORE_EX1_043"))
    elif card_id == "CORE_LOE_039":
        own.board = [
            Minion(
                150_002,
                "CORE_GVG_085",
                1,
                2,
                2,
                races=("MECHANICAL",),
                summoned_turn=0,
            )
        ]
    elif card_id == "CORE_KAR_057":
        own.hero_health = 20
    elif card_id in {"CORE_CATA_009", "CORE_BAR_541"}:
        target = TargetRef.hero(enemy)

    action = Action(ActionType.PLAY, 150_000, target)
    before = review_state_from_observation(game.observation(actor))
    engine_actions = [action.to_dict()]
    game.apply(action)
    offered = list(game.state.pending_discover_options)
    chosen_card_id = ""
    if offered:
        chosen_card_id = offered[0]
        choice_action = Action(ActionType.DISCOVER, choice=0)
        game.apply(choice_action)
        engine_actions.append(choice_action.to_dict())
    after = review_state_from_observation(game.observation(actor))
    own_before = _player(before, "我方")
    own_after = _player(after, "我方")
    enemy_before = _player(before, "敌方")
    enemy_after = _player(after, "敌方")

    hand_before_ids = [item["card_id"] for item in own_before["zones"]["hand"]["cards"]]
    hand_after = own_after["zones"]["hand"]["cards"]
    hand_after_ids = [item["card_id"] for item in hand_after]
    if card_id in _RANDOM_GENERATION_IDS:
        added_count = 2 if card_id in {"CORE_EDR_001", "CORE_TID_931"} else 1
        assertions = [
            _assertion(
                "generated-card-count",
                "随机生成的手牌数量",
                len(hand_before_ids) - 1,
                len(hand_after_ids),
                "打出母卡后，按卡面向手牌加入{}张候选池卡牌".format(added_count),
            )
        ]
        special_cases = [
            {
                "kind": "special_tags",
                "summary_zh": "随机生成只从当前已注册且满足过滤条件的牌池取样。",
                "details": {
                    "entity_id": 150_000,
                    "card_id": card_id,
                    "tags_before": {"registered_pool_only": True},
                    "tags_after": {"generated_card_ids": hand_after_ids},
                    "explanation_zh": "固定随机种子可复现结果；扩充注册牌池后候选集合会随之扩大。",
                },
            }
        ]
    else:
        chosen_hand_card = next(
            (item for item in hand_after if item["card_id"] == chosen_card_id),
            None,
        )
        assertions = [
            _assertion(
                "discover-choice-added",
                "发现选择结果",
                offered,
                chosen_card_id,
                "展示至多三个候选，并把人工选择的第一项加入手牌",
            )
        ]
        if card_id == "CORE_CATA_009":
            assertions.append(
                _assertion(
                    "freeze-before-discover",
                    "敌方英雄标签",
                    enemy_before["hero"]["tags"],
                    enemy_after["hero"]["tags"],
                    "先冻结目标，再进入发现选择",
                )
            )
        elif card_id == "CORE_BAR_541":
            assertions.append(
                _assertion(
                    "orb-damage",
                    "敌方英雄生命值",
                    enemy_before["hero"]["health"],
                    enemy_after["hero"]["health"],
                    "造成2点伤害后进入发现选择",
                )
            )
        elif card_id == "CORE_DS1_184":
            assertions.append(
                _assertion(
                    "tracking-removes-from-deck",
                    "我方牌库数量",
                    own_before["zones"]["deck"]["count"],
                    own_after["zones"]["deck"]["count"],
                    "选中的牌从牌库移入手牌，其余候选仍留在牌库",
                )
            )
        elif card_id == "CORE_KAR_057":
            assertions.append(
                _assertion(
                    "ivory-heal",
                    "我方英雄生命值",
                    own_before["hero"]["health"],
                    own_after["hero"]["health"],
                    "按最终选择牌的印刷费用恢复生命值",
                )
            )
        elif card_id == "CORE_WON_350" and chosen_hand_card is not None:
            assertions.append(
                _assertion(
                    "dominance-hand-buff",
                    "被发现手牌的属性修正",
                    [0, 0],
                    [
                        chosen_hand_card["attack_bonus"],
                        chosen_hand_card["health_bonus"],
                    ],
                    "选择后在该手牌实例上记录+1/+2",
                )
            )
        special_cases = [
            {
                "kind": "special_tags",
                "summary_zh": "发现候选、选择和选择后处理分成两个确定性动作记录。",
                "details": {
                    "entity_id": 150_000,
                    "card_id": card_id,
                    "tags_before": {"offered_card_ids": offered},
                    "tags_after": {"chosen_card_id": chosen_card_id},
                    "explanation_zh": "对手只能看到候选数量；候选内容仅对发现方可见。",
                },
            }
        ]

    if card_id == "CORE_DS1_184":
        special_cases = [
            {
                "kind": "deck_change",
                "summary_zh": "追踪术只从牌库移走被选中的一张牌。",
                "details": {
                    "player_id": actor,
                    "before_count": own_before["zones"]["deck"]["count"],
                    "after_count": own_after["zones"]["deck"]["count"],
                    "drawn_count": 1,
                    "added_count": 0,
                    "shuffled_count": 0,
                    "order_changed": False,
                    "known_top_before": [],
                    "known_top_after": [],
                },
            }
        ]

    return {
        "scenario_id": "{}-discovery-generation-review-v1".format(
            card_id.lower().replace("_", "-")
        ),
        "title_zh": "{}：候选池与手牌结果核验".format(card.name),
        "purpose_zh": "核对候选池过滤、隐藏选项、随机生成和选择后的附加结算。",
        "before": before,
        "action": {
            "type": "play_then_choose_if_needed",
            "actor_player_id": actor,
            "source_entity_id": 150_000,
            "card_id": card_id,
            "target": asdict(target) if target else None,
            "description_zh": "我方使用《{}》，若进入发现则选择第一项。".format(card.name),
            "engine_action": engine_actions,
        },
        "after": after,
        "assertions": assertions,
        "special_cases": special_cases,
    }
