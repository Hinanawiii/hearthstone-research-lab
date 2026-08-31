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
from cardlab.authoring.generated.tribe_poison_batch import (
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

EXPECTED_CARD_IDS = {"RLK_958", "CORE_EDR_002"}


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
            "card_module": "src/cardlab/authoring/generated/tribe_poison_batch.py",
            "generator": metadata["generated_by"],
            "definition": asdict(CARDS[card_id]),
        },
        "scenario": build_review_scenario(card_id, runtime_registry([card_id])),
    }


def test_tribe_poison_batch_registration_is_complete() -> None:
    assert set(CARDS) == set(AUTHORING_METADATA) == EXPECTED_CARD_IDS
    for card_id in CARDS:
        assert CARD_MODULES[card_id].endswith("tribe_poison_batch.py")
        assert CARD_METADATA[card_id] == AUTHORING_METADATA[card_id]
        assert card_id in SCENARIO_BUILDERS
        assert SCENARIO_CARD_NAME_CATALOGS[card_id] == SCENARIO_CARD_NAMES_ZH


@pytest.mark.parametrize("card_id", list(CARDS))
def test_each_card_has_a_valid_executable_chinese_review(card_id: str) -> None:
    document = _document(card_id)
    validate_review_document(document)
    rendered = render_review_document_zh(document, SCENARIO_CARD_NAMES_ZH)
    assert AUTHORING_METADATA[card_id]["name_zh"] in rendered
    assert "种族：亡灵" in rendered
    assert "非亡灵淡水鳄不可选" in rendered


def _poison_combat_game(*, defender_has_shield: bool) -> tuple[Game, int, int]:
    game = Game(card_registry=runtime_registry(["CORE_EDR_002"]))
    actor = game.state.active_player
    enemy = 1 - actor
    own = game.state.players[actor]
    opposing = game.state.players[enemy]
    own.mana = 10
    own.hand = [HandCard(96_000, "CORE_EDR_002")]
    own.board = [
        Minion(
            96_001,
            "RLK_503",
            1,
            3,
            3,
            summoned_turn=0,
            races=("UNDEAD",),
        ),
        Minion(96_002, "CS2_120", 2, 3, 3, summoned_turn=0),
    ]
    opposing.board = [
        Minion(
            96_003,
            "CS2_182",
            4,
            5,
            5,
            summoned_turn=0,
            divine_shield=defender_has_shield,
        )
    ]
    return game, actor, enemy


def test_only_friendly_undead_is_legal_and_poison_destroys_damaged_minion() -> None:
    game, actor, enemy = _poison_combat_game(defender_has_shield=False)
    play_actions = [
        action
        for action in game.legal_actions()
        if action.action_type == ActionType.PLAY and action.source_id == 96_000
    ]
    assert [action.target for action in play_actions] == [TargetRef.minion(actor, 96_001)]

    game.apply(play_actions[0])
    assert game.state.players[actor].board[0].poisonous is True
    game.apply(Action(ActionType.ATTACK, 96_001, TargetRef.minion(enemy, 96_003)))
    assert [minion.entity_id for minion in game.state.players[actor].board] == [96_002]
    assert game.state.players[enemy].board == []


def test_divine_shield_prevents_damage_and_therefore_poisonous_destruction() -> None:
    game, actor, enemy = _poison_combat_game(defender_has_shield=True)
    game.apply(Action(ActionType.PLAY, 96_000, TargetRef.minion(actor, 96_001)))
    game.apply(Action(ActionType.ATTACK, 96_001, TargetRef.minion(enemy, 96_003)))
    defender = game.state.players[enemy].board[0]
    assert defender.entity_id == 96_003
    assert defender.health == 5
    assert defender.divine_shield is False
    assert all(minion.entity_id != 96_001 for minion in game.state.players[actor].board)
