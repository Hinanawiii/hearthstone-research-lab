from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, Mapping, Optional, Tuple

from ...engine import Game
from ...model import Action, ActionType, CardDef, CardType, HandCard, Minion, TargetRef
from ..review_format import review_state_from_observation

SOURCE_VERSION = "250339"
GENERATED_BY = "codex-gpt-5.6-sol-keyword-batch-v1"

# card_id: (name_zh, source_text_zh, cost, attack, health, keywords, overload)
_SOURCE_CONTRACTS: Mapping[str, Tuple[str, str, int, int, int, Tuple[str, ...], int]] = {
    "Core_CS2_200": ("石拳食人魔", "", 6, 6, 7, (), 0),
    "CORE_BT_701": ("间谍女郎", "潜行", 1, 3, 1, ("STEALTH",), 0),
    "CORE_EX1_010": ("狼人渗透者", "潜行", 1, 2, 1, ("STEALTH",), 0),
    "CORE_GIL_558": ("沼泽水蛭", "吸血", 1, 2, 1, ("LIFESTEAL",), 0),
    "CORE_ULD_723": ("鱼人木乃伊", "复生", 1, 1, 1, ("REBORN",), 0),
    "CORE_NEW1_023": ("精灵龙", "扰魔", 2, 3, 2, ("ELUSIVE",), 0),
    "CS3_038": ("红鳃锋颚战士", "突袭", 2, 3, 1, ("RUSH",), 0),
    "CORE_EX1_028": ("荆棘谷猛虎", "潜行", 5, 5, 5, ("STEALTH",), 0),
    "CORE_LOOT_137": ("贪睡巨龙", "嘲讽", 9, 6, 12, ("TAUNT",), 0),
    "CORE_ICC_038": (
        "正义保护者",
        "嘲讽 圣盾",
        1,
        1,
        1,
        ("DIVINE_SHIELD", "TAUNT"),
        0,
    ),
    "CORE_GVG_085": (
        "吵吵机器人",
        "嘲讽 圣盾",
        2,
        1,
        2,
        ("DIVINE_SHIELD", "TAUNT"),
        0,
    ),
    "CORE_AT_052": ("图腾魔像", "过载：（1）", 2, 3, 4, ("OVERLOAD",), 1),
    "CORE_DRG_079": (
        "辟法巨龙",
        "突袭。圣盾。扰魔",
        6,
        5,
        4,
        ("DIVINE_SHIELD", "ELUSIVE", "RUSH"),
        0,
    ),
    "CORE_EX1_250": (
        "土元素",
        "嘲讽，过载：（2）",
        5,
        7,
        9,
        ("OVERLOAD", "TAUNT"),
        2,
    ),
}


def _definition(
    card_id: str,
    contract: Tuple[str, str, int, int, int, Tuple[str, ...], int],
) -> CardDef:
    name, _text, cost, attack, health, keywords, overload = contract
    mechanics = set(keywords)
    return CardDef(
        card_id=card_id,
        name=name,
        card_type=CardType.MINION,
        cost=cost,
        attack=attack,
        health=health,
        taunt="TAUNT" in mechanics,
        stealth="STEALTH" in mechanics,
        lifesteal="LIFESTEAL" in mechanics,
        reborn="REBORN" in mechanics,
        elusive="ELUSIVE" in mechanics,
        rush="RUSH" in mechanics,
        divine_shield="DIVINE_SHIELD" in mechanics,
        overload=overload,
    )


CARDS: Dict[str, CardDef] = {
    card_id: _definition(card_id, contract)
    for card_id, contract in _SOURCE_CONTRACTS.items()
}

AUTHORING_METADATA: Dict[str, Dict[str, Any]] = {
    card_id: {
        "source_version": SOURCE_VERSION,
        "source_text": contract[1],
        "source_text_zh": contract[1],
        "name_zh": contract[0],
        "cost": contract[2],
        "attack": contract[3],
        "health": contract[4],
        "keywords": list(contract[5]),
        "overload": contract[6],
        "generated_by": GENERATED_BY,
        "review_status": "awaiting_human_scenario_review",
    }
    for card_id, contract in _SOURCE_CONTRACTS.items()
}

SCENARIO_CARD_NAMES_ZH = {
    **{card_id: contract[0] for card_id, contract in _SOURCE_CONTRACTS.items()},
    "CS2_029": "火球术",
    "CS2_120": "淡水鳄",
    "CS2_172": "血沼迅猛龙",
}


def _minion(entity_id: int, card: CardDef, *, summoned_turn: int) -> Minion:
    return Minion(
        entity_id=entity_id,
        card_id=card.card_id,
        attack=card.attack,
        health=card.health,
        max_health=card.health,
        taunt=card.taunt,
        charge=card.charge,
        stealth=card.stealth,
        lifesteal=card.lifesteal,
        reborn=card.reborn,
        elusive=card.elusive,
        rush=card.rush,
        divine_shield=card.divine_shield,
        summoned_turn=summoned_turn,
    )


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


def _card_on_board(state: Mapping[str, Any], role_zh: str, card_id: str) -> Dict[str, Any]:
    for player in state["players"]:
        if player["role_zh"] != role_zh:
            continue
        for minion in player["zones"]["board"]:
            if minion["card_id"] == card_id:
                return dict(minion)
    raise AssertionError("scenario card is not on the board: {}".format(card_id))


def build_review_scenario(
    card_id: str, card_registry: Mapping[str, CardDef]
) -> Dict[str, Any]:
    """Build and execute one deterministic Chinese review scenario for a batch card."""
    if card_id not in CARDS:
        raise ValueError("unknown keyword batch card: {}".format(card_id))
    if card_id not in card_registry:
        raise ValueError("card registry is missing batch card: {}".format(card_id))

    card = CARDS[card_id]
    metadata = AUTHORING_METADATA[card_id]
    game = Game(seed=sum(ord(char) for char in card_id), card_registry=card_registry)
    actor = game.state.active_player
    enemy = 1 - actor
    own = game.state.players[actor]
    opposing = game.state.players[enemy]
    own.deck = ["CS2_120"]
    opposing.deck = ["CS2_120"]
    own.board = []
    opposing.board = []
    own.hand = []
    opposing.hand = []
    own.mana = own.max_mana = 10
    opposing.mana = opposing.max_mana = 10
    action: Action
    action_type = "attack"
    source_entity_id: Optional[int] = 81_001
    target: Optional[Dict[str, Any]]
    assertions = []
    stealth_enemy_can_target: Optional[bool] = None
    stealth_enemy_can_target_after: Optional[bool] = None

    keywords = set(metadata["keywords"])
    if not keywords:
        own.hand = [HandCard(81_000, card_id)]
        action = Action(ActionType.PLAY, source_id=81_000)
        action_type = "play_card"
        source_entity_id = 81_000
        target = None
        title = "{}：按原始费用召唤白板随从".format(card.name)
        purpose = "核对费用、攻击力和生命值均与卡牌来源一致，且没有额外关键词。"
        description = "我方支付{}点法力，使用《{}》。".format(card.cost, card.name)
    elif "OVERLOAD" in keywords:
        owner = opposing
        owner.board = [_minion(81_001, card, summoned_turn=game.state.turn - 1)]
        owner.max_mana = 4
        owner.mana = 0
        owner.overload_pending = card.overload
        action = Action.end_turn()
        action_type = "end_turn"
        source_entity_id = None
        target = None
        title = "{}：下个回合锁定过载法力".format(card.name)
        purpose = "核对使用者进入下个回合时锁定{}点法力，过载只结算一次。".format(
            card.overload
        )
        description = "对手结束回合，使使用过《{}》的一方开始下个回合。".format(card.name)
    elif "REBORN" in keywords:
        own.board = [_minion(81_001, card, summoned_turn=game.state.turn - 1)]
        opposing.board = [Minion(81_002, "CS2_120", 1, 1, 1)]
        target_ref = TargetRef.minion(enemy, 81_002)
        action = Action(ActionType.ATTACK, 81_001, target_ref)
        target = asdict(target_ref)
        title = "{}：首次死亡后以1点生命复生".format(card.name)
        purpose = "核对原实体死亡后生成一个1血新实体，且新实体不再具有复生。"
        description = "我方《{}》攻击敌方1/1随从，双方同时受到致死伤害。".format(card.name)
    elif "LIFESTEAL" in keywords:
        opposing.hero_health = 25
        own.board = [
            Minion(
                81_001,
                "CS2_120",
                1,
                3,
                3,
                summoned_turn=game.state.turn - 1,
            )
        ]
        opposing.board = [_minion(81_002, card, summoned_turn=game.state.turn - 1)]
        target_ref = TargetRef.minion(enemy, 81_002)
        action = Action(ActionType.ATTACK, 81_001, target_ref)
        target = asdict(target_ref)
        title = "{}：作为防守方也会触发吸血".format(card.name)
        purpose = "核对吸血随从反击时也会按实际伤害治疗其拥有者。"
        description = "我方随从攻击敌方《{}》，由它造成反击伤害。".format(card.name)
    elif "STEALTH" in keywords:
        own.board = [_minion(81_001, card, summoned_turn=game.state.turn - 1)]
        opposing.board = [Minion(81_002, "CS2_120", 0, 10, 10)]
        opposing.hand = [HandCard(81_003, "CS2_029")]
        targeting_check = game.clone()
        targeting_check.state.active_player = enemy
        stealth_enemy_can_target = any(
            candidate.target == TargetRef.minion(actor, 81_001)
            for candidate in targeting_check.legal_actions()
            if candidate.action_type in {ActionType.PLAY, ActionType.HERO_POWER, ActionType.ATTACK}
        )
        target_ref = TargetRef.minion(enemy, 81_002)
        action = Action(ActionType.ATTACK, 81_001, target_ref)
        target = asdict(target_ref)
        title = "{}：攻击后移除潜行".format(card.name)
        purpose = "核对潜行时不能被敌方选择为目标或攻击，主动攻击后立即失去潜行。"
        description = "我方处于潜行的《{}》主动攻击敌方随从。".format(card.name)
    elif "RUSH" in keywords:
        own.board = [_minion(81_001, card, summoned_turn=game.state.turn)]
        opposing.board = [Minion(81_002, "CS2_120", 2, 10, 10)]
        target_ref = TargetRef.minion(enemy, 81_002)
        action = Action(ActionType.ATTACK, 81_001, target_ref)
        target = asdict(target_ref)
        title = "{}：进场回合突袭敌方随从".format(card.name)
        purpose = "核对突袭随从进场当回合可以攻击随从，但不能攻击敌方英雄。"
        if card.divine_shield:
            purpose += "同时核对圣盾抵消反击伤害，扰魔仍然保留。"
        description = "本回合进场的《{}》以突袭攻击敌方随从。".format(card.name)
    elif "ELUSIVE" in keywords:
        opposing.board = [_minion(81_002, card, summoned_turn=game.state.turn - 1)]
        own.board = [Minion(81_001, "CS2_120", 1, 5, 5, summoned_turn=game.state.turn - 1)]
        own.hand = [HandCard(81_003, "CS2_029")]
        target_ref = TargetRef.minion(enemy, 81_002)
        action = Action(ActionType.ATTACK, 81_001, target_ref)
        target = asdict(target_ref)
        title = "{}：扰魔不阻止随从攻击".format(card.name)
        purpose = "核对扰魔不能成为法术或英雄技能目标，但仍能被随从正常攻击。"
        description = "我方随从攻击具有扰魔的敌方《{}》。".format(card.name)
    else:
        opposing.board = [
            _minion(81_002, card, summoned_turn=game.state.turn - 1),
            Minion(81_003, "CS2_120", 2, 3, 3),
        ]
        own.board = [Minion(81_001, "CS2_172", 2, 3, 3, summoned_turn=game.state.turn - 1)]
        target_ref = TargetRef.minion(enemy, 81_002)
        action = Action(ActionType.ATTACK, 81_001, target_ref)
        target = asdict(target_ref)
        title = "{}：嘲讽限定攻击目标".format(card.name)
        purpose = "核对有嘲讽时不能攻击其他角色。"
        if card.divine_shield:
            purpose += " 同时核对圣盾替代第一次伤害并在结算后消失。"
        description = "我方随从攻击敌方具有嘲讽的《{}》。".format(card.name)

    before_legal = game.legal_actions()
    before = review_state_from_observation(game.observation(actor))
    game.apply(action)
    after = review_state_from_observation(game.observation(actor))
    if "STEALTH" in keywords:
        targeting_check = game.clone()
        targeting_check.state.active_player = enemy
        stealth_enemy_can_target_after = any(
            candidate.target == TargetRef.minion(actor, 81_001)
            for candidate in targeting_check.legal_actions()
            if candidate.action_type in {ActionType.PLAY, ActionType.HERO_POWER, ActionType.ATTACK}
        )

    if not keywords:
        played = _card_on_board(after, "我方", card_id)
        assertions.extend(
            [
                _assertion("mana", "我方法力", 10, 10 - card.cost, "支付原始费用"),
                _assertion(
                    "stats",
                    "召唤后的攻击力/生命值",
                    "不在场",
                    [played["attack"], played["health"]],
                    "面板为{}/{}且没有关键词".format(card.attack, card.health),
                ),
            ]
        )
    elif "OVERLOAD" in keywords:
        owner_before = next(player for player in before["players"] if player["role_zh"] == "敌方")
        owner_after = next(player for player in after["players"] if player["role_zh"] == "敌方")
        assertions.extend(
            [
                _assertion(
                    "overload-lock",
                    "使用者本回合锁定法力",
                    owner_before["resources"]["overloaded_mana"],
                    owner_after["resources"]["overloaded_mana"],
                    "下个回合锁定{}点法力".format(card.overload),
                ),
                _assertion(
                    "overload-pending",
                    "待结算过载",
                    owner_before["resources"]["overload_pending"],
                    owner_after["resources"]["overload_pending"],
                    "结算后清零，不会自动延续到再下个回合",
                ),
            ]
        )
    elif "REBORN" in keywords:
        returned = _card_on_board(after, "我方", card_id)
        assertions.extend(
            [
                _assertion(
                    "new-entity", "实体编号", 81_001, returned["entity_id"], "以新实体返回"
                ),
                _assertion("reborn-health", "复生实体生命值", card.health, 1, "以1点生命返回"),
                _assertion("reborn-consumed", "复生关键词", "有", "无", "复生只触发一次"),
            ]
        )
    elif "LIFESTEAL" in keywords:
        opposing_after = next(
            player for player in after["players"] if player["role_zh"] == "敌方"
        )
        assertions.extend(
            [
                _assertion(
                    "lifesteal-heal-as-defender",
                    "敌方英雄生命值",
                    25,
                    opposing_after["hero"]["health"],
                    "吸血随从作为防守方造成{}点伤害，仍为其拥有者恢复生命".format(
                        card.attack
                    ),
                ),
                _assertion(
                    "lifesteal-minion-dies",
                    "吸血随从是否仍在场",
                    True,
                    any(
                        minion["card_id"] == card_id
                        for minion in opposing_after["zones"]["board"]
                    ),
                    "受到致命伤害后离场；本次治疗来自同时结算的反击伤害",
                ),
            ]
        )
    elif "STEALTH" in keywords:
        result = _card_on_board(after, "我方", card_id)
        assertions.extend(
            [
                _assertion(
                    "stealth-protection",
                    "敌方可选择或攻击该潜行随从",
                    stealth_enemy_can_target,
                    stealth_enemy_can_target_after,
                    "攻击前不能成为敌方目标；失去潜行后可以被选择",
                ),
                _assertion(
                    "stealth-removed",
                    "潜行关键词",
                    True,
                    "潜行" in result["mechanics_zh"],
                    "主动攻击后失去潜行",
                ),
            ]
        )
    elif "RUSH" in keywords:
        rush_result = (
            _card_on_board(after, "我方", card_id)
            if card.health > 2 or card.divine_shield
            else None
        )
        hero_attack_available = Action(
            ActionType.ATTACK, 81_001, TargetRef.hero(enemy)
        ) in before_legal
        assertions.append(
            _assertion(
                "rush-restriction",
                "进场回合能否攻击英雄",
                hero_attack_available,
                False,
                "本回合只能攻击随从",
            )
        )
        if card.divine_shield and rush_result is not None:
            assertions.extend(
                [
                    _assertion(
                        "shield",
                        "圣盾与生命值",
                        [True, card.health],
                        ["圣盾" in rush_result["mechanics_zh"], rush_result["health"]],
                        "圣盾替代反击伤害后消失，生命值不变",
                    ),
                    _assertion(
                        "elusive",
                        "扰魔关键词",
                        True,
                        "扰魔" in rush_result["mechanics_zh"],
                        "战斗不会移除扰魔",
                    ),
                ]
            )
    elif "ELUSIVE" in keywords:
        result = _card_on_board(after, "敌方", card_id)
        targeted = any(
            candidate.target == TargetRef.minion(enemy, 81_002)
            for candidate in before_legal
            if candidate.action_type in {ActionType.PLAY, ActionType.HERO_POWER}
        )
        assertions.extend(
            [
                _assertion(
                    "elusive-targeting",
                    "法术或英雄技能能否选择扰魔随从",
                    targeted,
                    False,
                    "不能成为法术或英雄技能目标",
                ),
                _assertion(
                    "elusive-combat",
                    "扰魔随从生命值",
                    card.health,
                    result["health"],
                    "可以被随从攻击并受到1点战斗伤害",
                ),
            ]
        )
    else:
        result = _card_on_board(after, "敌方", card_id)
        other_target_available = any(
            candidate.action_type == ActionType.ATTACK
            and candidate.target == TargetRef.minion(enemy, 81_003)
            for candidate in before_legal
        )
        assertions.append(
            _assertion(
                "taunt",
                "能否绕过嘲讽攻击其他随从",
                other_target_available,
                False,
                "嘲讽随从在场时只能攻击嘲讽随从",
            )
        )
        if card.divine_shield:
            assertions.append(
                _assertion(
                    "divine-shield",
                    "圣盾与生命值",
                    [True, card.health],
                    ["圣盾" in result["mechanics_zh"], result["health"]],
                    "第一次伤害由圣盾替代，生命值不变",
                )
            )

    return {
        "scenario_id": "{}-keyword-review-v1".format(card_id.lower().replace("_", "-")),
        "title_zh": title,
        "purpose_zh": purpose,
        "before": before,
        "action": {
            "type": action_type,
            "actor_player_id": actor,
            "source_entity_id": source_entity_id,
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
    "SCENARIO_CARD_NAMES_ZH",
    "build_review_scenario",
]
