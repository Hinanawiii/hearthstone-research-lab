from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, Mapping

from ...engine import Game
from ...model import Action, ActionType, CardDef, CardType, Effect, HandCard, Minion, TargetRef
from ..review_format import review_state_from_observation

SOURCE_VERSION = "250339"
GENERATED_BY = "codex-gpt-5.6-core-secret-batch-v1"

TOKEN_CARDS: Dict[str, CardDef] = {
    "GIL_577t": CardDef(
        "GIL_577t",
        "末日骇鼠",
        CardType.MINION,
        6,
        6,
        6,
        races=("BEAST",),
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
}

CARDS: Dict[str, CardDef] = {
    "CORE_EX1_610": CardDef(
        "CORE_EX1_610",
        "爆炸陷阱",
        CardType.SPELL,
        2,
        rarity="COMMON",
        spell_school="FIRE",
        secret_kind="explosive_trap",
    ),
    "CORE_EX1_611": CardDef(
        "CORE_EX1_611",
        "冰冻陷阱",
        CardType.SPELL,
        2,
        rarity="COMMON",
        spell_school="FROST",
        secret_kind="freezing_trap",
    ),
    "CORE_GIL_577": CardDef(
        "CORE_GIL_577",
        "捕鼠陷阱",
        CardType.SPELL,
        2,
        rarity="EPIC",
        secret_kind="rat_trap",
        effects=(Effect("summon", card_id="GIL_577t"),),
    ),
    "CORE_ULD_152": CardDef(
        "CORE_ULD_152",
        "压感陷阱",
        CardType.SPELL,
        2,
        rarity="COMMON",
        secret_kind="pressure_plate",
    ),
    "CORE_BAR_812": CardDef(
        "CORE_BAR_812",
        "绿洲盟军",
        CardType.SPELL,
        3,
        rarity="COMMON",
        spell_school="FROST",
        secret_kind="oasis_ally",
        effects=(Effect("summon", card_id="CS2_033"),),
    ),
    "CORE_EX1_287": CardDef(
        "CORE_EX1_287",
        "法术反制",
        CardType.SPELL,
        3,
        rarity="RARE",
        spell_school="ARCANE",
        secret_kind="counterspell",
    ),
    "CORE_EX1_289": CardDef(
        "CORE_EX1_289",
        "寒冰护体",
        CardType.SPELL,
        3,
        rarity="COMMON",
        spell_school="FROST",
        secret_kind="ice_barrier",
    ),
    "CORE_LOOT_101": CardDef(
        "CORE_LOOT_101",
        "爆炸符文",
        CardType.SPELL,
        3,
        rarity="RARE",
        spell_school="FIRE",
        secret_kind="explosive_runes",
    ),
}

_SOURCE_TEXTS = {
    "CORE_EX1_610": "奥秘：当你的英雄受到攻击，对所有敌人造成2点伤害。",
    "CORE_EX1_611": "奥秘：当一个敌方随从攻击时，将其移回拥有者的手牌，并且法力值消耗增加（2）点。",
    "CORE_GIL_577": "奥秘：当你的对手在一回合中使用三张牌后，召唤一只6/6的老鼠。",
    "CORE_ULD_152": "奥秘：在你的对手施放一个法术后，随机消灭一个敌方 随从。",
    "CORE_BAR_812": "奥秘： 当一个友方随从受到攻击时，召唤一个3/6的水元素。",
    "CORE_EX1_287": "奥秘：当你的对手施放一个法术时，反制该法术。",
    "CORE_EX1_289": "奥秘：当你的英雄受到攻击时，获得8点护甲值。",
    "CORE_LOOT_101": "奥秘：在你的对手使用一张随从牌后，对该随从造成6点伤害，超过其生命值的伤害将由对方英雄 承受。",
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
    "CS2_029": "火球术",
    "EX1_277": "奥术飞弹",
    "GAME_005": "幸运币",
}


def _player(state: Mapping[str, Any], role_zh: str) -> Mapping[str, Any]:
    return next(item for item in state["players"] if item["role_zh"] == role_zh)


def build_review_scenario(card_id: str, card_registry: Mapping[str, CardDef]) -> Dict[str, Any]:
    if card_id not in CARDS:
        raise ValueError("unknown secret card: {}".format(card_id))
    card = CARDS[card_id]
    game = Game(seed=sum(ord(char) for char in card_id), card_registry=card_registry)
    owner = game.state.active_player
    opponent = 1 - owner
    own = game.state.players[owner]
    opposing = game.state.players[opponent]
    own.mana = own.max_mana = 10
    opposing.mana = opposing.max_mana = 10
    own.hand = []
    opposing.hand = []
    own.board = []
    opposing.board = []
    own.deck = ["CS2_120"]
    opposing.deck = ["CS2_120"]
    own.secrets = [card_id]
    game.state.active_player = opponent
    game.state.turn = 1

    if card_id in {"CORE_EX1_610", "CORE_EX1_611", "CORE_EX1_289"}:
        opposing.board = [Minion(230_001, "CS2_120", 3, 2, 2, summoned_turn=0)]
        action = Action(ActionType.ATTACK, 230_001, TargetRef.hero(owner))
    elif card_id == "CORE_BAR_812":
        own.board = [Minion(230_002, "CS2_120", 2, 3, 3, summoned_turn=0)]
        opposing.board = [Minion(230_003, "CS2_120", 3, 3, 3, summoned_turn=0)]
        action = Action(ActionType.ATTACK, 230_003, TargetRef.minion(owner, 230_002))
    elif card_id == "CORE_EX1_287":
        opposing.hand = [HandCard(230_004, "CS2_029")]
        action = Action(ActionType.PLAY, 230_004, TargetRef.hero(owner))
    elif card_id == "CORE_ULD_152":
        opposing.board = [Minion(230_005, "CS2_120", 2, 3, 3, summoned_turn=0)]
        opposing.hand = [HandCard(230_006, "EX1_277")]
        action = Action(ActionType.PLAY, 230_006)
    elif card_id == "CORE_GIL_577":
        opposing.cards_played_this_turn = 2
        opposing.hand = [HandCard(230_007, "GAME_005")]
        action = Action(ActionType.PLAY, 230_007)
    else:
        opposing.hand = [HandCard(230_008, "CS2_120")]
        action = Action(ActionType.PLAY, 230_008)

    before = review_state_from_observation(game.observation(owner))
    game.apply(action)
    after = review_state_from_observation(game.observation(owner))
    own_before = _player(before, "我方")
    own_after = _player(after, "我方")

    return {
        "scenario_id": "{}-secret-trigger-review-v1".format(card_id.lower().replace("_", "-")),
        "title_zh": "{}：奥秘触发核验".format(card.name),
        "purpose_zh": "核对奥秘区、触发条件、触发前后时点和一次性揭示。",
        "before": before,
        "action": {
            "type": "opponent_triggers_secret",
            "actor_player_id": opponent,
            "source_entity_id": action.source_id,
            "card_id": card_id,
            "target": asdict(action.target) if action.target else None,
            "description_zh": "让对手执行满足该奥秘条件的最小动作。",
            "engine_action": action.to_dict(),
        },
        "after": after,
        "assertions": [
            {
                "assertion_id": "secret-trigger-result",
                "subject_zh": "奥秘触发前后的公开状态",
                "before": {
                    "hero": own_before["hero"],
                    "board": own_before["zones"]["board"],
                    "secret_count": len(own_before["zones"]["secrets"]),
                },
                "after": {
                    "hero": own_after["hero"],
                    "board": own_after["zones"]["board"],
                    "secret_count": len(own_after["zones"]["secrets"]),
                },
                "expected_zh": "仅在条件满足时揭示一次，并在正确的伤害或施放时点结算",
            }
        ],
        "special_cases": [
            {
                "kind": "secret_zone",
                "summary_zh": "奥秘由隐藏区移除并公开结算。",
                "details": {
                    "player_id": owner,
                    "before_count": len(own_before["zones"]["secrets"]),
                    "after_count": len(own_after["zones"]["secrets"]),
                    "added_card_ids": [],
                    "removed_card_ids": [card_id],
                    "visibility_zh": "拥有者可见卡牌编号，对手仅见奥秘数量；触发后双方可见。",
                },
            }
        ],
    }
