from __future__ import annotations

from dataclasses import asdict

import pytest

from cardlab.authoring.generated import runtime_registry
from cardlab.authoring.generated.hero_weapon_mechanics_batch import (
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
from cardlab.model import Action, ActionType, HandCard, Minion, TargetRef, Weapon

EXPECTED_CARD_IDS = {
    "CORE_RLK_086",
    "CS3_020",
    "CORE_NEW1_022",
    "CORE_GVG_059",
    "CORE_DAL_720",
    "CORE_LOOT_044",
    "CORE_BT_781",
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
            "card_module": "src/cardlab/authoring/generated/hero_weapon_mechanics_batch.py",
            "generator": metadata["generated_by"],
            "definition": asdict(CARDS[card_id]),
        },
        "scenario": build_review_scenario(card_id, runtime_registry([card_id])),
    }


def _game(card_id: str) -> tuple[Game, int, int]:
    game = Game(seed=43, card_registry=runtime_registry([card_id]))
    actor = game.state.active_player
    enemy = 1 - actor
    own = game.state.players[actor]
    own.mana = own.max_mana = 10
    own.hand = []
    own.board = []
    game.state.players[enemy].board = []
    return game, actor, enemy


def test_hero_weapon_batch_registration_is_complete() -> None:
    assert set(CARDS) == set(AUTHORING_METADATA) == EXPECTED_CARD_IDS
    for card_id in CARDS:
        assert CARD_MODULES[card_id].endswith("hero_weapon_mechanics_batch.py")
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
    assert document["scenario"]["special_cases"]


def test_frostmourne_tracks_kills_and_resummons_them_when_it_breaks() -> None:
    game, actor, enemy = _game("CORE_RLK_086")
    own = game.state.players[actor]
    opposing = game.state.players[enemy]
    own.weapon = Weapon(
        140_000,
        "CORE_RLK_086",
        4,
        1,
        killed_minion_card_ids=("CS2_120",),
    )
    own.hero_attack = 4
    opposing.board = [Minion(140_001, "CS2_182", 4, 4, 5, summoned_turn=0)]
    game.apply(
        Action(
            ActionType.HERO_ATTACK,
            140_000,
            TargetRef.minion(enemy, 140_001),
        )
    )
    assert own.weapon is None
    assert [minion.card_id for minion in own.board] == ["CS2_120", "CS2_182"]


def test_inquisitor_attacks_the_same_surviving_target_after_hero_attack() -> None:
    game, actor, enemy = _game("CS3_020")
    own = game.state.players[actor]
    opposing = game.state.players[enemy]
    own.board = [
        Minion(140_010, "CS3_020", 8, 8, 8, rush=True, summoned_turn=0)
    ]
    own.weapon = Weapon(140_011, "fixture_weapon", 1, 2)
    own.hero_attack = 1
    game.apply(Action(ActionType.HERO_ATTACK, 140_011, TargetRef.hero(enemy)))
    assert opposing.hero_health == 21


def test_inquisitor_does_not_attack_a_target_that_died_to_the_hero() -> None:
    game, actor, enemy = _game("CS3_020")
    own = game.state.players[actor]
    opposing = game.state.players[enemy]
    own.board = [Minion(140_020, "CS3_020", 8, 8, 8, rush=True, summoned_turn=0)]
    own.weapon = Weapon(140_021, "fixture_weapon", 3, 2)
    own.hero_attack = 3
    opposing.board = [Minion(140_022, "CS2_120", 2, 3, 3, summoned_turn=0)]
    game.apply(
        Action(
            ActionType.HERO_ATTACK,
            140_021,
            TargetRef.minion(enemy, 140_022),
        )
    )
    assert opposing.board == []
    assert own.board[0].health == 8
    assert own.hero_health == 28


def test_dread_corsair_cost_is_reduced_by_current_weapon_attack() -> None:
    game, actor, _ = _game("CORE_NEW1_022")
    own = game.state.players[actor]
    own.weapon = Weapon(140_030, "fixture_weapon", 3, 2)
    own.hero_attack = 3
    own.hand = [HandCard(140_031, "CORE_NEW1_022")]
    game.apply(Action(ActionType.PLAY, 140_031))
    assert own.mana == 9
    assert own.board[0].taunt is True


def test_coghammer_grants_both_keywords_to_one_random_friendly_minion() -> None:
    game, actor, _ = _game("CORE_GVG_059")
    own = game.state.players[actor]
    own.hand = [HandCard(140_040, "CORE_GVG_059")]
    own.board = [Minion(140_041, "CS2_120", 2, 3, 3, summoned_turn=0)]
    game.apply(Action(ActionType.PLAY, 140_040))
    assert own.board[0].divine_shield is True
    assert own.board[0].taunt is True


def test_pickaxe_returns_a_random_friendly_minion_with_two_cost_discount() -> None:
    game, actor, enemy = _game("CORE_DAL_720")
    own = game.state.players[actor]
    own.weapon = Weapon(140_050, "CORE_DAL_720", 4, 1)
    own.hero_attack = 4
    own.board = [Minion(140_051, "CS2_182", 4, 5, 5, summoned_turn=0)]
    game.apply(Action(ActionType.HERO_ATTACK, 140_050, TargetRef.hero(enemy)))
    assert own.board == []
    assert [(card.card_id, card.cost_modifier) for card in own.hand] == [
        ("CS2_182", -2)
    ]


def test_bladed_gauntlet_tracks_armor_and_cannot_attack_heroes() -> None:
    game, actor, enemy = _game("CORE_LOOT_044")
    own = game.state.players[actor]
    opposing = game.state.players[enemy]
    own.hero_armor = 5
    own.hand = [HandCard(140_060, "CORE_LOOT_044")]
    opposing.board = [Minion(140_061, "CS2_120", 2, 3, 3, summoned_turn=0)]
    game.apply(Action(ActionType.PLAY, 140_060))
    weapon = own.weapon
    assert weapon is not None
    assert (weapon.attack, own.hero_attack) == (5, 5)
    hero_attacks = [
        action
        for action in game.legal_actions()
        if action.action_type == ActionType.HERO_ATTACK
    ]
    assert [action.target for action in hero_attacks] == [
        TargetRef.minion(enemy, 140_061)
    ]
    game.apply(hero_attacks[0])
    assert (own.hero_armor, weapon.attack, own.hero_attack) == (3, 3, 3)


def test_bulwark_replaces_an_entire_damage_event_with_one_durability() -> None:
    game, actor, _ = _game("CORE_BT_781")
    own = game.state.players[actor]
    own.weapon = Weapon(140_070, "CORE_BT_781", 1, 1)
    own.hero_attack = 1
    own.hand = [HandCard(140_071, "CS2_029")]
    game.apply(Action(ActionType.PLAY, 140_071, TargetRef.hero(actor)))
    assert own.hero_health == 30
    assert own.weapon is None


def test_bulwark_prevents_fatigue_as_a_damage_event() -> None:
    game, actor, _ = _game("CORE_BT_781")
    own = game.state.players[actor]
    own.deck = []
    own.weapon = Weapon(140_080, "CORE_BT_781", 1, 1)
    own.hero_attack = 1
    game._draw(actor)
    assert own.fatigue == 1
    assert own.hero_health == 30
    assert own.weapon is None
