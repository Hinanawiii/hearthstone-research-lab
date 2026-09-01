from __future__ import annotations

from dataclasses import asdict

import pytest

from cardlab.authoring.generated import generated_dependencies, runtime_registry
from cardlab.authoring.generated.death_history_batch import (
    AUTHORING_METADATA,
    CARDS,
    SCENARIO_CARD_NAMES_ZH,
    TOKEN_CARDS,
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
    "CORE_SW_439",
    "CORE_BT_201",
    "CORE_YOD_026",
    "CORE_UNG_952",
    "CORE_CATA_002",
    "CORE_GVG_114",
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
            "card_module": "src/cardlab/authoring/generated/death_history_batch.py",
            "generator": metadata["generated_by"],
            "definition": asdict(CARDS[card_id]),
        },
        "scenario": build_review_scenario(card_id, runtime_registry([card_id])),
    }


def _game(card_id: str) -> tuple[Game, int, int]:
    game = Game(seed=37, card_registry=runtime_registry([card_id]))
    actor = game.state.active_player
    enemy = 1 - actor
    own = game.state.players[actor]
    own.mana = own.max_mana = 10
    own.hand = []
    own.board = []
    game.state.players[enemy].board = []
    return game, actor, enemy


def test_death_history_batch_registration_is_complete() -> None:
    assert set(CARDS) == set(AUTHORING_METADATA) == EXPECTED_CARD_IDS
    assert set(TOKEN_CARDS) <= set(runtime_registry([]))
    assert set(generated_dependencies("CORE_SW_439")) == {"SW_439t", "SW_439t2"}
    for card_id in CARDS:
        assert CARD_MODULES[card_id].endswith("death_history_batch.py")
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


def test_vibrant_squirrel_shuffles_four_acorns_on_death() -> None:
    game, actor, _ = _game("CORE_SW_439")
    own = game.state.players[actor]
    own.deck = ["CS2_120"]
    own.board = [Minion(120_000, "CORE_SW_439", 2, 1, 1, summoned_turn=0)]
    game.apply(Action(ActionType.HERO_POWER, target=TargetRef.minion(actor, 120_000)))
    assert own.graveyard == ["CORE_SW_439"]
    assert own.deck.count("SW_439t") == 4
    assert len(own.deck) == 5


def test_drawing_an_acorn_casts_it_summons_a_squirrel_and_draws_replacement() -> None:
    game, actor, _ = _game("CORE_SW_439")
    own = game.state.players[actor]
    own.deck = ["CS2_120", "SW_439t"]
    game._draw(actor)
    assert [minion.card_id for minion in own.board] == ["SW_439t2"]
    assert [card.card_id for card in own.hand] == ["CS2_120"]
    assert own.deck == []


def test_augmented_porcupine_uses_its_attack_at_death_as_one_damage_hits() -> None:
    game, actor, enemy = _game("CORE_BT_201")
    own = game.state.players[actor]
    opposing = game.state.players[enemy]
    own.board = [
        Minion(
            120_010,
            "CORE_BT_201",
            5,
            1,
            4,
            races=("MECHANICAL", "BEAST"),
            summoned_turn=0,
        )
    ]
    opposing.board = []
    game.apply(Action(ActionType.HERO_POWER, target=TargetRef.minion(actor, 120_010)))
    assert opposing.hero_health == 25


def test_evil_conscript_uses_its_attack_at_death_for_the_random_buff() -> None:
    game, actor, _ = _game("CORE_YOD_026")
    own = game.state.players[actor]
    own.board = [
        Minion(120_020, "CORE_YOD_026", 5, 1, 1, races=("DEMON",), summoned_turn=0),
        Minion(120_021, "CS2_120", 2, 3, 3, summoned_turn=0),
    ]
    game.apply(Action(ActionType.HERO_POWER, target=TargetRef.minion(actor, 120_020)))
    assert [(minion.card_id, minion.attack) for minion in own.board] == [("CS2_120", 7)]


def test_spikeridged_steed_attaches_a_deathrattle_to_the_target_instance() -> None:
    game, actor, _ = _game("CORE_UNG_952")
    own = game.state.players[actor]
    own.hand = [HandCard(120_030, "CORE_UNG_952")]
    own.board = [Minion(120_031, "CS2_120", 2, 3, 3, summoned_turn=0)]
    game.apply(Action(ActionType.PLAY, 120_030, TargetRef.minion(actor, 120_031)))
    target = own.board[0]
    assert (target.attack, target.health, target.max_health, target.taunt) == (4, 9, 9, True)
    assert target.attached_deathrattle_effects[0].card_id == "UNG_810"

    target.health = 1
    game.apply(Action(ActionType.HERO_POWER, target=TargetRef.minion(actor, 120_031)))
    assert [(minion.card_id, minion.attack, minion.health, minion.taunt) for minion in own.board] == [
        ("UNG_810", 2, 6, True)
    ]


def test_calia_resurrects_a_highest_cost_friendly_minion_from_history() -> None:
    game, actor, _ = _game("CORE_CATA_002")
    own = game.state.players[actor]
    own.hand = [HandCard(120_040, "CORE_CATA_002")]
    own.graveyard = ["CS2_120", "CS2_200"]
    game.apply(Action(ActionType.PLAY, 120_040))
    assert [minion.card_id for minion in own.board] == ["CORE_CATA_002", "CS2_200"]
    assert own.graveyard == ["CS2_120", "CS2_200"]


def test_sneeds_deathrattle_summons_from_the_registered_legendary_pool() -> None:
    game, actor, _ = _game("CORE_GVG_114")
    own = game.state.players[actor]
    own.board = [
        Minion(
            120_050,
            "CORE_GVG_114",
            5,
            1,
            7,
            races=("MECHANICAL",),
            summoned_turn=0,
        )
    ]
    game.apply(Action(ActionType.HERO_POWER, target=TargetRef.minion(actor, 120_050)))
    assert len(own.board) == 1
    result = game.cards[own.board[0].card_id]
    assert result.rarity == "LEGENDARY" and result.collectible
