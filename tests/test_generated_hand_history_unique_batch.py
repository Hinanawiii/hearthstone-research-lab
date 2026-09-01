from __future__ import annotations

from dataclasses import asdict

import pytest

from cardlab.authoring.generated import runtime_registry
from cardlab.authoring.generated.hand_history_unique_batch import (
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
    "CORE_WON_141",
    "CORE_REV_946",
    "CORE_CFM_670",
    "CORE_TRL_345",
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
            "card_module": "src/cardlab/authoring/generated/hand_history_unique_batch.py",
            "generator": metadata["generated_by"],
            "definition": asdict(CARDS[card_id]),
        },
        "scenario": build_review_scenario(card_id, runtime_registry([card_id])),
    }


def _game(card_id: str) -> tuple[Game, int, int]:
    game = Game(seed=53, card_registry=runtime_registry([card_id]))
    actor = game.state.active_player
    enemy = 1 - actor
    own = game.state.players[actor]
    own.mana = own.max_mana = 10
    own.hand = []
    own.board = []
    game.state.players[enemy].board = []
    return game, actor, enemy


def test_hand_history_unique_batch_registration_is_complete() -> None:
    assert set(CARDS) == set(AUTHORING_METADATA) == EXPECTED_CARD_IDS
    for card_id in CARDS:
        assert CARD_MODULES[card_id].endswith("hand_history_unique_batch.py")
        assert CARD_METADATA[card_id] == AUTHORING_METADATA[card_id]
        assert card_id in SCENARIO_BUILDERS
        assert SCENARIO_CARD_NAME_CATALOGS[card_id] == SCENARIO_CARD_NAMES_ZH


@pytest.mark.parametrize("card_id", list(CARDS))
def test_each_card_has_a_valid_executable_chinese_review(card_id: str) -> None:
    document = _document(card_id)
    validate_review_document(document)
    rendered = render_review_document_zh(document, SCENARIO_CARD_NAMES_ZH)
    assert AUTHORING_METADATA[card_id]["name_zh"] in rendered
    assert document["scenario"]["assertions"]


def test_teacup_buffs_at_most_one_minion_from_each_type() -> None:
    game, actor, _ = _game("CORE_WON_141")
    own = game.state.players[actor]
    own.hand = [HandCard(180_000, "CORE_WON_141")]
    own.board = [
        Minion(180_001, "CS2_120", 2, 3, 3, races=("BEAST",), summoned_turn=0),
        Minion(180_002, "CORE_NEW1_022", 3, 3, 3, races=("PIRATE",), summoned_turn=0),
        Minion(180_003, "CORE_GVG_085", 1, 2, 2, races=("MECHANICAL",), summoned_turn=0),
    ]
    game.apply(Action(ActionType.PLAY, 180_000))
    assert [(m.attack, m.health) for m in own.board[:-1]] == [(3, 4), (4, 4), (2, 3)]


def test_steamcleaner_removes_only_outside_starting_deck_instances() -> None:
    game, actor, enemy = _game("CORE_REV_946")
    own = game.state.players[actor]
    opposing = game.state.players[enemy]
    own.hand = [HandCard(180_010, "CORE_REV_946")]
    own.deck = ["CS2_120", "CS2_029"]
    own.deck_outside_starting = [False, True]
    opposing.deck = ["CS2_120", "CS2_023"]
    opposing.deck_outside_starting = [False, True]
    game.apply(Action(ActionType.PLAY, 180_010))
    assert own.deck == opposing.deck == ["CS2_120"]
    assert own.deck_outside_starting == opposing.deck_outside_starting == [False]


def test_shuffled_cards_keep_outside_starting_origin_when_drawn() -> None:
    game, actor, _ = _game("CORE_REV_946")
    own = game.state.players[actor]
    own.deck = ["CS2_120", "CS2_029"]
    own.deck_outside_starting = [False, True]
    game._draw(actor)
    assert own.hand[-1].card_id == "CS2_029"
    assert own.hand[-1].outside_starting_deck is True


def test_mayor_rewrites_target_and_records_the_resolved_target() -> None:
    game, actor, enemy = _game("CORE_CFM_670")
    own = game.state.players[actor]
    own.board = [Minion(180_020, "CORE_CFM_670", 5, 4, 4, summoned_turn=0)]
    own.hand = [HandCard(180_021, "CS2_029")]
    declared = TargetRef.hero(enemy)
    game.apply(Action(ActionType.PLAY, 180_021, declared))
    resolved = game.history[-1]["action"]["target"]
    assert resolved in [
        asdict(TargetRef.hero(actor)),
        asdict(TargetRef.hero(enemy)),
        asdict(TargetRef.minion(actor, 180_020)),
    ]


def test_kragwa_returns_previous_turn_spells_and_turn_history_rolls_per_player() -> None:
    game, actor, _ = _game("CORE_TRL_345")
    own = game.state.players[actor]
    own.spells_played_this_turn = ["CS2_029", "CS2_023"]
    game.apply(Action.end_turn())
    assert own.spells_played_previous_turn == ["CS2_029", "CS2_023"]
    assert own.spells_played_this_turn == []

    game.apply(Action.end_turn())
    own.mana = own.max_mana = 10
    own.hand = [HandCard(180_030, "CORE_TRL_345")]
    game.apply(Action(ActionType.PLAY, 180_030))
    assert [card.card_id for card in own.hand] == ["CS2_029", "CS2_023"]
