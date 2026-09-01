from __future__ import annotations

from dataclasses import asdict

import pytest

from cardlab.authoring.generated import runtime_registry
from cardlab.authoring.generated.discovery_generation_batch import (
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
    "CORE_CATA_009",
    "CORE_BT_321",
    "CORE_UNG_912",
    "CORE_DS1_184",
    "CORE_EDR_001",
    "CORE_BAR_541",
    "CORE_EX1_189",
    "CORE_KAR_062",
    "CORE_LOE_039",
    "Core_UNG_072",
    "CORE_ONY_022",
    "CORE_KAR_057",
    "CORE_KAR_069",
    "CORE_TID_931",
    "CORE_GIL_531",
    "CORE_DRG_024",
    "CORE_WON_350",
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
            "card_module": "src/cardlab/authoring/generated/discovery_generation_batch.py",
            "generator": metadata["generated_by"],
            "definition": asdict(CARDS[card_id]),
        },
        "scenario": build_review_scenario(card_id, runtime_registry([card_id])),
    }


def _game(card_id: str) -> tuple[Game, int, int]:
    game = Game(seed=47, card_registry=runtime_registry([card_id]))
    actor = game.state.active_player
    enemy = 1 - actor
    own = game.state.players[actor]
    own.mana = own.max_mana = 10
    own.hand = []
    own.board = []
    game.state.players[enemy].board = []
    return game, actor, enemy


def test_discovery_generation_batch_registration_is_complete() -> None:
    assert set(CARDS) == set(AUTHORING_METADATA) == EXPECTED_CARD_IDS
    for card_id in CARDS:
        assert CARD_MODULES[card_id].endswith("discovery_generation_batch.py")
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


def test_tracking_discovers_from_deck_and_removes_only_the_choice() -> None:
    game, actor, _ = _game("CORE_DS1_184")
    own = game.state.players[actor]
    own.hand = [HandCard(160_000, "CORE_DS1_184")]
    own.deck = ["CS2_029", "CS2_023", "EX1_277"]
    game.apply(Action(ActionType.PLAY, 160_000))
    chosen = game.state.pending_discover_options[0]
    game.apply(Action(ActionType.DISCOVER, choice=0))
    assert chosen not in own.deck
    assert [card.card_id for card in own.hand] == [chosen]
    assert len(own.deck) == 2


def test_historian_requires_a_dragon_in_hand_after_the_card_is_played() -> None:
    game, actor, _ = _game("CORE_KAR_062")
    own = game.state.players[actor]
    own.hand = [HandCard(160_010, "CORE_KAR_062")]
    game.apply(Action(ActionType.PLAY, 160_010))
    assert game.state.pending_discover_player is None

    game, actor, _ = _game("CORE_KAR_062")
    own = game.state.players[actor]
    own.hand = [
        HandCard(160_011, "CORE_KAR_062"),
        HandCard(160_012, "CORE_EX1_043"),
    ]
    game.apply(Action(ActionType.PLAY, 160_011))
    assert game.state.pending_discover_player == actor


def test_a3_requires_an_other_friendly_mech() -> None:
    game, actor, _ = _game("CORE_LOE_039")
    own = game.state.players[actor]
    own.hand = [HandCard(160_020, "CORE_LOE_039")]
    game.apply(Action(ActionType.PLAY, 160_020))
    assert game.state.pending_discover_player is None

    game, actor, _ = _game("CORE_LOE_039")
    own = game.state.players[actor]
    own.hand = [HandCard(160_021, "CORE_LOE_039")]
    own.board = [
        Minion(
            160_022,
            "CORE_GVG_085",
            1,
            2,
            2,
            races=("MECHANICAL",),
            summoned_turn=0,
        )
    ]
    game.apply(Action(ActionType.PLAY, 160_021))
    assert game.state.pending_discover_player == actor


def test_ivory_knight_heals_by_the_chosen_cards_printed_cost() -> None:
    game, actor, _ = _game("CORE_KAR_057")
    own = game.state.players[actor]
    own.hero_health = 20
    own.hand = [HandCard(160_030, "CORE_KAR_057")]
    game.apply(Action(ActionType.PLAY, 160_030))
    chosen = game.state.pending_discover_options[0]
    expected = min(30, 20 + game.cards[chosen].cost)
    game.apply(Action(ActionType.DISCOVER, choice=0))
    assert own.hero_health == expected


def test_dominance_buffs_the_discovered_hand_instance() -> None:
    game, actor, _ = _game("CORE_WON_350")
    own = game.state.players[actor]
    own.hand = [HandCard(160_040, "CORE_WON_350")]
    game.apply(Action(ActionType.PLAY, 160_040))
    chosen = game.state.pending_discover_options[0]
    game.apply(Action(ActionType.DISCOVER, choice=0))
    assert [(card.card_id, card.attack_bonus, card.health_bonus) for card in own.hand] == [
        (chosen, 1, 2)
    ]


@pytest.mark.parametrize("card_id", ["CORE_EDR_001", "CORE_TID_931"])
def test_two_card_generators_add_two_cards(card_id: str) -> None:
    game, actor, _ = _game(card_id)
    own = game.state.players[actor]
    own.hand = [HandCard(160_050, card_id)]
    game.apply(Action(ActionType.PLAY, 160_050))
    assert len(own.hand) == 2


def test_death_footsteps_freezes_before_exposing_discover_options() -> None:
    game, actor, enemy = _game("CORE_CATA_009")
    own = game.state.players[actor]
    own.hand = [HandCard(160_060, "CORE_CATA_009")]
    game.apply(Action(ActionType.PLAY, 160_060, TargetRef.hero(enemy)))
    assert game.state.players[enemy].hero_frozen is True
    assert game.state.pending_discover_player == actor
    assert game.observation(enemy)["pending_discover"]["options"] == []
