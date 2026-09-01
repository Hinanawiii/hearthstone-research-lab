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
GENERATED_BY = "codex-gpt-5.6-core-rune-location-batch-v1"

BLOOD_POOL = ("CORE_RLK_506", "CORE_RLK_712", "CORE_RLK_066")
FROST_POOL = ("RLK_025", "RLK_223", "RLK_709", "CORE_RLK_505")
UNHOLY_POOL = (
    "CORE_WW_374",
    "CORE_RLK_116",
    "RLK_048",
    "RLK_060",
    "CORE_RLK_118",
    "CORE_EDR_003",
)
CORPSE_SPENDER_POOL = (
    "CORE_RLK_066",
    "CORE_RLK_712",
    "RLK_707",
    "RLK_060",
    "CORE_RLK_118",
    "CORE_RLK_506",
    "CORE_RLK_505",
    "CORE_WW_374",
)

CARDS: Dict[str, CardDef] = {
    "CORE_RLK_066": CardDef(
        "CORE_RLK_066",
        "鲜血魔术师",
        CardType.MINION,
        2,
        2,
        3,
        rarity="RARE",
        runes=("BLOOD",),
        spends_corpses=True,
        effects=(
            Effect("discover_from_pool", card_ids=BLOOD_POOL, corpse_cost=1),
        ),
    ),
    "CORE_RLK_116": CardDef(
        "CORE_RLK_116",
        "死灵殡葬师",
        CardType.MINION,
        2,
        2,
        3,
        rarity="COMMON",
        runes=("UNHOLY",),
        effects=(Effect("discover_from_pool_if_undead_died", card_ids=UNHOLY_POOL),),
    ),
    "CORE_EDR_003": CardDef(
        "CORE_EDR_003",
        "法瑞克",
        CardType.MINION,
        3,
        2,
        4,
        races=("UNDEAD",),
        rarity="LEGENDARY",
        runes=("UNHOLY", "UNHOLY"),
        corpse_gain_multiplier=2,
        effects=(Effect("draw_spends_corpses", 1, card_ids=CORPSE_SPENDER_POOL),),
    ),
    "RLK_025": CardDef(
        "RLK_025",
        "冰霜打击",
        CardType.SPELL,
        2,
        target_mode=TargetMode.ANY_MINION,
        rarity="COMMON",
        runes=("FROST",),
        spell_school="FROST",
        effects=(
            Effect("damage", 3),
            Effect("discover_from_pool_if_selected_dead", card_ids=FROST_POOL),
        ),
    ),
    "CORE_EX1_312": CardDef(
        "CORE_EX1_312",
        "扭曲虚空",
        CardType.SPELL,
        8,
        rarity="EPIC",
        effects=(Effect("destroy_all_minions_and_locations"),),
    ),
}

_SOURCE_TEXTS = {
    "CORE_RLK_066": "战吼：消耗一份残骸，发现一张鲜血符文牌。",
    "CORE_RLK_116": "战吼：如果在你的上回合之后有友方亡灵死亡，发现一张邪恶符文牌。",
    "CORE_EDR_003": "你获得的残骸量为正常的两倍。战吼：抽一张消耗残骸的牌。",
    "RLK_025": "对一个随从造成3点伤害。如果该随从死亡，发现一张冰霜符文牌。",
    "CORE_EX1_312": "消灭所有随从和地标。",
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
    "CORE_RLK_506": "白骨卫士指挥官",
    "CORE_RLK_712": "活力分流",
    "RLK_223": "萨萨里安",
    "RLK_709": "冷酷严冬",
    "CORE_RLK_505": "髓骨使御者",
    "CORE_WW_374": "凉心农场",
    "RLK_048": "反魔法护罩",
    "RLK_060": "亡者大军",
    "CORE_RLK_118": "坟墓守卫",
    "RLK_707": "墓地之力",
    "CORE_REV_990": "赤红深渊",
    "CS2_120": "淡水鳄",
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
        raise ValueError("unknown rune/location batch card: {}".format(card_id))
    card = CARDS[card_id]
    game = Game(seed=sum(ord(char) for char in card_id), card_registry=card_registry)
    actor = game.state.active_player
    enemy = 1 - actor
    own = game.state.players[actor]
    opposing = game.state.players[enemy]
    own.mana = own.max_mana = 10
    opposing.mana = opposing.max_mana = 10
    own.hand = [HandCard(121_000, card_id)]
    opposing.hand = []
    own.board = []
    opposing.board = []
    own.deck = ["CS2_120"]
    opposing.deck = ["CS2_120"]
    own.corpses = 0
    offered: list[str] = []
    chosen_card_id = ""

    if card_id == "CORE_RLK_066":
        own.corpses = 1
        action = Action(ActionType.PLAY, 121_000)
        description = "我方有1份残骸，使用《鲜血魔术师》并选择第一张发现选项。"
    elif card_id == "CORE_RLK_116":
        own.friendly_undead_died_since_last_turn = True
        action = Action(ActionType.PLAY, 121_000)
        description = "已有友方亡灵在上回合后死亡，我方使用《死灵殡葬师》并选择第一项。"
    elif card_id == "RLK_025":
        opposing.board = [Minion(121_010, "CS2_120", 2, 3, 3, summoned_turn=0)]
        action = Action(ActionType.PLAY, 121_000, TargetRef.minion(enemy, 121_010))
        description = "我方用《冰霜打击》消灭3点生命的敌方淡水鳄，并选择第一项。"
    elif card_id == "CORE_EDR_003":
        own.deck = ["CS2_120", "CORE_RLK_712"]
        action = Action(ActionType.PLAY, 121_000)
        description = "我方使用《法瑞克》，牌库中只有一张会消耗残骸的牌。"
    else:
        own.board = [Minion(121_020, "CS2_120", 2, 3, 3, summoned_turn=0)]
        opposing.board = [Minion(121_021, "CS2_120", 2, 3, 3, summoned_turn=0)]
        own.locations = [Location(121_022, "CORE_REV_990", 3)]
        opposing.locations = [Location(121_023, "CORE_REV_990", 2)]
        action = Action(ActionType.PLAY, 121_000)
        description = "双方各有一个随从和一个地标时，我方使用《扭曲虚空》。"

    before = review_state_from_observation(game.observation(actor))
    game.apply(action)
    engine_actions = [action.to_dict()]
    if game.state.pending_discover_player is not None:
        offered = list(game.state.pending_discover_options)
        chosen_card_id = offered[0]
        discover_action = Action(ActionType.DISCOVER, choice=0)
        game.apply(discover_action)
        engine_actions.append(discover_action.to_dict())
    after = review_state_from_observation(game.observation(actor))
    own_before = _player(before, "我方")
    own_after = _player(after, "我方")
    opposing_before = _player(before, "敌方")
    opposing_after = _player(after, "敌方")
    assertions = []

    if card_id == "CORE_RLK_066":
        assertions.extend(
            [
                _assertion(
                    "spend-one-corpse",
                    "我方残骸",
                    own_before["resources"]["corpses"],
                    own_after["resources"]["corpses"],
                    "支付1份残骸后才建立发现选项",
                ),
                _discover_assertion(own_before, own_after, chosen_card_id, "鲜血"),
            ]
        )
    elif card_id == "CORE_RLK_116":
        assertions.append(_discover_assertion(own_before, own_after, chosen_card_id, "邪恶"))
    elif card_id == "RLK_025":
        assertions.extend(
            [
                _assertion(
                    "target-died",
                    "敌方淡水鳄数量",
                    len(opposing_before["zones"]["board"]),
                    len(opposing_after["zones"]["board"]),
                    "3点伤害使目标死亡后才建立发现选项",
                ),
                _discover_assertion(own_before, own_after, chosen_card_id, "冰霜"),
            ]
        )
    elif card_id == "CORE_EDR_003":
        hand_ids = [item["card_id"] for item in own_after["zones"]["hand"]["cards"]]
        assertions.append(
            _assertion(
                "draw-corpse-spender",
                "我方手牌",
                [],
                hand_ids,
                "从牌库抽取唯一标记为消耗残骸的《活力分流》",
            )
        )
    else:
        assertions.extend(
            [
                _assertion(
                    "destroy-all-minions",
                    "双方场上随从数量",
                    [
                        len(own_before["zones"]["board"]),
                        len(opposing_before["zones"]["board"]),
                    ],
                    [
                        len(own_after["zones"]["board"]),
                        len(opposing_after["zones"]["board"]),
                    ],
                    "双方所有随从被消灭并进入死亡清理",
                ),
                _assertion(
                    "destroy-all-locations",
                    "双方地标数量",
                    [
                        len(own_before["zones"]["locations"]),
                        len(opposing_before["zones"]["locations"]),
                    ],
                    [
                        len(own_after["zones"]["locations"]),
                        len(opposing_after["zones"]["locations"]),
                    ],
                    "双方所有地标直接离场",
                ),
            ]
        )

    return {
        "scenario_id": "{}-rune-location-review-v1".format(card_id.lower().replace("_", "-")),
        "title_zh": "{}：条件选择与区域核验".format(card.name),
        "purpose_zh": "核对发现决策、条件历史、残骸倍率、筛选抽牌和地标清除。",
        "before": before,
        "action": {
            "type": "play_card_and_resolve_discover",
            "actor_player_id": actor,
            "source_entity_id": action.source_id,
            "card_id": card_id,
            "target": asdict(action.target) if action.target else None,
            "description_zh": description,
            "engine_action": {"sequence": engine_actions},
        },
        "after": after,
        "assertions": assertions,
        "special_cases": [
            {
                "kind": "special_tags",
                "summary_zh": "发现候选、条件历史和区域数量单独记录。",
                "details": {
                    "entity_id": action.source_id,
                    "card_id": card_id,
                    "tags_before": {
                        "undead_died_since_last_turn": own_before["history"]["friendly_undead_died_since_last_turn"],
                        "locations": [
                            len(own_before["zones"]["locations"]),
                            len(opposing_before["zones"]["locations"]),
                        ],
                    },
                    "tags_after": {
                        "offered_card_ids": offered,
                        "chosen_card_id": chosen_card_id,
                        "locations": [
                            len(own_after["zones"]["locations"]),
                            len(opposing_after["zones"]["locations"]),
                        ],
                    },
                    "explanation_zh": "发现是独立合法动作，专用AI必须在三个候选中决策；条件不满足时不会创建该动作。",
                },
            }
        ],
    }


def _discover_assertion(
    own_before: Mapping[str, Any],
    own_after: Mapping[str, Any],
    chosen_card_id: str,
    rune_zh: str,
) -> Dict[str, Any]:
    return _assertion(
        "discover-choice",
        "我方手牌数量",
        own_before["zones"]["hand"]["count"],
        own_after["zones"]["hand"]["count"],
        "从三个{}符文候选中选择{}并置入手牌".format(rune_zh, chosen_card_id),
    )


__all__ = [
    "AUTHORING_METADATA",
    "BLOOD_POOL",
    "CARDS",
    "CORPSE_SPENDER_POOL",
    "FROST_POOL",
    "SCENARIO_CARD_NAMES_ZH",
    "UNHOLY_POOL",
    "build_review_scenario",
]
