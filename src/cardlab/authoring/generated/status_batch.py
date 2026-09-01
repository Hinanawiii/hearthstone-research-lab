from __future__ import annotations

from dataclasses import asdict
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
GENERATED_BY = "codex-gpt-5.6-core-status-batch-v1"

CARDS: Dict[str, CardDef] = {
    "CORE_EX1_169": CardDef(
        "CORE_EX1_169",
        "激活",
        CardType.SPELL,
        0,
        effects=(Effect("temporary_mana", 1, target="owner"),),
    ),
    "RLK_048": CardDef(
        "RLK_048",
        "反魔法护罩",
        CardType.SPELL,
        3,
        runes=("UNHOLY",),
        effects=(
            Effect("buff_all", target="friendly_minions", attack=1, health=1),
            Effect("grant_keyword_all", target="friendly_minions", keyword="elusive"),
        ),
    ),
    "CORE_CS2_009": CardDef(
        "CORE_CS2_009",
        "野性印记",
        CardType.SPELL,
        2,
        target_mode=TargetMode.ANY_MINION,
        effects=(
            Effect("buff", target="selected", attack=2, health=3),
            Effect("grant_keyword", target="selected", keyword="taunt"),
        ),
    ),
    "CORE_EX1_011": CardDef(
        "CORE_EX1_011",
        "巫医",
        CardType.MINION,
        1,
        2,
        1,
        target_mode=TargetMode.ANY_CHARACTER,
        effects=(Effect("heal", 2),),
    ),
    "CORE_ULD_191": CardDef(
        "CORE_ULD_191",
        "欢快的同伴",
        CardType.MINION,
        1,
        1,
        2,
        target_mode=TargetMode.FRIENDLY_MINION,
        effects=(Effect("buff", target="selected", health=2),),
    ),
    "CORE_GIL_622": CardDef(
        "CORE_GIL_622",
        "吸血蚊",
        CardType.MINION,
        4,
        3,
        3,
        effects=(
            Effect("damage", 3, target="enemy_hero"),
            Effect("heal", 3, target="owner_hero"),
        ),
    ),
    "CORE_EX1_362": CardDef(
        "CORE_EX1_362",
        "银色保卫者",
        CardType.MINION,
        2,
        3,
        2,
        target_mode=TargetMode.FRIENDLY_MINION,
        effects=(Effect("grant_keyword", target="selected", keyword="divine_shield"),),
    ),
    "CORE_EX1_619": CardDef(
        "CORE_EX1_619",
        "生而平等",
        CardType.SPELL,
        2,
        effects=(Effect("set_health_all", 1, target="all_minions"),),
    ),
    "CORE_AT_055": CardDef(
        "CORE_AT_055",
        "快速治疗",
        CardType.SPELL,
        1,
        target_mode=TargetMode.ANY_CHARACTER,
        effects=(Effect("heal", 5),),
    ),
    "CORE_CS1_112": CardDef(
        "CORE_CS1_112",
        "神圣新星",
        CardType.SPELL,
        3,
        effects=(
            Effect("damage_all", 2, target="enemy_minions"),
            Effect("heal_all", 2, target="friendly_characters"),
        ),
    ),
    "CORE_AT_064": CardDef(
        "CORE_AT_064",
        "怒袭",
        CardType.SPELL,
        2,
        target_mode=TargetMode.ANY_CHARACTER,
        effects=(
            Effect("damage", 3),
            Effect("armor", 3, target="owner_hero"),
        ),
    ),
}

_SOURCE_TEXTS = {
    "CORE_EX1_169": "在本回合中，获得一个 法力水晶。",
    "RLK_048": "使你的所有随从获得+1/+1和扰魔。",
    "CORE_CS2_009": "使一个随从获得嘲讽和+2/+3。（+2攻击力/+3生命值）",
    "CORE_EX1_011": "战吼： 恢复2点生命值。",
    "CORE_ULD_191": "战吼：使一个友方随从获得+2生命值。",
    "CORE_GIL_622": "战吼：对敌方英雄造成3点伤害。为你的英雄恢复3点生命值。",
    "CORE_EX1_362": "战吼：使一个其他友方随从获得圣盾。",
    "CORE_EX1_619": "将所有随从的生命值变为1。",
    "CORE_AT_055": "恢复5点生命值。",
    "CORE_CS1_112": "对所有敌方随从造成2点伤害，为所有友方角色恢复2点 生命值。",
    "CORE_AT_064": "造成3点伤害。获得3点 护甲值。",
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
    "CS2_172": "血沼迅猛龙",
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
        raise ValueError("unknown status batch card: {}".format(card_id))
    card = CARDS[card_id]
    game = Game(seed=sum(ord(char) for char in card_id), card_registry=card_registry)
    actor = game.state.active_player
    enemy = 1 - actor
    own = game.state.players[actor]
    opposing = game.state.players[enemy]
    own.hero_health = 22
    opposing.hero_health = 25
    own.deck = ["CS2_120"]
    opposing.deck = ["CS2_172"]
    own.hand = [HandCard(93_000, card_id)]
    opposing.hand = []
    own.board = [Minion(93_001, "CS2_120", 2, 2, 3, summoned_turn=0)]
    opposing.board = [
        Minion(93_002, "CS2_182", 4, 5, 5, summoned_turn=0),
        Minion(93_003, "CS2_172", 3, 3, 3, summoned_turn=0),
    ]
    own.mana = own.max_mana = 10
    opposing.mana = opposing.max_mana = 10
    if card_id == "CORE_EX1_169":
        own.mana = 5

    target_ref: Optional[TargetRef] = None
    target_description = "无目标"
    if card_id == "CORE_CS2_009":
        target_ref = TargetRef.minion(enemy, 93_002)
        target_description = "敌方冰风雪人"
    elif card_id in {"CORE_EX1_011", "CORE_AT_055"}:
        target_ref = TargetRef.hero(enemy)
        target_description = "敌方英雄"
    elif card_id in {"CORE_ULD_191", "CORE_EX1_362"}:
        target_ref = TargetRef.minion(actor, 93_001)
        target_description = "我方淡水鳄"
    elif card_id == "CORE_AT_064":
        target_ref = TargetRef.hero(actor)
        target_description = "我方英雄"

    action = Action(ActionType.PLAY, 93_000, target_ref)
    before = review_state_from_observation(game.observation(actor))
    game.apply(action)
    after = review_state_from_observation(game.observation(actor))
    own_before = _player(before, "我方")
    own_after = _player(after, "我方")
    enemy_before = _player(before, "敌方")
    enemy_after = _player(after, "敌方")
    assertions = [
        _assertion(
            "mana",
            "我方法力",
            own_before["resources"]["mana"],
            own_after["resources"]["mana"],
            "支付{}点法力".format(card.cost),
        )
    ]

    if card_id == "CORE_EX1_169":
        assertions.append(
            _assertion(
                "temporary-mana",
                "本回合临时法力",
                own_before["resources"]["temporary_mana"],
                own_after["resources"]["temporary_mana"],
                "获得1点仅限本回合使用的法力",
            )
        )
        title = "激活：获得本回合临时法力"
        purpose = "核对零费使用后增加1点临时法力，不增加永久法力上限。"
    elif card_id == "RLK_048":
        before_minion = _minion(before, "我方", "CS2_120")
        after_minion = _minion(after, "我方", "CS2_120")
        assertions.extend(
            [
                _assertion(
                    "friendly-board-buff",
                    "我方淡水鳄攻击力/生命值上限/当前生命值",
                    [before_minion["attack"], before_minion["max_health"], before_minion["health"]],
                    [after_minion["attack"], after_minion["max_health"], after_minion["health"]],
                    "永久获得+1/+1，受伤状态保留",
                ),
                _assertion(
                    "friendly-board-elusive",
                    "我方淡水鳄关键词",
                    before_minion["mechanics_zh"],
                    after_minion["mechanics_zh"],
                    "获得扰魔",
                ),
            ]
        )
        title = "反魔法护罩：强化全部友方随从"
        purpose = "核对场上每个友方随从同时获得+1/+1和扰魔，敌方随从不变。"
    elif card_id == "CORE_CS2_009":
        before_minion = _minion(before, "敌方", "CS2_182")
        after_minion = _minion(after, "敌方", "CS2_182")
        assertions.extend(
            [
                _assertion(
                    "enemy-minion-is-valid",
                    "敌方冰风雪人攻击力/生命值",
                    [before_minion["attack"], before_minion["health"]],
                    [after_minion["attack"], after_minion["health"]],
                    "敌方随从也是合法目标并获得+2/+3",
                ),
                _assertion(
                    "taunt-granted",
                    "敌方冰风雪人关键词",
                    before_minion["mechanics_zh"],
                    after_minion["mechanics_zh"],
                    "获得嘲讽",
                ),
            ]
        )
        title = "野性印记：可以强化敌方随从"
        purpose = "核对卡面写的是一个随从，因此敌方随从也可成为目标。"
    elif card_id in {"CORE_EX1_011", "CORE_AT_055"}:
        amount = 2 if card_id == "CORE_EX1_011" else 5
        assertions.append(
            _assertion(
                "enemy-hero-healed",
                "敌方英雄生命值",
                enemy_before["hero"]["health"],
                enemy_after["hero"]["health"],
                "敌方英雄是合法目标，恢复{}点生命值且不超过30".format(amount),
            )
        )
        title = "{}：可以治疗敌方英雄".format(card.name)
        purpose = "核对没有友方限制的治疗效果可以选择敌方角色。"
    elif card_id == "CORE_ULD_191":
        before_minion = _minion(before, "我方", "CS2_120")
        after_minion = _minion(after, "我方", "CS2_120")
        assertions.append(
            _assertion(
                "health-buff",
                "我方淡水鳄生命值上限/当前生命值",
                [before_minion["max_health"], before_minion["health"]],
                [after_minion["max_health"], after_minion["health"]],
                "获得+2生命值，同时提高上限和当前生命值",
            )
        )
        title = "欢快的同伴：增加友方随从生命值"
        purpose = "核对生命值增益同时提高当前生命值和生命值上限。"
    elif card_id == "CORE_GIL_622":
        assertions.extend(
            [
                _assertion(
                    "enemy-hero-damaged",
                    "敌方英雄生命值",
                    enemy_before["hero"]["health"],
                    enemy_after["hero"]["health"],
                    "固定受到3点伤害",
                ),
                _assertion(
                    "owner-hero-healed",
                    "我方英雄生命值",
                    own_before["hero"]["health"],
                    own_after["hero"]["health"],
                    "固定恢复3点生命值",
                ),
            ]
        )
        title = "吸血蚊：伤害对手并治疗自己"
        purpose = "核对两个固定英雄效果都结算，不需要选择目标。"
    elif card_id == "CORE_EX1_362":
        before_minion = _minion(before, "我方", "CS2_120")
        after_minion = _minion(after, "我方", "CS2_120")
        assertions.append(
            _assertion(
                "divine-shield-granted",
                "我方淡水鳄关键词",
                before_minion["mechanics_zh"],
                after_minion["mechanics_zh"],
                "其他友方随从获得圣盾",
            )
        )
        title = "银色保卫者：为其他友方随从提供圣盾"
        purpose = "核对目标必须是使用前已在场的友方随从，不能选择战吼来源自己。"
    elif card_id == "CORE_EX1_619":
        assertions.extend(
            [
                _assertion(
                    "friendly-health-set",
                    "我方淡水鳄生命值",
                    _minion(before, "我方", "CS2_120")["health"],
                    _minion(after, "我方", "CS2_120")["health"],
                    "友方随从生命值变为1",
                ),
                _assertion(
                    "enemy-health-set",
                    "敌方冰风雪人生命值",
                    _minion(before, "敌方", "CS2_182")["health"],
                    _minion(after, "敌方", "CS2_182")["health"],
                    "敌方随从生命值也变为1",
                ),
            ]
        )
        title = "生而平等：双方所有随从生命值变为1"
        purpose = "核对效果没有阵营限制，并同步修改当前生命值和生命值上限。"
    elif card_id == "CORE_CS1_112":
        assertions.extend(
            [
                _assertion(
                    "enemy-minions-damaged",
                    "敌方冰风雪人生命值",
                    _minion(before, "敌方", "CS2_182")["health"],
                    _minion(after, "敌方", "CS2_182")["health"],
                    "所有敌方随从受到2点伤害",
                ),
                _assertion(
                    "friendly-hero-healed",
                    "我方英雄生命值",
                    own_before["hero"]["health"],
                    own_after["hero"]["health"],
                    "友方英雄恢复2点生命值",
                ),
                _assertion(
                    "friendly-minion-healed",
                    "我方淡水鳄生命值",
                    _minion(before, "我方", "CS2_120")["health"],
                    _minion(after, "我方", "CS2_120")["health"],
                    "友方随从恢复2点，但不超过生命值上限",
                ),
            ]
        )
        title = "神圣新星：伤害敌方随从并治疗友方角色"
        purpose = "核对伤害只覆盖敌方随从，治疗覆盖友方英雄和友方随从。"
    else:
        assertions.extend(
            [
                _assertion(
                    "friendly-target-damaged",
                    "我方英雄生命值",
                    own_before["hero"]["health"],
                    own_after["hero"]["health"],
                    "我方英雄是合法目标并受到3点伤害",
                ),
                _assertion(
                    "armor-gained",
                    "我方英雄护甲",
                    own_before["hero"]["armor"],
                    own_after["hero"]["armor"],
                    "无论目标阵营，使用者都获得3点护甲",
                ),
            ]
        )
        title = "怒袭：可以伤害自己并获得护甲"
        purpose = "核对伤害目标没有阵营限制，护甲固定归使用者。"

    description = "我方使用《{}》".format(card.name)
    if target_ref is not None:
        description += "，选择{}".format(target_description)
    description += "。"
    return {
        "scenario_id": "{}-status-review-v1".format(card_id.lower().replace("_", "-")),
        "title_zh": title,
        "purpose_zh": purpose,
        "before": before,
        "action": {
            "type": "play_card",
            "actor_player_id": actor,
            "source_entity_id": 93_000,
            "card_id": card_id,
            "target": asdict(target_ref) if target_ref else None,
            "description_zh": description,
            "engine_action": action.to_dict(),
        },
        "after": after,
        "assertions": assertions,
        "special_cases": [],
    }


__all__ = [
    "AUTHORING_METADATA",
    "CARDS",
    "SCENARIO_CARD_NAMES_ZH",
    "build_review_scenario",
]
