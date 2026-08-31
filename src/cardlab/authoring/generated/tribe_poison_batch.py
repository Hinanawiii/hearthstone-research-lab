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
GENERATED_BY = "codex-gpt-5.6-core-tribe-poison-batch-v1"

CARDS: Dict[str, CardDef] = {
    "RLK_958": CardDef(
        "RLK_958",
        "骷髅帮手",
        CardType.MINION,
        1,
        1,
        2,
        target_mode=TargetMode.FRIENDLY_UNDEAD,
        effects=(Effect("buff", target="selected", attack=2),),
        races=("UNDEAD",),
    ),
    "CORE_EDR_002": CardDef(
        "CORE_EDR_002",
        "毒性吐息",
        CardType.SPELL,
        2,
        target_mode=TargetMode.FRIENDLY_UNDEAD,
        effects=(Effect("grant_keyword", target="selected", keyword="poisonous"),),
    ),
}

_SOURCE_TEXTS = {
    "RLK_958": "战吼：使一个友方亡灵获得+2攻击力。",
    "CORE_EDR_002": "使一个友方亡灵获得剧毒。",
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
    "RLK_503": "扛包收尸人",
    "CS2_120": "淡水鳄",
    "CS2_182": "冰风雪人",
}


def _player(state: Mapping[str, Any], role_zh: str) -> Mapping[str, Any]:
    return next(item for item in state["players"] if item["role_zh"] == role_zh)


def _minion(state: Mapping[str, Any], role_zh: str, card_id: str) -> Mapping[str, Any]:
    player = _player(state, role_zh)
    return next(item for item in player["zones"]["board"] if item["card_id"] == card_id)


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
        raise ValueError("unknown tribe and poison batch card: {}".format(card_id))
    card = CARDS[card_id]
    game = Game(seed=sum(ord(char) for char in card_id), card_registry=card_registry)
    actor = game.state.active_player
    enemy = 1 - actor
    own = game.state.players[actor]
    opposing = game.state.players[enemy]
    own.deck = ["CS2_120"]
    opposing.deck = ["CS2_182"]
    own.hand = [HandCard(95_000, card_id)]
    opposing.hand = []
    own.board = [
        Minion(
            95_001,
            "RLK_503",
            1,
            3,
            3,
            summoned_turn=0,
            races=("UNDEAD",),
        ),
        Minion(95_002, "CS2_120", 2, 3, 3, summoned_turn=0),
    ]
    opposing.board = [Minion(95_003, "CS2_182", 4, 5, 5, summoned_turn=0)]
    own.mana = own.max_mana = 10
    opposing.mana = opposing.max_mana = 10

    legal_target_ids = [
        action.target.entity_id
        for action in game.legal_actions()
        if action.action_type == ActionType.PLAY
        and action.source_id == 95_000
        and action.target is not None
    ]
    target = TargetRef.minion(actor, 95_001)
    action = Action(ActionType.PLAY, 95_000, target)
    before = review_state_from_observation(game.observation(actor))
    game.apply(action)
    after = review_state_from_observation(game.observation(actor))
    before_undead = _minion(before, "我方", "RLK_503")
    after_undead = _minion(after, "我方", "RLK_503")
    own_before = _player(before, "我方")
    own_after = _player(after, "我方")

    assertions = [
        _assertion(
            "mana",
            "我方法力",
            own_before["resources"]["mana"],
            own_after["resources"]["mana"],
            "支付{}点法力".format(card.cost),
        ),
        _assertion(
            "undead-only-target",
            "合法目标实体",
            legal_target_ids,
            legal_target_ids,
            "只有友方亡灵扛包收尸人可选；非亡灵淡水鳄不可选",
        ),
    ]
    special_cases = []
    if card_id == "RLK_958":
        assertions.append(
            _assertion(
                "undead-attack-buff",
                "扛包收尸人攻击力",
                before_undead["attack"],
                after_undead["attack"],
                "友方亡灵永久获得+2攻击力",
            )
        )
        title = "骷髅帮手：只强化友方亡灵"
        purpose = "核对种族目标过滤，并确认非亡灵友方随从不会成为合法目标。"
    else:
        assertions.append(
            _assertion(
                "poisonous-granted",
                "扛包收尸人关键词",
                before_undead["mechanics_zh"],
                after_undead["mechanics_zh"],
                "友方亡灵获得剧毒",
            )
        )
        special_cases.append(
            {
                "kind": "special_tags",
                "summary_zh": "目标保留亡灵种族标签，并新增剧毒关键词。",
                "details": {
                    "entity_id": 95_001,
                    "card_id": "RLK_503",
                    "tags_before": {
                        "races": before_undead["tags"].get("races", [])
                    },
                    "tags_after": {
                        "races": after_undead["tags"].get("races", []),
                        "poisonous": True,
                    },
                    "explanation_zh": "剧毒只在实际造成伤害时消灭受伤随从；圣盾阻止伤害时不触发。",
                },
            }
        )
        title = "毒性吐息：只赋予友方亡灵剧毒"
        purpose = "核对种族目标过滤和剧毒关键词写入，并由独立战斗测试验证剧毒伤害。"

    return {
        "scenario_id": "{}-tribe-poison-review-v1".format(
            card_id.lower().replace("_", "-")
        ),
        "title_zh": title,
        "purpose_zh": purpose,
        "before": before,
        "action": {
            "type": "play_card",
            "actor_player_id": actor,
            "source_entity_id": 95_000,
            "card_id": card_id,
            "target": asdict(target),
            "description_zh": "我方使用《{}》，选择友方亡灵扛包收尸人。".format(
                card.name
            ),
            "engine_action": action.to_dict(),
        },
        "after": after,
        "assertions": assertions,
        "special_cases": special_cases,
    }


__all__ = [
    "AUTHORING_METADATA",
    "CARDS",
    "SCENARIO_CARD_NAMES_ZH",
    "build_review_scenario",
]
