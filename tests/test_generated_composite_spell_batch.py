from __future__ import annotations

from dataclasses import asdict

import pytest

from cardlab.authoring.generated import runtime_registry
from cardlab.authoring.generated.composite_spell_batch import (
    AUTHORING_METADATA,
    CARDS,
    CONTRACTS,
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
    "CORE_BOT_222",
    "CORE_BRM_013",
    "CORE_BT_292",
    "CORE_CFM_604",
    "CORE_CS1_130",
    "CORE_CS2_004",
    "CORE_CS2_076",
    "CORE_CS2_094",
    "CORE_CS2_108",
    "CORE_EX1_129",
    "CORE_EX1_197",
    "CORE_EX1_278",
    "CORE_EX1_302",
    "CORE_EX1_309",
    "CORE_EX1_391",
    "CORE_EX1_606",
    "CORE_ICC_055",
    "CORE_SW_442",
    "CORE_TRL_307",
    "RLK_024",
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
            "card_module": "src/cardlab/authoring/generated/composite_spell_batch.py",
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
    opposing = game.state.players[enemy]
    own.hero_health = 15
    own.mana = own.max_mana = 10
    own.hand = [HandCard(109_000, card_id)]
    own.deck = ["CS2_120", "CS2_172"]
    own.board = [Minion(109_001, "CS2_120", 2, 1, 3, summoned_turn=0)]
    opposing.board = [
        Minion(109_002, "CS2_182", 4, 6, 6, summoned_turn=0),
        Minion(109_003, "CS2_231", 1, 1, 1, summoned_turn=0),
    ]
    return game, actor, enemy


def test_composite_spell_batch_registration_is_complete() -> None:
    assert set(CARDS) == set(CONTRACTS) == set(AUTHORING_METADATA) == EXPECTED_CARD_IDS
    for card_id in CARDS:
        assert CARD_MODULES[card_id].endswith("composite_spell_batch.py")
        assert CARD_METADATA[card_id] == AUTHORING_METADATA[card_id]
        assert card_id in SCENARIO_BUILDERS
        assert SCENARIO_CARD_NAME_CATALOGS[card_id] == SCENARIO_CARD_NAMES_ZH


@pytest.mark.parametrize("card_id", list(CARDS))
def test_each_card_has_a_valid_executable_chinese_review(card_id: str) -> None:
    document = _document(card_id)
    validate_review_document(document)
    scenario = document["scenario"]
    assert scenario["assertions"]
    rendered = render_review_document_zh(document, SCENARIO_CARD_NAMES_ZH)
    assert AUTHORING_METADATA[card_id]["name_zh"] in rendered
    assert "操作前" in rendered and "操作后" in rendered


def test_holy_smite_only_targets_minions() -> None:
    game, actor, enemy = _game("CORE_CS1_130")
    targets = [
        action.target
        for action in game.legal_actions()
        if action.action_type == ActionType.PLAY and action.source_id == 109_000
    ]
    assert TargetRef.hero(actor) not in targets
    assert TargetRef.hero(enemy) not in targets
    assert set(targets) == {
        TargetRef.minion(actor, 109_001),
        TargetRef.minion(enemy, 109_002),
        TargetRef.minion(enemy, 109_003),
    }


def test_greater_healing_potion_only_targets_friendly_characters() -> None:
    game, actor, enemy = _game("CORE_CFM_604")
    targets = [
        action.target
        for action in game.legal_actions()
        if action.action_type == ActionType.PLAY and action.source_id == 109_000
    ]
    assert targets == [TargetRef.hero(actor), TargetRef.minion(actor, 109_001)]
    assert TargetRef.hero(enemy) not in targets


def test_execute_only_targets_damaged_enemy_minions() -> None:
    game, _, enemy = _game("CORE_CS2_108")
    opposing = game.state.players[enemy]
    opposing.board[0].health = 5
    targets = [
        action.target
        for action in game.legal_actions()
        if action.action_type == ActionType.PLAY and action.source_id == 109_000
    ]
    assert targets == [TargetRef.minion(enemy, 109_002)]


@pytest.mark.parametrize(
    ("target_health", "expected_draws"),
    [(1, 1), (2, 0)],
)
def test_mortal_coil_draws_only_if_target_dies(target_health: int, expected_draws: int) -> None:
    game, actor, enemy = _game("CORE_EX1_302")
    own = game.state.players[actor]
    target = game.state.players[enemy].board[1]
    target.health = target.max_health = target_health
    game.apply(Action(ActionType.PLAY, 109_000, TargetRef.minion(enemy, target.entity_id)))
    assert len(own.hand) == expected_draws
    assert len(own.deck) == 2 - expected_draws


@pytest.mark.parametrize(
    ("target_health", "expected_draws"),
    [(3, 1), (2, 0)],
)
def test_slam_draws_only_if_target_survives(target_health: int, expected_draws: int) -> None:
    game, actor, enemy = _game("CORE_EX1_391")
    own = game.state.players[actor]
    target = game.state.players[enemy].board[0]
    target.health = target.max_health = target_health
    game.apply(Action(ActionType.PLAY, 109_000, TargetRef.minion(enemy, target.entity_id)))
    assert len(own.hand) == expected_draws
    assert len(own.deck) == 2 - expected_draws


@pytest.mark.parametrize("has_other_card", [False, True])
def test_quick_shot_checks_hand_after_the_spell_leaves_it(has_other_card: bool) -> None:
    game, actor, enemy = _game("CORE_BRM_013")
    own = game.state.players[actor]
    if has_other_card:
        own.hand.append(HandCard(109_010, "CS2_120"))
    game.apply(Action(ActionType.PLAY, 109_000, TargetRef.hero(enemy)))
    assert len(own.deck) == (2 if has_other_card else 1)
    assert [card.card_id for card in own.hand] == (["CS2_120"] if has_other_card else ["CS2_172"])


@pytest.mark.parametrize(
    ("card_id", "damage"),
    [("CORE_ICC_055", 3), ("RLK_024", 6)],
)
def test_minion_targeted_lifesteal_spells_heal_for_damage_dealt(card_id: str, damage: int) -> None:
    game, actor, enemy = _game(card_id)
    own = game.state.players[actor]
    game.apply(Action(ActionType.PLAY, 109_000, TargetRef.minion(enemy, 109_002)))
    assert own.hero_health == 15 + damage


def test_void_shard_can_target_a_hero_and_lifesteal() -> None:
    game, actor, enemy = _game("CORE_SW_442")
    own = game.state.players[actor]
    opposing = game.state.players[enemy]
    game.apply(Action(ActionType.PLAY, 109_000, TargetRef.hero(enemy)))
    assert own.hero_health == 19
    assert opposing.hero_health == 26


def test_spell_lifesteal_does_not_heal_when_divine_shield_prevents_damage() -> None:
    game, actor, enemy = _game("CORE_ICC_055")
    own = game.state.players[actor]
    target = game.state.players[enemy].board[0]
    target.divine_shield = True
    game.apply(Action(ActionType.PLAY, 109_000, TargetRef.minion(enemy, target.entity_id)))
    assert own.hero_health == 15
    assert target.health == 6 and target.divine_shield is False


def test_spirit_bomb_damages_target_and_owner_hero() -> None:
    game, actor, enemy = _game("CORE_BOT_222")
    own = game.state.players[actor]
    opposing = game.state.players[enemy]
    game.apply(Action(ActionType.PLAY, 109_000, TargetRef.minion(enemy, 109_002)))
    assert own.hero_health == 11
    assert opposing.board[0].health == 2


@pytest.mark.parametrize(
    ("card_id", "expected_attack", "expected_health", "expected_max_health"),
    [("CORE_CS2_004", 2, 3, 5), ("CORE_BT_292", 4, 2, 4)],
)
def test_buff_and_draw_spells_apply_both_steps(
    card_id: str,
    expected_attack: int,
    expected_health: int,
    expected_max_health: int,
) -> None:
    game, actor, _ = _game(card_id)
    own = game.state.players[actor]
    game.apply(Action(ActionType.PLAY, 109_000, TargetRef.minion(actor, 109_001)))
    assert (own.board[0].attack, own.board[0].health, own.board[0].max_health) == (
        expected_attack,
        expected_health,
        expected_max_health,
    )
    assert [card.card_id for card in own.hand] == ["CS2_172"]


def test_fan_of_knives_damages_all_enemy_minions_then_draws() -> None:
    game, actor, enemy = _game("CORE_EX1_129")
    own = game.state.players[actor]
    opposing = game.state.players[enemy]
    game.apply(Action(ActionType.PLAY, 109_000))
    assert [(minion.card_id, minion.health) for minion in opposing.board] == [("CS2_182", 5)]
    assert [card.card_id for card in own.hand] == ["CS2_172"]


def test_destroy_spells_remove_only_the_selected_minion() -> None:
    game, _, enemy = _game("CORE_CS2_076")
    game.apply(Action(ActionType.PLAY, 109_000, TargetRef.minion(enemy, 109_002)))
    assert [minion.card_id for minion in game.state.players[enemy].board] == ["CS2_231"]


def test_destroy_effect_runs_the_destroyed_minions_deathrattle() -> None:
    game = Game(card_registry=runtime_registry(["CORE_CS2_076", "CORE_EX1_096"]))
    actor = game.state.active_player
    enemy = 1 - actor
    own = game.state.players[actor]
    opposing = game.state.players[enemy]
    own.mana = own.max_mana = 10
    own.hand = [HandCard(109_030, "CORE_CS2_076")]
    opposing.hand = []
    opposing.deck = ["CS2_172"]
    opposing.board = [Minion(109_031, "CORE_EX1_096", 2, 1, 1, summoned_turn=0)]
    game.apply(Action(ActionType.PLAY, 109_030, TargetRef.minion(enemy, 109_031)))
    assert opposing.board == []
    assert [card.card_id for card in opposing.hand] == ["CS2_172"]


def test_siphon_soul_destroys_a_minion_and_heals_owner() -> None:
    game, actor, enemy = _game("CORE_EX1_309")
    own = game.state.players[actor]
    game.apply(Action(ActionType.PLAY, 109_000, TargetRef.minion(enemy, 109_002)))
    assert own.hero_health == 18
    assert [minion.card_id for minion in game.state.players[enemy].board] == ["CS2_231"]


def test_shadow_word_ruin_destroys_high_attack_minions_on_both_sides() -> None:
    game, actor, enemy = _game("CORE_EX1_197")
    own = game.state.players[actor]
    opposing = game.state.players[enemy]
    own.board.append(Minion(109_020, "CS2_200", 6, 7, 7, summoned_turn=0))
    opposing.board[0].attack = 5
    game.apply(Action(ActionType.PLAY, 109_000))
    assert [minion.card_id for minion in own.board] == ["CS2_120"]
    assert [minion.card_id for minion in opposing.board] == ["CS2_231"]
