from __future__ import annotations

from dataclasses import asdict

import pytest

from cardlab.authoring.generated import runtime_registry
from cardlab.authoring.generated.conditional_weapon_batch import (
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
from cardlab.model import (
    Action,
    ActionType,
    HandCard,
    Minion,
    TargetRef,
    Weapon,
)

EXPECTED_CARD_IDS = {
    "CORE_TRL_111",
    "CORE_NEW1_018",
    "CS3_022",
    "CORE_TRL_240",
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
            "card_module": (
                "src/cardlab/authoring/generated/conditional_weapon_batch.py"
            ),
            "generator": metadata["generated_by"],
            "definition": asdict(CARDS[card_id]),
        },
        "scenario": build_review_scenario(card_id, runtime_registry([card_id])),
    }


def _game(card_ids: list[str]) -> tuple[Game, int, int]:
    game = Game(card_registry=runtime_registry(card_ids))
    actor = game.state.active_player
    enemy = 1 - actor
    own = game.state.players[actor]
    opposing = game.state.players[enemy]
    own.mana = own.max_mana = 10
    own.hand = [HandCard(102_000 + index, card_id) for index, card_id in enumerate(card_ids)]
    own.board = []
    opposing.board = []
    return game, actor, enemy


def test_conditional_weapon_batch_registration_is_complete() -> None:
    assert set(CARDS) == set(AUTHORING_METADATA) == EXPECTED_CARD_IDS
    for card_id in CARDS:
        assert CARD_MODULES[card_id].endswith("conditional_weapon_batch.py")
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
    assert "特殊情况" in rendered


@pytest.mark.parametrize(
    ("races", "expected_durability"),
    [
        ((), 2),
        (("BEAST",), 3),
        (("PIRATE",), 2),
    ],
)
def test_headhunters_hatchet_gains_durability_only_for_friendly_beast(
    races: tuple[str, ...], expected_durability: int
) -> None:
    game, actor, _ = _game(["CORE_TRL_111"])
    own = game.state.players[actor]
    if races:
        own.board = [
            Minion(102_100, "CS2_120", 2, 3, 3, races=races, summoned_turn=0)
        ]
    game.apply(Action(ActionType.PLAY, 102_000))
    assert own.weapon is not None
    assert (own.weapon.attack, own.weapon.durability) == (2, expected_durability)


def test_bloodsail_raider_reads_current_weapon_attack() -> None:
    game, actor, _ = _game(["CORE_NEW1_018"])
    own = game.state.players[actor]
    own.weapon = Weapon(102_200, "CORE_BT_921", 5, 2)
    own.hero_attack = 5
    game.apply(Action(ActionType.PLAY, 102_000))
    assert (own.board[0].attack, own.board[0].health) == (7, 3)

    game_without_weapon, actor_without_weapon, _ = _game(["CORE_NEW1_018"])
    own_without_weapon = game_without_weapon.state.players[actor_without_weapon]
    game_without_weapon.apply(Action(ActionType.PLAY, 102_000))
    assert own_without_weapon.board[0].attack == 2


def test_fogsail_freebooter_only_requests_a_target_with_weapon() -> None:
    game, actor, enemy = _game(["CS3_022"])
    own = game.state.players[actor]
    no_weapon_actions = [
        action for action in game.legal_actions() if action.source_id == 102_000
    ]
    assert no_weapon_actions == [Action(ActionType.PLAY, 102_000)]
    game.apply(no_weapon_actions[0])
    assert game.state.players[enemy].hero_health == 30

    game, actor, enemy = _game(["CS3_022"])
    own = game.state.players[actor]
    own.weapon = Weapon(102_300, "CORE_BT_921", 2, 2)
    own.hero_attack = 2
    own.board = [Minion(102_301, "CS2_120", 2, 3, 3, summoned_turn=0)]
    game.state.players[enemy].board = [
        Minion(102_302, "CS2_182", 4, 5, 5, summoned_turn=0)
    ]
    with_weapon_actions = [
        action for action in game.legal_actions() if action.source_id == 102_000
    ]
    assert all(action.target is not None for action in with_weapon_actions)
    assert TargetRef.hero(actor) in [action.target for action in with_weapon_actions]
    assert TargetRef.minion(actor, 102_301) in [
        action.target for action in with_weapon_actions
    ]
    game.apply(Action(ActionType.PLAY, 102_000, TargetRef.hero(actor)))
    assert own.hero_health == 28


def test_savage_striker_targets_only_enemy_minions_and_reads_hero_attack() -> None:
    game, actor, enemy = _game(["CORE_TRL_240"])
    own = game.state.players[actor]
    opposing = game.state.players[enemy]
    own.hero_attack = 4
    own.board = [Minion(102_400, "CS2_120", 2, 3, 3, summoned_turn=0)]
    opposing.board = [Minion(102_401, "CS2_182", 4, 7, 7, summoned_turn=0)]
    play_actions = [
        action for action in game.legal_actions() if action.source_id == 102_000
    ]
    assert play_actions == [
        Action(ActionType.PLAY, 102_000, TargetRef.minion(enemy, 102_401))
    ]
    game.apply(play_actions[0])
    assert opposing.board[0].health == 3


def test_savage_striker_can_be_played_when_no_enemy_minion_exists() -> None:
    game, actor, _ = _game(["CORE_TRL_240"])
    own = game.state.players[actor]
    own.hero_attack = 4
    play_actions = [
        action for action in game.legal_actions() if action.source_id == 102_000
    ]
    assert play_actions == [Action(ActionType.PLAY, 102_000)]
    game.apply(play_actions[0])
    assert own.board[0].card_id == "CORE_TRL_240"
