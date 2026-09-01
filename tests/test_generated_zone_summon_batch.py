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
from cardlab.authoring.generated.zone_summon_batch import (
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
from cardlab.model import Action, ActionType, HandCard, Minion

EXPECTED_CARD_IDS = {"CORE_CFM_790", "CORE_SCH_181", "CORE_DAL_575"}


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
            "card_module": "src/cardlab/authoring/generated/zone_summon_batch.py",
            "generator": metadata["generated_by"],
            "definition": asdict(CARDS[card_id]),
        },
        "scenario": build_review_scenario(card_id, runtime_registry([card_id])),
    }


def _game(card_id: str, extra_ids: tuple[str, ...] = ()) -> tuple[Game, int, int]:
    game = Game(seed=31, card_registry=runtime_registry((card_id, *extra_ids)))
    actor = game.state.active_player
    enemy = 1 - actor
    own = game.state.players[actor]
    own.mana = own.max_mana = 10
    own.hand = [HandCard(118_000, card_id)]
    own.board = []
    game.state.players[enemy].board = []
    return game, actor, enemy


def test_zone_summon_batch_registration_is_complete() -> None:
    assert set(CARDS) == set(AUTHORING_METADATA) == EXPECTED_CARD_IDS
    for card_id in CARDS:
        assert CARD_MODULES[card_id].endswith("zone_summon_batch.py")
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


def test_dirty_rat_summons_only_a_minion_and_preserves_hand_enchantments() -> None:
    game, actor, enemy = _game("CORE_CFM_790")
    opposing = game.state.players[enemy]
    opposing.hand = [
        HandCard(118_010, "CS2_120", attack_bonus=1, health_bonus=2),
        HandCard(118_011, "CS2_029"),
    ]
    game.apply(Action(ActionType.PLAY, 118_000))
    assert [(minion.card_id, minion.attack, minion.health) for minion in opposing.board] == [
        ("CS2_120", 3, 5)
    ]
    assert [card.card_id for card in opposing.hand] == ["CS2_029"]


def test_dirty_rat_does_not_trigger_the_summoned_minions_battlecry() -> None:
    game, _, enemy = _game("CORE_CFM_790")
    opposing = game.state.players[enemy]
    opposing.hand = [HandCard(118_020, "EX1_015")]
    opposing.deck = ["CS2_120"]
    game.apply(Action(ActionType.PLAY, 118_000))
    assert [minion.card_id for minion in opposing.board] == ["EX1_015"]
    assert opposing.hand == []
    assert opposing.deck == ["CS2_120"]


def test_dirty_rat_does_not_remove_a_card_when_the_opponents_board_is_full() -> None:
    game, _, enemy = _game("CORE_CFM_790")
    opposing = game.state.players[enemy]
    opposing.hand = [HandCard(118_030, "CS2_120")]
    opposing.board = [
        Minion(118_100 + index, "CS2_120", 2, 3, 3, summoned_turn=0)
        for index in range(7)
    ]
    game.apply(Action(ActionType.PLAY, 118_000))
    assert [card.card_id for card in opposing.hand] == ["CS2_120"]


def test_willow_summons_one_demon_from_hand_and_one_from_deck() -> None:
    game, actor, _ = _game("CORE_SCH_181")
    own = game.state.players[actor]
    own.hand.extend(
        [
            HandCard(118_040, "CS2_065", attack_bonus=2, health_bonus=1),
            HandCard(118_041, "CS2_029"),
        ]
    )
    own.deck = ["CS2_120", "CS2_065"]
    game.apply(Action(ActionType.PLAY, 118_000))
    assert [(minion.card_id, minion.attack, minion.health) for minion in own.board] == [
        ("CORE_SCH_181", 5, 5),
        ("CS2_065", 3, 4),
        ("CS2_065", 1, 3),
    ]
    assert [card.card_id for card in own.hand] == ["CS2_029"]
    assert own.deck == ["CS2_120"]


def test_khadgar_doubles_card_summons_but_not_overload() -> None:
    game, actor, _ = _game("CORE_DAL_575", ("CORE_BOT_451",))
    own = game.state.players[actor]
    own.board = [Minion(118_050, "CORE_DAL_575", 2, 2, 2, summoned_turn=0)]
    own.hand = [HandCard(118_051, "CORE_BOT_451")]
    game.apply(Action(ActionType.PLAY, 118_051))
    assert len([minion for minion in own.board if minion.card_id == "BOT_102t"]) == 4
    assert own.overload_pending == 1


def test_two_khadgars_multiply_the_summon_count_subject_to_board_space() -> None:
    game, actor, _ = _game("CORE_DAL_575", ("CORE_BOT_451",))
    own = game.state.players[actor]
    own.board = [
        Minion(118_060, "CORE_DAL_575", 2, 2, 2, summoned_turn=0),
        Minion(118_061, "CORE_DAL_575", 2, 2, 2, summoned_turn=0),
    ]
    own.hand = [HandCard(118_062, "CORE_BOT_451")]
    game.apply(Action(ActionType.PLAY, 118_062))
    assert len([minion for minion in own.board if minion.card_id == "BOT_102t"]) == 5
    assert len(own.board) == 7


def test_khadgar_doubles_corpse_summons_without_doubling_corpse_spend() -> None:
    game, actor, _ = _game("CORE_DAL_575", ("RLK_060",))
    own = game.state.players[actor]
    own.board = [Minion(118_070, "CORE_DAL_575", 2, 2, 2, summoned_turn=0)]
    own.hand = [HandCard(118_071, "RLK_060")]
    own.corpses = 2
    game.apply(Action(ActionType.PLAY, 118_071))
    assert len([minion for minion in own.board if minion.card_id == "RLK_008t"]) == 4
    assert own.corpses == 0
