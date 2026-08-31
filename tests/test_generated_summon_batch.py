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
from cardlab.authoring.generated.summon_batch import (
    AUTHORING_METADATA,
    CARDS,
    SCENARIO_CARD_NAMES_ZH,
    TOKEN_CARDS,
    build_review_scenario,
)
from cardlab.authoring.review_format import (
    REVIEW_SCHEMA_VERSION,
    render_review_document_zh,
    validate_review_document,
)
from cardlab.engine import Game
from cardlab.model import Action, ActionType, HandCard, Minion, TargetRef

EXPECTED_CARD_IDS = {
    "CORE_EX1_506",
    "CORE_BAR_801",
    "CORE_BOT_451",
    "CORE_SW_088",
    "CORE_RLK_062",
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
            "card_module": "src/cardlab/authoring/generated/summon_batch.py",
            "generator": metadata["generated_by"],
            "definition": asdict(CARDS[card_id]),
        },
        "scenario": build_review_scenario(card_id, runtime_registry([card_id])),
    }


def _game(card_id: str) -> tuple[Game, int, int]:
    game = Game(card_registry=runtime_registry([card_id]))
    actor = game.state.active_player
    enemy = 1 - actor
    own = game.state.players[actor]
    own.mana = own.max_mana = 10
    own.hand = [HandCard(104_000, card_id)]
    own.board = []
    game.state.players[enemy].board = []
    return game, actor, enemy


def test_summon_batch_registration_is_complete() -> None:
    assert set(CARDS) == set(AUTHORING_METADATA) == EXPECTED_CARD_IDS
    assert set(TOKEN_CARDS) <= set(runtime_registry([]))
    for card_id in CARDS:
        assert CARD_MODULES[card_id].endswith("summon_batch.py")
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
    assert "召唤" in rendered


def test_murloc_tidehunter_summons_a_separate_murloc_scout() -> None:
    game, actor, _ = _game("CORE_EX1_506")
    own = game.state.players[actor]
    game.apply(Action(ActionType.PLAY, 104_000))
    assert [(m.card_id, m.attack, m.health, m.races) for m in own.board] == [
        ("CORE_EX1_506", 2, 1, ("MURLOC",)),
        ("EX1_506a", 1, 1, ("MURLOC",)),
    ]
    assert own.board[0].entity_id != own.board[1].entity_id


def test_summon_respects_the_seven_minion_board_limit() -> None:
    game, actor, _ = _game("CORE_EX1_506")
    own = game.state.players[actor]
    own.board = [
        Minion(104_100 + index, "CS2_120", 2, 3, 3, summoned_turn=0)
        for index in range(6)
    ]
    game.apply(Action(ActionType.PLAY, 104_000))
    assert len(own.board) == 7
    assert all(minion.card_id != "EX1_506a" for minion in own.board)


def test_wound_prey_deals_damage_then_summons_a_rush_beast() -> None:
    game, actor, enemy = _game("CORE_BAR_801")
    own = game.state.players[actor]
    opposing = game.state.players[enemy]
    own.board = [Minion(104_200, "CS2_120", 2, 3, 3, summoned_turn=0)]
    opposing.board = [Minion(104_201, "CS2_182", 4, 5, 5, summoned_turn=0)]
    game.apply(Action(ActionType.PLAY, 104_000, TargetRef.hero(actor)))
    assert own.hero_health == 29
    hyena = next(minion for minion in own.board if minion.card_id == "BAR_035t")
    assert hyena.rush is True and hyena.races == ("BEAST",)
    rush_targets = [
        action.target
        for action in game.legal_actions()
        if action.action_type == ActionType.ATTACK and action.source_id == hyena.entity_id
    ]
    assert rush_targets == [TargetRef.minion(enemy, 104_201)]


def test_voltaic_burst_summons_two_sparks_and_records_overload() -> None:
    game, actor, _ = _game("CORE_BOT_451")
    own = game.state.players[actor]
    game.apply(Action(ActionType.PLAY, 104_000))
    sparks = [minion for minion in own.board if minion.card_id == "BOT_102t"]
    assert len(sparks) == 2
    assert all(minion.rush and minion.races == ("ELEMENTAL",) for minion in sparks)
    assert own.overload_pending == 1


def test_demonic_assault_can_damage_friendly_character_and_summon_two_taunts() -> None:
    game, actor, _ = _game("CORE_SW_088")
    own = game.state.players[actor]
    game.apply(Action(ActionType.PLAY, 104_000, TargetRef.hero(actor)))
    assert own.hero_health == 27
    voidwalkers = [minion for minion in own.board if minion.card_id == "CS2_065"]
    assert len(voidwalkers) == 2
    assert all(
        minion.taunt and minion.races == ("DEMON",) for minion in voidwalkers
    )


def test_swarmguard_summons_exactly_two_non_recursive_copies() -> None:
    game, actor, _ = _game("CORE_RLK_062")
    own = game.state.players[actor]
    game.apply(Action(ActionType.PLAY, 104_000))
    assert len(own.board) == 3
    assert all(
        (minion.card_id, minion.attack, minion.health, minion.taunt, minion.races)
        == ("CORE_RLK_062", 1, 3, True, ("UNDEAD",))
        for minion in own.board
    )
    assert len({minion.entity_id for minion in own.board}) == 3
