from __future__ import annotations

from dataclasses import asdict

import pytest

from cardlab.authoring.generated import runtime_registry
from cardlab.authoring.generated.rune_location_batch import (
    AUTHORING_METADATA,
    BLOOD_POOL,
    CARDS,
    FROST_POOL,
    SCENARIO_CARD_NAMES_ZH,
    UNHOLY_POOL,
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
from cardlab.model import (
    Action,
    ActionType,
    CardDef,
    CardType,
    HandCard,
    Location,
    Minion,
    TargetRef,
)

EXPECTED_CARD_IDS = {
    "CORE_RLK_066",
    "CORE_RLK_116",
    "CORE_EDR_003",
    "RLK_025",
    "CORE_EX1_312",
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
            "card_module": "src/cardlab/authoring/generated/rune_location_batch.py",
            "generator": metadata["generated_by"],
            "definition": asdict(CARDS[card_id]),
        },
        "scenario": build_review_scenario(card_id, runtime_registry([card_id])),
    }


def _game(card_id: str, extra_ids: tuple[str, ...] = ()) -> tuple[Game, int, int]:
    game = Game(seed=41, card_registry=runtime_registry((card_id, *extra_ids)))
    actor = game.state.active_player
    enemy = 1 - actor
    own = game.state.players[actor]
    own.mana = own.max_mana = 10
    own.hand = [HandCard(122_000, card_id)]
    own.board = []
    game.state.players[enemy].board = []
    return game, actor, enemy


def test_rune_location_batch_registration_is_complete() -> None:
    assert set(CARDS) == set(AUTHORING_METADATA) == EXPECTED_CARD_IDS
    for card_id in CARDS:
        assert CARD_MODULES[card_id].endswith("rune_location_batch.py")
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


def test_hematurge_spends_a_corpse_then_exposes_three_blood_discover_actions() -> None:
    game, actor, enemy = _game("CORE_RLK_066")
    own = game.state.players[actor]
    own.corpses = 1
    game.apply(Action(ActionType.PLAY, 122_000))
    assert own.corpses == 0
    assert set(game.state.pending_discover_options) == set(BLOOD_POOL)
    legal = game.legal_actions()
    assert len(legal) == 3
    assert all(action.action_type == ActionType.DISCOVER for action in legal)
    assert game.observation(actor)["pending_discover"]["options"]
    assert game.observation(enemy)["pending_discover"]["options"] == []

    chosen = game.state.pending_discover_options[1]
    game.apply(Action(ActionType.DISCOVER, choice=1))
    assert [card.card_id for card in own.hand] == [chosen]
    assert game.state.pending_discover_player is None


def test_hematurge_without_a_corpse_does_not_open_discover() -> None:
    game, actor, _ = _game("CORE_RLK_066")
    game.apply(Action(ActionType.PLAY, 122_000))
    assert game.state.players[actor].corpses == 0
    assert game.state.pending_discover_player is None


@pytest.mark.parametrize(("target_health", "should_discover"), [(3, True), (4, False)])
def test_frost_strike_discovers_only_when_the_damaged_minion_dies(
    target_health: int, should_discover: bool
) -> None:
    game, _, enemy = _game("RLK_025")
    opposing = game.state.players[enemy]
    opposing.board = [
        Minion(122_010, "CS2_120", 2, target_health, 4, summoned_turn=0)
    ]
    game.apply(Action(ActionType.PLAY, 122_000, TargetRef.minion(enemy, 122_010)))
    assert (game.state.pending_discover_player is not None) is should_discover
    if should_discover:
        assert len(game.state.pending_discover_options) == 3
        assert set(game.state.pending_discover_options) <= set(FROST_POOL)


def test_necrotic_mortician_uses_and_resets_the_since_last_turn_history_flag() -> None:
    game, actor, _ = _game("CORE_RLK_116")
    own = game.state.players[actor]
    own.friendly_undead_died_since_last_turn = True
    game.apply(Action(ActionType.PLAY, 122_000))
    assert len(game.state.pending_discover_options) == 3
    assert set(game.state.pending_discover_options) <= set(UNHOLY_POOL)

    game.apply(Action(ActionType.DISCOVER, choice=0))
    game.apply(Action.end_turn())
    assert own.friendly_undead_died_since_last_turn is False


def test_falric_draws_a_card_marked_as_spending_corpses() -> None:
    game, actor, _ = _game("CORE_EDR_003")
    own = game.state.players[actor]
    own.deck = ["CS2_120", "CORE_RLK_712"]
    game.apply(Action(ActionType.PLAY, 122_000))
    assert [card.card_id for card in own.hand] == ["CORE_RLK_712"]
    assert own.deck == ["CS2_120"]


def test_falric_doubles_direct_and_death_generated_corpses_while_alive() -> None:
    game, actor, _ = _game("CORE_EDR_003", ("RLK_503",))
    own = game.state.players[actor]
    own.board = [
        Minion(
            122_020,
            "CORE_EDR_003",
            2,
            4,
            4,
            races=("UNDEAD",),
            summoned_turn=0,
        )
    ]
    own.hand = [HandCard(122_021, "RLK_503")]
    game.apply(Action(ActionType.PLAY, 122_021))
    assert own.corpses == 2

    own.board.append(Minion(122_022, "CS2_120", 2, 1, 3, summoned_turn=0))
    game.apply(Action(ActionType.HERO_POWER, target=TargetRef.minion(actor, 122_022)))
    assert own.corpses == 4


def test_twisting_nether_destroys_both_players_minions_and_locations() -> None:
    game, actor, enemy = _game("CORE_EX1_312")
    own = game.state.players[actor]
    opposing = game.state.players[enemy]
    own.board = [Minion(122_030, "CS2_120", 2, 3, 3, summoned_turn=0)]
    opposing.board = [Minion(122_031, "CS2_120", 2, 3, 3, summoned_turn=0)]
    own.locations = [Location(122_032, "CORE_REV_990", 3)]
    opposing.locations = [Location(122_033, "CORE_REV_990", 2)]
    game.apply(Action(ActionType.PLAY, 122_000))
    assert own.board == [] and opposing.board == []
    assert own.locations == [] and opposing.locations == []
    assert own.graveyard == ["CS2_120"]
    assert opposing.graveyard == ["CS2_120"]


def test_location_cards_share_the_seven_slot_play_limit_with_minions() -> None:
    location = CardDef(
        "TEST_LOCATION",
        "测试地标",
        CardType.LOCATION,
        1,
        durability=3,
        collectible=False,
    )
    registry = runtime_registry([])
    registry[location.card_id] = location
    game = Game(card_registry=registry)
    actor = game.state.active_player
    own = game.state.players[actor]
    own.mana = own.max_mana = 10
    own.board = [
        Minion(122_100 + index, "CS2_120", 2, 3, 3, summoned_turn=0)
        for index in range(6)
    ]
    own.hand = [HandCard(122_110, location.card_id)]
    game.apply(Action(ActionType.PLAY, 122_110))
    assert len(own.board) + len(own.locations) == 7

    own.hand = [HandCard(122_111, location.card_id)]
    assert all(
        not (action.action_type == ActionType.PLAY and action.source_id == 122_111)
        for action in game.legal_actions()
    )
