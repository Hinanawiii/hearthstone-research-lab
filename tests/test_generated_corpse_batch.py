from __future__ import annotations

from dataclasses import asdict

import pytest

from cardlab.authoring.generated import runtime_registry
from cardlab.authoring.generated.corpse_batch import (
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
    "RLK_503",
    "CORE_RLK_712",
    "RLK_707",
    "RLK_060",
    "CORE_RLK_118",
    "CORE_RLK_506",
    "CORE_RLK_505",
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
            "card_module": "src/cardlab/authoring/generated/corpse_batch.py",
            "generator": metadata["generated_by"],
            "definition": asdict(CARDS[card_id]),
        },
        "scenario": build_review_scenario(card_id, runtime_registry([card_id])),
    }


def _game(card_id: str, corpses: int = 0) -> tuple[Game, int, int]:
    game = Game(seed=17, card_registry=runtime_registry([card_id]))
    actor = game.state.active_player
    enemy = 1 - actor
    own = game.state.players[actor]
    own.mana = own.max_mana = 10
    own.corpses = corpses
    own.hand = [HandCard(114_000, card_id)]
    own.board = []
    game.state.players[enemy].board = []
    return game, actor, enemy


def test_corpse_batch_registration_is_complete() -> None:
    assert set(CARDS) == set(AUTHORING_METADATA) == EXPECTED_CARD_IDS
    assert set(TOKEN_CARDS) <= set(runtime_registry([]))
    for card_id in CARDS:
        assert CARD_MODULES[card_id].endswith("corpse_batch.py")
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
    assert "残骸" in rendered


def test_body_bagger_gains_one_corpse_on_battlecry() -> None:
    game, actor, _ = _game("RLK_503")
    game.apply(Action(ActionType.PLAY, 114_000))
    assert game.state.players[actor].corpses == 1


def test_normal_minion_death_leaves_a_corpse_but_excluded_token_does_not() -> None:
    game, actor, _ = _game("RLK_060")
    own = game.state.players[actor]
    own.hand = []
    own.board = [Minion(114_010, "CS2_120", 2, 1, 3, summoned_turn=0)]
    game.apply(Action(ActionType.HERO_POWER, target=TargetRef.minion(actor, 114_010)))
    assert own.corpses == 1

    own.hero_power_used = False
    own.board = [
        Minion(
            114_011,
            "RLK_008t",
            2,
            1,
            2,
            rush=True,
            races=("UNDEAD",),
            summoned_turn=0,
        )
    ]
    game.apply(Action(ActionType.HERO_POWER, target=TargetRef.minion(actor, 114_011)))
    assert own.corpses == 1


@pytest.mark.parametrize(
    ("corpses", "expected_bonus", "remaining"),
    [(1, 1, 1), (2, 2, 0)],
)
def test_vitality_tap_only_applies_the_second_hand_buff_when_paid(
    corpses: int, expected_bonus: int, remaining: int
) -> None:
    game, actor, _ = _game("CORE_RLK_712", corpses)
    own = game.state.players[actor]
    own.hand.extend([HandCard(114_020, "CS2_120"), HandCard(114_021, "CS2_182")])
    game.apply(Action(ActionType.PLAY, 114_000))
    assert [(card.attack_bonus, card.health_bonus) for card in own.hand] == [
        (expected_bonus, expected_bonus),
        (expected_bonus, expected_bonus),
    ]
    assert own.corpses == remaining


@pytest.mark.parametrize(
    ("corpses", "expected_attack", "remaining"),
    [(4, 3, 4), (5, 5, 0)],
)
def test_grave_strength_replaces_plus_one_with_plus_three_when_paid(
    corpses: int, expected_attack: int, remaining: int
) -> None:
    game, actor, _ = _game("RLK_707", corpses)
    own = game.state.players[actor]
    own.board = [Minion(114_030, "CS2_120", 2, 3, 3, summoned_turn=0)]
    game.apply(Action(ActionType.PLAY, 114_000))
    assert own.board[0].attack == expected_attack
    assert own.corpses == remaining


def test_army_of_the_dead_spends_only_for_successful_summons() -> None:
    game, actor, _ = _game("RLK_060", 3)
    own = game.state.players[actor]
    own.board = [
        Minion(114_100 + index, "CS2_120", 2, 3, 3, summoned_turn=0)
        for index in range(6)
    ]
    game.apply(Action(ActionType.PLAY, 114_000))
    ghouls = [minion for minion in own.board if minion.card_id == "RLK_008t"]
    assert len(ghouls) == 1
    assert ghouls[0].rush is True
    assert own.corpses == 2


def test_graveyard_shift_grants_reborn_only_when_four_corpses_are_available() -> None:
    for corpses, expected_reborn, remaining in [(3, False, 3), (4, True, 0)]:
        game, actor, _ = _game("CORE_RLK_118", corpses)
        own = game.state.players[actor]
        game.apply(Action(ActionType.PLAY, 114_000))
        zombies = [minion for minion in own.board if minion.card_id == "RLK_118t3"]
        assert len(zombies) == 2
        assert all(minion.taunt and minion.reborn is expected_reborn for minion in zombies)
        assert own.corpses == remaining


def test_graveyard_shift_does_not_spend_corpses_when_no_zombie_can_be_summoned() -> None:
    game, actor, _ = _game("CORE_RLK_118", 4)
    own = game.state.players[actor]
    own.board = [
        Minion(114_200 + index, "CS2_120", 2, 3, 3, summoned_turn=0)
        for index in range(7)
    ]
    game.apply(Action(ActionType.PLAY, 114_000))
    assert own.corpses == 4


def test_boneshredder_commander_summons_six_corpseless_taunts() -> None:
    game, actor, _ = _game("CORE_RLK_506", 6)
    own = game.state.players[actor]
    game.apply(Action(ActionType.PLAY, 114_000))
    infantry = [minion for minion in own.board if minion.card_id == "RLK_061t"]
    assert len(infantry) == 6
    assert all(minion.taunt and minion.health == 3 for minion in infantry)
    assert own.corpses == 0


def test_marrow_manipulator_spends_up_to_five_for_separate_damage_hits() -> None:
    game, actor, enemy = _game("CORE_RLK_505", 7)
    opposing = game.state.players[enemy]
    game.apply(Action(ActionType.PLAY, 114_000))
    assert game.state.players[actor].corpses == 2
    assert opposing.hero_health == 20
