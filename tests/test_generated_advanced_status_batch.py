from __future__ import annotations

from dataclasses import asdict

import pytest

from cardlab.authoring.generated import runtime_registry
from cardlab.authoring.generated.advanced_status_batch import (
    AUTHORING_METADATA,
    CARDS,
    SCENARIO_CARD_NAMES_ZH,
    build_review_scenario,
)
from cardlab.authoring.generated.runner import (
    CARD_METADATA,
    CARD_MODULES,
    SCENARIO_BUILDERS,
    SCENARIO_CARD_NAME_CATALOGS,
)
from cardlab.authoring.review_format import (
    REVIEW_SCHEMA_VERSION,
    render_review_document_zh,
    validate_review_document,
)
from cardlab.engine import Game
from cardlab.model import Action, ActionType, HandCard, Minion, TargetRef

EXPECTED_CARD_IDS = {
    "CORE_CS2_024",
    "CORE_CS2_028",
    "CORE_CS2_188",
    "CORE_UNG_205",
    "CORE_EX1_059",
}


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
            "card_module": "src/cardlab/authoring/generated/advanced_status_batch.py",
            "generator": metadata["generated_by"],
            "definition": asdict(CARDS[card_id]),
        },
        "scenario": build_review_scenario(card_id, runtime_registry([card_id])),
    }


def test_advanced_status_registration_is_complete() -> None:
    assert set(CARDS) == set(AUTHORING_METADATA) == EXPECTED_CARD_IDS
    for card_id in CARDS:
        assert CARD_MODULES[card_id].endswith("advanced_status_batch.py")
        assert CARD_METADATA[card_id] == AUTHORING_METADATA[card_id]
        assert card_id in SCENARIO_BUILDERS
        assert SCENARIO_CARD_NAME_CATALOGS[card_id] == SCENARIO_CARD_NAMES_ZH


@pytest.mark.parametrize("card_id", list(CARDS))
def test_each_card_has_a_valid_executable_chinese_review(card_id: str) -> None:
    document = _document(card_id)
    validate_review_document(document)
    scenario = document["scenario"]
    assert scenario["assertions"]
    assert scenario["special_cases"]
    rendered = render_review_document_zh(document, SCENARIO_CARD_NAMES_ZH)
    assert AUTHORING_METADATA[card_id]["name_zh"] in rendered
    assert "特殊情况" in rendered


def _freeze_game() -> tuple[Game, int, int]:
    game = Game(card_registry=runtime_registry(["CORE_CS2_024"]))
    actor = game.state.active_player
    enemy = 1 - actor
    own = game.state.players[actor]
    opposing = game.state.players[enemy]
    own.mana = own.max_mana = 10
    own.hand = [HandCard(98_000, "CORE_CS2_024")]
    own.board = [Minion(98_001, "CS2_182", 4, 5, 5, summoned_turn=0)]
    opposing.board = [Minion(98_002, "CS2_182", 4, 5, 5, summoned_turn=0)]
    return game, actor, enemy


def test_enemy_frozen_on_previous_turn_misses_attack_then_thaws() -> None:
    game, actor, enemy = _freeze_game()
    game.apply(Action(ActionType.PLAY, 98_000, TargetRef.minion(enemy, 98_002)))
    target = game.state.players[enemy].board[0]
    assert target.health == 2 and target.frozen is True

    game.apply(Action.end_turn())
    assert game.state.active_player == enemy
    assert all(
        action.source_id != 98_002 or action.action_type != ActionType.ATTACK
        for action in game.legal_actions()
    )
    game.apply(Action.end_turn())
    assert target.frozen is False


def test_freeze_after_attacking_persists_until_a_later_missed_attack() -> None:
    game, actor, enemy = _freeze_game()
    game.apply(Action(ActionType.ATTACK, 98_001, TargetRef.hero(enemy)))
    game.apply(Action(ActionType.PLAY, 98_000, TargetRef.minion(actor, 98_001)))
    own_minion = game.state.players[actor].board[0]
    game.apply(Action.end_turn())
    assert own_minion.frozen is True

    game.apply(Action.end_turn())
    assert game.state.active_player == actor
    assert all(
        action.source_id != 98_001 or action.action_type != ActionType.ATTACK
        for action in game.legal_actions()
    )
    game.apply(Action.end_turn())
    assert own_minion.frozen is False


def test_temporary_attack_expires_at_the_end_of_the_current_turn() -> None:
    game = Game(card_registry=runtime_registry(["CORE_CS2_188"]))
    actor = game.state.active_player
    enemy = 1 - actor
    own = game.state.players[actor]
    opposing = game.state.players[enemy]
    own.mana = own.max_mana = 10
    own.hand = [HandCard(98_100, "CORE_CS2_188")]
    opposing.board = [Minion(98_101, "CS2_182", 4, 5, 5, summoned_turn=0)]
    game.apply(Action(ActionType.PLAY, 98_100, TargetRef.minion(enemy, 98_101)))
    target = opposing.board[0]
    assert target.attack == 6
    assert target.temporary_attack == 2
    game.apply(Action.end_turn())
    assert target.attack == 4
    assert target.temporary_attack == 0


def test_stat_swap_uses_current_health_and_incorporates_temporary_attack() -> None:
    game = Game(
        card_registry=runtime_registry(["CORE_CS2_188", "CORE_EX1_059"])
    )
    actor = game.state.active_player
    own = game.state.players[actor]
    own.mana = own.max_mana = 10
    own.hand = [
        HandCard(98_200, "CORE_CS2_188"),
        HandCard(98_201, "CORE_EX1_059"),
    ]
    own.board = [Minion(98_202, "CS2_182", 4, 5, 5, summoned_turn=0)]
    target = TargetRef.minion(actor, 98_202)
    game.apply(Action(ActionType.PLAY, 98_200, target))
    assert (own.board[0].attack, own.board[0].health) == (6, 5)
    game.apply(Action(ActionType.PLAY, 98_201, target))
    swapped = own.board[0]
    assert (swapped.attack, swapped.health, swapped.max_health) == (5, 6, 6)
    assert swapped.temporary_attack == 0
    game.apply(Action.end_turn())
    assert (swapped.attack, swapped.health, swapped.max_health) == (5, 6, 6)


def test_swapping_zero_attack_to_health_destroys_the_target() -> None:
    game = Game(card_registry=runtime_registry(["CORE_EX1_059"]))
    actor = game.state.active_player
    enemy = 1 - actor
    own = game.state.players[actor]
    opposing = game.state.players[enemy]
    own.mana = own.max_mana = 10
    own.hand = [HandCard(98_300, "CORE_EX1_059")]
    opposing.board = [Minion(98_301, "CS2_182", 0, 4, 4, summoned_turn=0)]
    game.apply(
        Action(ActionType.PLAY, 98_300, TargetRef.minion(enemy, 98_301))
    )
    assert opposing.board == []
