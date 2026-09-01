from __future__ import annotations

from dataclasses import dataclass
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
GENERATED_BY = "codex-gpt-5.6-core-choose-one-batch-v1"

TOKEN_CARDS: Dict[str, CardDef] = {
    "AT_037t": CardDef("AT_037t", "树苗", CardType.MINION, 1, 1, 1, collectible=False),
    "EX1_160t": CardDef(
        "EX1_160t",
        "猎豹",
        CardType.MINION,
        2,
        3,
        2,
        races=("BEAST",),
        collectible=False,
    ),
    "TSC_650t": CardDef(
        "TSC_650t",
        "虎鲸",
        CardType.MINION,
        6,
        6,
        6,
        taunt=True,
        races=("BEAST",),
        collectible=False,
    ),
    "TSC_650t4": CardDef(
        "TSC_650t4",
        "海獭",
        CardType.MINION,
        1,
        1,
        1,
        rush=True,
        races=("BEAST",),
        collectible=False,
    ),
}

SUPPORT_CARDS: Dict[str, CardDef] = {
    "CHOOSE_TEST_MINION": CardDef(
        "CHOOSE_TEST_MINION",
        "测试随从",
        CardType.MINION,
        1,
        2,
        4,
        collectible=False,
    ),
    "CHOOSE_TEST_DRAW": CardDef(
        "CHOOSE_TEST_DRAW",
        "测试牌库牌",
        CardType.MINION,
        1,
        1,
        1,
        collectible=False,
    ),
}


@dataclass(frozen=True)
class ChooseContract:
    card_id: str
    name_zh: str
    source_text_zh: str
    definition: CardDef
    scenario_choice: int
    expected_zh: str


_CONTRACTS = (
    ChooseContract(
        "CORE_AT_037",
        "活体根须",
        "抉择：造成2点伤害；或者召唤两个1/1的树苗。",
        CardDef(
            "CORE_AT_037",
            "活体根须",
            CardType.SPELL,
            1,
            choose_one_effects=(
                (Effect("damage", 2),),
                (Effect("summon", 2, card_id="AT_037t"),),
            ),
            choose_one_target_modes=(TargetMode.ANY_CHARACTER, TargetMode.NONE),
            spell_school="NATURE",
        ),
        1,
        "选择召唤分支后，我方召唤两个1/1树苗，不需要选择伤害目标。",
    ),
    ChooseContract(
        "CORE_EX1_154",
        "愤怒",
        "抉择： 对一个随从造成3点伤害；或者造成1点伤害并抽一张牌。",
        CardDef(
            "CORE_EX1_154",
            "愤怒",
            CardType.SPELL,
            2,
            choose_one_effects=(
                (Effect("damage", 3),),
                (Effect("damage", 1), Effect("draw", 1)),
            ),
            choose_one_target_modes=(TargetMode.ANY_MINION, TargetMode.ANY_MINION),
            spell_school="NATURE",
        ),
        1,
        "选择抽牌分支后，所选随从受到1点伤害，我方抽一张牌。",
    ),
    ChooseContract(
        "CORE_EX1_160",
        "野性之力",
        "抉择：使你的所有随从获得+1/+1；或者召唤一只3/2的 猎豹。",
        CardDef(
            "CORE_EX1_160",
            "野性之力",
            CardType.SPELL,
            2,
            choose_one_effects=(
                (Effect("buff_all", target="friendly_minions", attack=1, health=1),),
                (Effect("summon", 1, card_id="EX1_160t"),),
            ),
            choose_one_target_modes=(TargetMode.NONE, TargetMode.NONE),
        ),
        0,
        "选择群体增益分支后，场上已有的友方随从获得+1/+1。",
    ),
    ChooseContract(
        "CORE_OG_047",
        "野性之怒",
        "抉择：使你的英雄在本回合中获得+4攻击力；或者获得8点护甲值。",
        CardDef(
            "CORE_OG_047",
            "野性之怒",
            CardType.SPELL,
            3,
            choose_one_effects=(
                (Effect("temporary_hero_attack", attack=4),),
                (Effect("armor", 8, target="owner_hero"),),
            ),
            choose_one_target_modes=(TargetMode.NONE, TargetMode.NONE),
        ),
        1,
        "选择护甲分支后，我方英雄获得8点护甲，不获得临时攻击力。",
    ),
    ChooseContract(
        "CORE_TSC_650",
        "划水好友",
        "抉择：召唤一只6/6并具有嘲讽的虎鲸；或者六只1/1并具有突袭的海獭。",
        CardDef(
            "CORE_TSC_650",
            "划水好友",
            CardType.SPELL,
            5,
            choose_one_effects=(
                (Effect("summon", 1, card_id="TSC_650t"),),
                (Effect("summon", 6, card_id="TSC_650t4"),),
            ),
            choose_one_target_modes=(TargetMode.NONE, TargetMode.NONE),
            spell_school="NATURE",
        ),
        1,
        "选择海獭分支后，我方召唤六只1/1并具有突袭的海獭。",
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
}


def _player(state: Mapping[str, Any], role_zh: str) -> Mapping[str, Any]:
    return next(item for item in state["players"] if item["role_zh"] == role_zh)


def _focus(state: Mapping[str, Any]) -> Dict[str, Any]:
    own = _player(state, "我方")
    enemy = _player(state, "敌方")
    return {
        "我方英雄": own["hero"],
        "敌方英雄": enemy["hero"],
        "我方手牌": own["zones"]["hand"],
        "我方牌库": own["zones"]["deck"],
        "我方场上": own["zones"]["board"],
        "敌方场上": enemy["zones"]["board"],
    }


def build_review_scenario(card_id: str, card_registry: Mapping[str, CardDef]) -> Dict[str, Any]:
    if card_id not in CONTRACTS:
        raise ValueError("unknown choose-one batch card: {}".format(card_id))
    contract = CONTRACTS[card_id]
    registry = dict(card_registry)
    registry.update(TOKEN_CARDS)
    registry.update(SUPPORT_CARDS)
    game = Game(seed=sum(ord(char) for char in card_id), card_registry=registry)
    owner = game.state.active_player
    enemy = 1 - owner
    own = game.state.players[owner]
    opposing = game.state.players[enemy]
    own.hero_health = opposing.hero_health = 30
    own.mana = own.max_mana = 10
    opposing.mana = opposing.max_mana = 10
    own.deck = ["CHOOSE_TEST_DRAW"]
    opposing.deck = ["CHOOSE_TEST_DRAW"]
    own.hand = [HandCard(190_000, card_id)]
    opposing.hand = []
    own.board = []
    opposing.board = []
    target = None

    if card_id == "CORE_EX1_154":
        opposing.board = [Minion(190_010, "CHOOSE_TEST_MINION", 2, 4, 4, summoned_turn=0)]
        target = TargetRef.minion(enemy, 190_010)
    elif card_id == "CORE_EX1_160":
        own.board = [Minion(190_020, "CHOOSE_TEST_MINION", 2, 4, 4, summoned_turn=0)]

    action = Action(
        ActionType.PLAY,
        190_000,
        target,
        choice=contract.scenario_choice,
    )
    before = review_state_from_observation(game.observation(owner))
    game.apply(action)
    after = review_state_from_observation(game.observation(owner))
    return {
        "scenario_id": "{}-choose-one-review-v1".format(card_id.lower().replace("_", "-")),
        "title_zh": "{}：抉择分支核验".format(contract.name_zh),
        "purpose_zh": "核对所选分支的目标要求和效果，并确保未选分支不会同时结算。",
        "before": before,
        "action": {
            "type": action.action_type.value,
            "actor_player_id": owner,
            "source_entity_id": 190_000,
            "card_id": card_id,
            "target": action.to_dict()["target"],
            "description_zh": "选择《{}》的第{}个抉择分支。".format(
                contract.name_zh, contract.scenario_choice + 1
            ),
            "engine_action": action.to_dict(),
        },
        "after": after,
        "assertions": [
            {
                "assertion_id": "choose-one-outcome",
                "subject_zh": "所选抉择分支影响的英雄、手牌、牌库与场面",
                "before": _focus(before),
                "after": _focus(after),
                "expected_zh": contract.expected_zh,
            }
        ],
        "special_cases": [
            {
                "kind": "special_tags",
                "summary_zh": "抉择编号和未选分支单独记录。",
                "details": {
                    "entity_id": 190_000,
                    "card_id": card_id,
                    "tags_before": {"selected_choice": contract.scenario_choice},
                    "tags_after": {"only_selected_choice_resolved": True},
                    "explanation_zh": contract.expected_zh,
                },
            }
        ],
    }


__all__ = [
    "AUTHORING_METADATA",
    "CARDS",
    "CONTRACTS",
    "SCENARIO_CARD_NAMES_ZH",
    "TOKEN_CARDS",
    "build_review_scenario",
]
