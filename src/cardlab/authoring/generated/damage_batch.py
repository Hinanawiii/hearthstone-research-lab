from __future__ import annotations

from dataclasses import asdict, dataclass
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
GENERATED_BY = "codex-gpt-5.6-core-damage-batch-v1"


@dataclass(frozen=True)
class DamageContract:
    card_id: str
    name_zh: str
    source_text_zh: str
    card_type: CardType
    cost: int
    damage: int
    effect_target: str
    attack: int = 0
    health: int = 0
    taunt: bool = False
    overload: int = 0


_CONTRACTS = (
    DamageContract(
        "CORE_CS2_029", "火球术", "造成6点伤害。", CardType.SPELL, 4, 6, "selected"
    ),
    DamageContract(
        "CORE_CS2_189",
        "精灵弓箭手",
        "战吼：造成1点伤害。",
        CardType.MINION,
        1,
        1,
        "selected",
        1,
        1,
    ),
    DamageContract(
        "CORE_UNG_084",
        "火羽凤凰",
        "战吼：造成3点伤害。",
        CardType.MINION,
        4,
        3,
        "selected",
        3,
        4,
    ),
    DamageContract(
        "CORE_CS2_042",
        "火元素",
        "战吼：造成4点伤害。",
        CardType.MINION,
        6,
        4,
        "selected",
        6,
        5,
    ),
    DamageContract(
        "CORE_EX1_238",
        "闪电箭",
        "造成3点伤害，过载：（1）",
        CardType.SPELL,
        1,
        3,
        "selected",
        overload=1,
    ),
    DamageContract(
        "CORE_CS2_093",
        "奉献",
        "对所有敌人造成2点伤害。",
        CardType.SPELL,
        3,
        2,
        "enemy_characters",
    ),
    DamageContract(
        "CORE_CS2_032",
        "烈焰风暴",
        "对所有敌方随从造成5点伤害。",
        CardType.SPELL,
        7,
        5,
        "enemy_minions",
    ),
    DamageContract(
        "CORE_EX1_259",
        "闪电风暴",
        "对所有敌方随从造成3点伤害，过载：（1）",
        CardType.SPELL,
        3,
        3,
        "enemy_minions",
        overload=1,
    ),
    DamageContract(
        "CORE_EX1_319",
        "烈焰小鬼",
        "战吼：对你的英雄造成3点伤害。",
        CardType.MINION,
        1,
        3,
        "owner_hero",
        3,
        2,
    ),
    DamageContract(
        "CORE_LOOT_013",
        "粗俗的矮劣魔",
        "嘲讽，战吼：对你的英雄造成2点伤害。",
        CardType.MINION,
        2,
        2,
        "owner_hero",
        2,
        4,
        taunt=True,
    ),
    DamageContract(
        "CORE_ULD_271",
        "受伤的托维尔人",
        "嘲讽。战吼：对本随从造成3点伤害。",
        CardType.MINION,
        2,
        3,
        "played_minion",
        2,
        6,
        taunt=True,
    ),
    DamageContract(
        "CORE_CS2_062",
        "地狱烈焰",
        "对所有角色造成3点伤害。",
        CardType.SPELL,
        3,
        3,
        "all_characters",
    ),
    DamageContract(
        "CORE_OG_149",
        "暴虐食尸鬼",
        "战吼：对所有其他随从造成1点伤害。",
        CardType.MINION,
        3,
        1,
        "all_other_minions",
        3,
        3,
    ),
    DamageContract(
        "CORE_UNG_848",
        "始生幼龙",
        "嘲讽，战吼： 对所有其他随从造成2点伤害。",
        CardType.MINION,
        8,
        2,
        "all_other_minions",
        4,
        8,
        taunt=True,
    ),
)

CONTRACTS: Dict[str, DamageContract] = {item.card_id: item for item in _CONTRACTS}


def _definition(contract: DamageContract) -> CardDef:
    single_target = contract.effect_target in {"selected", "owner_hero", "played_minion"}
    effect = Effect(
        "damage" if single_target else "damage_all",
        contract.damage,
        target=contract.effect_target,
    )
    return CardDef(
        card_id=contract.card_id,
        name=contract.name_zh,
        card_type=contract.card_type,
        cost=contract.cost,
        attack=contract.attack,
        health=contract.health,
        taunt=contract.taunt,
        target_mode=(
            TargetMode.ANY_CHARACTER
            if contract.effect_target == "selected"
            else TargetMode.NONE
        ),
        effects=(effect,),
        overload=contract.overload,
    )


CARDS: Dict[str, CardDef] = {
    card_id: _definition(contract) for card_id, contract in CONTRACTS.items()
}

AUTHORING_METADATA: Dict[str, Dict[str, Any]] = {
    card_id: {
        "source_version": SOURCE_VERSION,
        "source_text": contract.source_text_zh,
        "source_text_zh": contract.source_text_zh,
        "name_zh": contract.name_zh,
        "cost": contract.cost,
        "damage": contract.damage,
        "effect_target": contract.effect_target,
        "generated_by": GENERATED_BY,
        "review_status": "awaiting_human_scenario_review",
    }
    for card_id, contract in CONTRACTS.items()
}

SCENARIO_CARD_NAMES_ZH = {
    **{card_id: contract.name_zh for card_id, contract in CONTRACTS.items()},
    "CS2_120": "淡水鳄",
    "CS2_172": "血沼迅猛龙",
    "CS2_231": "小精灵",
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
    if card_id not in CONTRACTS:
        raise ValueError("unknown damage batch card: {}".format(card_id))
    contract = CONTRACTS[card_id]
    game = Game(seed=sum(ord(char) for char in card_id), card_registry=card_registry)
    actor = game.state.active_player
    enemy = 1 - actor
    own = game.state.players[actor]
    opposing = game.state.players[enemy]
    own.hero_health = 30
    opposing.hero_health = 30
    own.deck = ["CS2_120"]
    opposing.deck = ["CS2_172"]
    own.hand = [HandCard(92_000, card_id)]
    opposing.hand = []
    own.board = [Minion(92_001, "CS2_120", 2, 6, 6, summoned_turn=0)]
    opposing.board = [
        Minion(92_002, "CS2_231", 1, 2, 2, summoned_turn=0),
        Minion(92_003, "CS2_172", 3, 7, 7, summoned_turn=0),
    ]
    own.mana = own.max_mana = 10
    opposing.mana = opposing.max_mana = 10

    target_ref: Optional[TargetRef] = None
    target: Optional[Dict[str, Any]] = None
    if contract.effect_target == "selected":
        target_ref = TargetRef.hero(actor)
        target = asdict(target_ref)
    action = Action(ActionType.PLAY, 92_000, target_ref)
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
            "支付{}点法力".format(contract.cost),
        )
    ]

    if contract.effect_target in {"selected", "owner_hero"}:
        assertions.append(
            _assertion(
                "friendly-hero-damage",
                "我方英雄生命值",
                own_before["hero"]["health"],
                own_after["hero"]["health"],
                "受到{}点伤害".format(contract.damage),
            )
        )
        title = "{}：伤害结算到我方英雄".format(contract.name_zh)
        purpose = (
            "核对无阵营限制的目标可以选择我方英雄，并只伤害所选角色。"
            if contract.effect_target == "selected"
            else "核对战吼伤害固定结算到使用者的英雄，不要求选择目标。"
        )
    elif contract.effect_target == "played_minion":
        played = _minion(after, "我方", card_id)
        assertions.append(
            _assertion(
                "played-minion-damage",
                "进场随从生命值",
                contract.health,
                played["health"],
                "战吼对本随从造成{}点伤害".format(contract.damage),
            )
        )
        title = "{}：战吼伤害自身".format(contract.name_zh)
        purpose = "核对随从先进入场上，再由战吼对该实体造成伤害。"
    elif contract.effect_target == "enemy_characters":
        assertions.extend(
            [
                _assertion(
                    "enemy-hero-damage",
                    "敌方英雄生命值",
                    enemy_before["hero"]["health"],
                    enemy_after["hero"]["health"],
                    "敌方英雄受到{}点伤害".format(contract.damage),
                ),
                _assertion(
                    "friendly-minion-safe",
                    "我方淡水鳄生命值",
                    _minion(before, "我方", "CS2_120")["health"],
                    _minion(after, "我方", "CS2_120")["health"],
                    "友方随从不属于敌人，生命值不变",
                ),
            ]
        )
        title = "{}：伤害所有敌人".format(contract.name_zh)
        purpose = "核对敌方英雄和敌方随从同时受伤，友方角色不受影响。"
    elif contract.effect_target == "enemy_minions":
        assertions.extend(
            [
                _assertion(
                    "enemy-hero-safe",
                    "敌方英雄生命值",
                    enemy_before["hero"]["health"],
                    enemy_after["hero"]["health"],
                    "效果只伤害敌方随从，敌方英雄不受影响",
                ),
                _assertion(
                    "enemy-large-minion-damage",
                    "敌方血沼迅猛龙生命值",
                    _minion(before, "敌方", "CS2_172")["health"],
                    _minion(after, "敌方", "CS2_172")["health"],
                    "受到{}点伤害".format(contract.damage),
                ),
            ]
        )
        title = "{}：只伤害所有敌方随从".format(contract.name_zh)
        purpose = "核对群体伤害包含每个敌方随从，但不包含英雄或友方随从。"
    elif contract.effect_target == "all_characters":
        assertions.extend(
            [
                _assertion(
                    "both-heroes-damaged",
                    "双方英雄生命值",
                    [own_before["hero"]["health"], enemy_before["hero"]["health"]],
                    [own_after["hero"]["health"], enemy_after["hero"]["health"]],
                    "双方英雄各受到{}点伤害".format(contract.damage),
                ),
                _assertion(
                    "friendly-minion-damaged",
                    "我方淡水鳄生命值",
                    _minion(before, "我方", "CS2_120")["health"],
                    _minion(after, "我方", "CS2_120")["health"],
                    "友方随从也受到{}点伤害".format(contract.damage),
                ),
            ]
        )
        title = "{}：伤害所有角色".format(contract.name_zh)
        purpose = "核对双方英雄和双方随从都属于所有角色。"
    else:
        played = _minion(after, "我方", card_id)
        assertions.extend(
            [
                _assertion(
                    "source-excluded",
                    "战吼来源随从生命值",
                    contract.health,
                    played["health"],
                    "所有其他随从不包含刚进场的战吼来源",
                ),
                _assertion(
                    "friendly-other-damaged",
                    "我方淡水鳄生命值",
                    _minion(before, "我方", "CS2_120")["health"],
                    _minion(after, "我方", "CS2_120")["health"],
                    "其他友方随从受到{}点伤害".format(contract.damage),
                ),
                _assertion(
                    "enemy-other-damaged",
                    "敌方血沼迅猛龙生命值",
                    _minion(before, "敌方", "CS2_172")["health"],
                    _minion(after, "敌方", "CS2_172")["health"],
                    "其他敌方随从受到{}点伤害".format(contract.damage),
                ),
            ]
        )
        title = "{}：伤害所有其他随从".format(contract.name_zh)
        purpose = "核对效果覆盖双方已有随从，但排除触发该战吼的随从本身。"

    if contract.overload:
        assertions.append(
            _assertion(
                "overload-pending",
                "待结算过载",
                own_before["resources"]["overload_pending"],
                own_after["resources"]["overload_pending"],
                "记录{}点过载，留到使用者下回合结算".format(contract.overload),
            )
        )

    description = "我方使用《{}》".format(contract.name_zh)
    if target_ref is not None:
        description += "，选择我方英雄作为目标"
    description += "。"
    return {
        "scenario_id": "{}-damage-review-v1".format(card_id.lower().replace("_", "-")),
        "title_zh": title,
        "purpose_zh": purpose,
        "before": before,
        "action": {
            "type": "play_card",
            "actor_player_id": actor,
            "source_entity_id": 92_000,
            "card_id": card_id,
            "target": target,
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
    "CONTRACTS",
    "SCENARIO_CARD_NAMES_ZH",
    "build_review_scenario",
]
