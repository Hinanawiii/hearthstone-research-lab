from __future__ import annotations

from dataclasses import asdict

import pytest

from cardlab.authoring.generated import runtime_registry
from cardlab.authoring.generated.runner import (
    CARD_METADATA,
    CARD_MODULES,
    SCENARIO_BUILDERS,
    SCENARIO_CARD_NAME_CATALOGS,
)
from cardlab.authoring.generated.weapon_batch import (
    AUTHORING_METADATA,
    CARDS,
    SCENARIO_CARD_NAMES_ZH,
    build_review_scenario,
)
from cardlab.authoring.review_format import (
    REVIEW_SCHEMA_VERSION,
    render_review_document_zh,
    validate_review_document,
)
from cardlab.engine import Game
from cardlab.model import Action, ActionType, HandCard, Minion, TargetRef

EXPECTED_CARD_IDS = {"RLK_067", "CORE_BT_921", "CORE_CS2_074"}


def _document(card_id: str) -> dict[str, object]:
    metadata = AUTHORING_METADATA[card_id]
    return {
        "schema_version": REVIEW_SCHEMA_VERSION,
        "locale": "zh-CN",
        "card": {
            "card_id": card_id,
            "name_zh": metadata["name_zh"],
            "source_text_zh": metadata["source_text_zh"],
            "source_version": metadata["source_version"],
        },
        "implementation": {
            "card_module": "src/cardlab/authoring/generated/weapon_batch.py",
            "generator": metadata["generated_by"],
            "definition": asdict(CARDS[card_id]),
        },
        "scenario": build_review_scenario(card_id, runtime_registry([card_id])),
    }


def test_weapon_batch_registration_is_complete() -> None:
    assert set(CARDS) == set(AUTHORING_METADATA) == EXPECTED_CARD_IDS
    for card_id in CARDS:
        assert CARD_MODULES[card_id].endswith("weapon_batch.py")
        assert CARD_METADATA[card_id] == AUTHORING_METADATA[card_id]
        assert card_id in SCENARIO_BUILDERS
        assert SCENARIO_CARD_NAME_CATALOGS[card_id] == SCENARIO_CARD_NAMES_ZH


@pytest.mark.parametrize("card_id", list(CARDS))
def test_each_weapon_card_has_a_valid_executable_chinese_review(card_id: str) -> None:
    document = _document(card_id)
    validate_review_document(document)
    rendered = render_review_document_zh(document, SCENARIO_CARD_NAMES_ZH)
    assert AUTHORING_METADATA[card_id]["name_zh"] in rendered
    assert "武器" in rendered
    assert "特殊情况" in rendered


def _warblades_game() -> tuple[Game, int, int]:
    game = Game(card_registry=runtime_registry(["CORE_BT_921"]))
    actor = game.state.active_player
    enemy = 1 - actor
    own = game.state.players[actor]
    opposing = game.state.players[enemy]
    own.hero_health = 20
    own.mana = own.max_mana = 10
    own.hand = [HandCard(100_000, "CORE_BT_921")]
    opposing.board = [Minion(100_001, "CS2_182", 4, 8, 8, summoned_turn=0)]
    return game, actor, enemy


def test_hero_attack_uses_weapon_lifesteal_and_consumes_durability() -> None:
    game, actor, enemy = _warblades_game()
    game.apply(Action(ActionType.PLAY, 100_000))
    weapon = game.state.players[actor].weapon
    assert weapon is not None
    game.apply(
        Action(
            ActionType.HERO_ATTACK,
            weapon.entity_id,
            TargetRef.minion(enemy, 100_001),
        )
    )
    assert game.state.players[actor].hero_health == 18
    assert game.state.players[enemy].board[0].health == 6
    assert weapon.durability == 1

    game.apply(Action.end_turn())
    game.apply(Action.end_turn())
    game.apply(
        Action(
            ActionType.HERO_ATTACK,
            weapon.entity_id,
            TargetRef.minion(enemy, 100_001),
        )
    )
    assert game.state.players[actor].weapon is None
    assert game.state.players[actor].hero_attack == 0


def test_hero_attack_obeys_taunt_and_freeze() -> None:
    game, actor, enemy = _warblades_game()
    opposing = game.state.players[enemy]
    opposing.board = [
        Minion(100_101, "CS2_120", 2, 3, 3, taunt=True, summoned_turn=0),
        Minion(100_102, "CS2_182", 4, 5, 5, summoned_turn=0),
    ]
    game.apply(Action(ActionType.PLAY, 100_000))
    weapon = game.state.players[actor].weapon
    assert weapon is not None
    hero_attacks = [
        action
        for action in game.legal_actions()
        if action.action_type == ActionType.HERO_ATTACK
    ]
    assert [action.target for action in hero_attacks] == [
        TargetRef.minion(enemy, 100_101)
    ]

    game.state.players[actor].hero_frozen = True
    assert all(
        action.action_type != ActionType.HERO_ATTACK for action in game.legal_actions()
    )
    game.apply(Action.end_turn())
    assert game.state.players[actor].hero_frozen is False


def test_deadly_poison_requires_and_only_buffs_the_current_weapon() -> None:
    game = Game(card_registry=runtime_registry(["CORE_CS2_074", "CORE_BT_921"]))
    actor = game.state.active_player
    own = game.state.players[actor]
    own.mana = own.max_mana = 10
    own.hand = [HandCard(100_200, "CORE_CS2_074")]
    assert all(action.source_id != 100_200 for action in game.legal_actions())

    own.hand.append(HandCard(100_201, "CORE_BT_921"))
    game.apply(Action(ActionType.PLAY, 100_201))
    game.apply(Action(ActionType.PLAY, 100_200))
    assert own.weapon is not None
    assert (own.weapon.attack, own.weapon.durability) == (4, 2)
    assert own.hero_attack == 4


def test_equipping_a_new_weapon_replaces_the_previous_weapon() -> None:
    game = Game(card_registry=runtime_registry(["CORE_BT_921", "RLK_067"]))
    actor = game.state.active_player
    own = game.state.players[actor]
    own.mana = own.max_mana = 10
    own.hand = [
        HandCard(100_300, "CORE_BT_921"),
        HandCard(100_301, "RLK_067"),
    ]
    game.apply(Action(ActionType.PLAY, 100_300))
    first_weapon = own.weapon
    assert first_weapon is not None
    game.apply(Action(ActionType.PLAY, 100_301))
    assert own.weapon is not None
    assert own.weapon.entity_id != first_weapon.entity_id
    assert (own.weapon.card_id, own.weapon.attack, own.weapon.durability) == (
        "RLK_067",
        5,
        2,
    )
