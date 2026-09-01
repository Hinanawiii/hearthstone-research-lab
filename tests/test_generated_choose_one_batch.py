from __future__ import annotations

from dataclasses import asdict

import pytest

from cardlab.authoring.generated import runtime_registry
from cardlab.authoring.generated.choose_one_batch import (
    AUTHORING_METADATA,
    CARDS,
    CONTRACTS,
    SCENARIO_CARD_NAMES_ZH,
    SUPPORT_CARDS,
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
    "CORE_AT_037",
    "CORE_EX1_154",
    "CORE_EX1_160",
    "CORE_OG_047",
    "CORE_TSC_650",
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
            "card_module": "src/cardlab/authoring/generated/choose_one_batch.py",
            "generator": metadata["generated_by"],
            "definition": asdict(CARDS[card_id]),
        },
        "scenario": build_review_scenario(card_id, runtime_registry([card_id])),
    }


def _game(card_id: str) -> tuple[Game, int, int]:
    registry = runtime_registry([card_id])
    registry.update(SUPPORT_CARDS)
    game = Game(card_registry=registry)
    actor = game.state.active_player
    enemy = 1 - actor
    own = game.state.players[actor]
    own.mana = own.max_mana = 10
    own.hand = [HandCard(200_000, card_id)]
    own.deck = ["CHOOSE_TEST_DRAW"]
    own.board = []
    game.state.players[enemy].board = []
    return game, actor, enemy


def test_choose_one_batch_registration_is_complete() -> None:
    assert set(CARDS) == set(CONTRACTS) == set(AUTHORING_METADATA) == EXPECTED_CARD_IDS
    assert set(TOKEN_CARDS) <= set(runtime_registry([]))
    for card_id in CARDS:
        assert CARD_MODULES[card_id].endswith("choose_one_batch.py")
        assert CARD_METADATA[card_id] == AUTHORING_METADATA[card_id]
        assert card_id in SCENARIO_BUILDERS
        assert SCENARIO_CARD_NAME_CATALOGS[card_id] == SCENARIO_CARD_NAMES_ZH


@pytest.mark.parametrize("card_id", list(CARDS))
def test_each_card_has_a_valid_executable_chinese_review(card_id: str) -> None:
    document = _document(card_id)
    validate_review_document(document)
    rendered = render_review_document_zh(document, SCENARIO_CARD_NAMES_ZH)
    assert AUTHORING_METADATA[card_id]["name_zh"] in rendered
    assert "操作前" in rendered and "操作后" in rendered


def test_living_roots_exposes_targeted_damage_and_untargeted_summon_choices() -> None:
    game, actor, enemy = _game("CORE_AT_037")
    opposing = game.state.players[enemy]
    damage = Action(ActionType.PLAY, 200_000, TargetRef.hero(enemy), choice=0)
    summon = Action(ActionType.PLAY, 200_000, choice=1)
    assert damage in game.legal_actions()
    assert summon in game.legal_actions()
    game.apply(damage)
    assert opposing.hero_health == 28
    assert game.state.players[actor].board == []

    game, actor, _ = _game("CORE_AT_037")
    game.apply(Action(ActionType.PLAY, 200_000, choice=1))
    assert [minion.card_id for minion in game.state.players[actor].board] == [
        "AT_037t",
        "AT_037t",
    ]


def test_wrath_resolves_only_the_selected_damage_draw_branch() -> None:
    game, actor, enemy = _game("CORE_EX1_154")
    target = Minion(200_010, "CHOOSE_TEST_MINION", 2, 4, 4, summoned_turn=0)
    game.state.players[enemy].board = [target]
    game.apply(
        Action(
            ActionType.PLAY,
            200_000,
            TargetRef.minion(enemy, 200_010),
            choice=1,
        )
    )
    assert target.health == 3
    assert len(game.state.players[actor].hand) == 1
    assert game.state.players[actor].deck == []


def test_power_of_the_wild_offers_buff_or_panther_but_not_both() -> None:
    game, actor, _ = _game("CORE_EX1_160")
    own = game.state.players[actor]
    own.board = [Minion(200_020, "CHOOSE_TEST_MINION", 2, 4, 4, summoned_turn=0)]
    game.apply(Action(ActionType.PLAY, 200_000, choice=0))
    assert [(minion.card_id, minion.attack, minion.health) for minion in own.board] == [
        ("CHOOSE_TEST_MINION", 3, 5)
    ]

    game, actor, _ = _game("CORE_EX1_160")
    game.apply(Action(ActionType.PLAY, 200_000, choice=1))
    assert [minion.card_id for minion in game.state.players[actor].board] == ["EX1_160t"]


def test_feral_rage_choice_separates_temporary_attack_and_armor() -> None:
    game, actor, _ = _game("CORE_OG_047")
    own = game.state.players[actor]
    game.apply(Action(ActionType.PLAY, 200_000, choice=0))
    assert own.hero_attack == 4
    assert own.hero_armor == 0

    game, actor, _ = _game("CORE_OG_047")
    own = game.state.players[actor]
    game.apply(Action(ActionType.PLAY, 200_000, choice=1))
    assert own.hero_attack == 0
    assert own.hero_armor == 8


def test_flipper_friends_respects_board_capacity_for_either_choice() -> None:
    game, actor, _ = _game("CORE_TSC_650")
    game.apply(Action(ActionType.PLAY, 200_000, choice=0))
    whale = game.state.players[actor].board[0]
    assert (whale.card_id, whale.attack, whale.health, whale.taunt) == (
        "TSC_650t",
        6,
        6,
        True,
    )

    game, actor, _ = _game("CORE_TSC_650")
    game.apply(Action(ActionType.PLAY, 200_000, choice=1))
    otters = game.state.players[actor].board
    assert len(otters) == 6
    assert all(minion.card_id == "TSC_650t4" and minion.rush for minion in otters)
