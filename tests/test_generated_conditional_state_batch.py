from __future__ import annotations

from dataclasses import asdict

import pytest

from cardlab.authoring.generated import runtime_registry
from cardlab.authoring.generated.conditional_state_batch import (
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
from cardlab.model import Action, ActionType, HandCard, Minion, TargetRef, Weapon

EXPECTED_CARD_IDS = {
    "CORE_BAR_878",
    "CORE_BT_035",
    "CORE_BT_072",
    "CORE_CS2_072",
    "CORE_EX1_043",
    "CORE_EX1_103",
    "CORE_EX1_193",
    "CORE_EX1_414",
    "CORE_GIL_534",
    "CORE_GIL_623",
    "CORE_GVG_061",
    "CORE_KAR_061",
    "CORE_NEW1_021",
    "CORE_OG_218",
    "CORE_RLK_814",
    "CORE_UNG_928",
    "CORE_WON_351",
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
            "card_module": "src/cardlab/authoring/generated/conditional_state_batch.py",
            "generator": metadata["generated_by"],
            "definition": asdict(CARDS[card_id]),
        },
        "scenario": build_review_scenario(card_id, runtime_registry([card_id])),
    }


def _players(card_id: str) -> tuple[dict[str, object], dict[str, object]]:
    scenario = build_review_scenario(card_id, runtime_registry([card_id]))
    players = scenario["after"]["players"]
    return players[0], players[1]


def _board(player: dict[str, object]) -> list[dict[str, object]]:
    return player["zones"]["board"]


def _find(player: dict[str, object], card_id: str) -> dict[str, object]:
    return next(item for item in _board(player) if item["card_id"] == card_id)


def test_conditional_state_batch_registration_is_complete() -> None:
    assert set(CARDS) == set(CONTRACTS) == set(AUTHORING_METADATA) == EXPECTED_CARD_IDS
    assert set(TOKEN_CARDS) <= set(runtime_registry([]))
    for card_id in CARDS:
        assert CARD_MODULES[card_id].endswith("conditional_state_batch.py")
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


def test_combat_medic_only_listens_for_holy_spells() -> None:
    own, _ = _players("CORE_BAR_878")
    token = _find(own, "BAR_878t")
    assert (token["attack"], token["health"]) == (2, 2)
    assert "吸血" in token["mechanics_zh"]

    registry = runtime_registry(["CORE_BAR_878"])
    registry.update(SUPPORT_CARDS)
    game = Game(card_registry=registry)
    actor = game.state.active_player
    own_state = game.state.players[actor]
    own_state.mana = own_state.max_mana = 10
    own_state.board = [Minion(140_001, "CORE_BAR_878", 3, 5, 5, summoned_turn=0)]
    own_state.hand = [HandCard(140_002, "STATE_TEST_SHADOW")]
    game.apply(Action(ActionType.PLAY, 140_002))
    assert [minion.card_id for minion in own_state.board] == ["CORE_BAR_878"]


def test_chaos_strike_attack_expires_and_allows_an_unarmed_attack() -> None:
    registry = runtime_registry(["CORE_BT_035"])
    registry.update(SUPPORT_CARDS)
    game = Game(card_registry=registry)
    actor = game.state.active_player
    enemy = 1 - actor
    own = game.state.players[actor]
    own.mana = own.max_mana = 10
    own.hand = [HandCard(140_010, "CORE_BT_035")]
    own.deck = ["STATE_TEST_DRAW"]
    game.apply(Action(ActionType.PLAY, 140_010))
    assert own.hero_attack == 2
    assert Action(ActionType.HERO_ATTACK, None, TargetRef.hero(enemy)) in game.legal_actions()
    game.apply(Action.end_turn())
    assert own.hero_attack == 0


def test_deep_freeze_summons_water_elementals_that_freeze_damaged_targets() -> None:
    own, enemy = _players("CORE_BT_072")
    assert enemy["hero"]["tags"] == ["冻结"]
    assert [(item["attack"], item["health"]) for item in _board(own)] == [(3, 6), (3, 6)]

    registry = runtime_registry(["CORE_BT_072"])
    game = Game(card_registry=registry)
    actor = game.state.active_player
    enemy_index = 1 - actor
    game.state.turn = 2
    own_state = game.state.players[actor]
    opposing = game.state.players[enemy_index]
    own_state.board = [Minion(140_020, "CS2_033", 3, 6, 6, summoned_turn=0)]
    opposing.board = [Minion(140_021, "CS2_182", 4, 6, 6, summoned_turn=0)]
    game.apply(Action(ActionType.ATTACK, 140_020, TargetRef.minion(enemy_index, 140_021)))
    assert opposing.board[0].frozen is True


def test_backstab_excludes_damaged_minions_from_legal_targets() -> None:
    registry = runtime_registry(["CORE_CS2_072"])
    game = Game(card_registry=registry)
    actor = game.state.active_player
    enemy = 1 - actor
    own = game.state.players[actor]
    own.mana = own.max_mana = 10
    own.hand = [HandCard(140_030, "CORE_CS2_072")]
    game.state.players[enemy].board = [
        Minion(140_031, "CS2_182", 4, 6, 6, summoned_turn=0),
        Minion(140_032, "CS2_182", 4, 5, 6, summoned_turn=0),
    ]
    play_targets = {
        action.target
        for action in game.legal_actions()
        if action.action_type == ActionType.PLAY and action.source_id == 140_030
    }
    assert TargetRef.minion(enemy, 140_031) in play_targets
    assert TargetRef.minion(enemy, 140_032) not in play_targets


def test_battlecry_conditions_update_only_the_intended_entities() -> None:
    own, _ = _players("CORE_EX1_043")
    dragon = _find(own, "CORE_EX1_043")
    assert (dragon["attack"], dragon["health"], dragon["max_health"]) == (4, 4, 4)

    own, _ = _players("CORE_EX1_103")
    assert _find(own, "STATE_TEST_MURLOC")["health"] == 4
    assert _find(own, "CORE_EX1_103")["health"] == 3

    own, enemy = _players("CORE_GIL_623")
    assert _find(own, "CORE_GIL_623")["health"] == 9
    assert enemy["zones"]["hand"]["count"] == 3

    own, _ = _players("CORE_RLK_814")
    minion = _find(own, "CORE_RLK_814")
    assert (minion["attack"], minion["health"]) == (2, 3)


def test_deck_copy_and_each_race_draw_preserve_zone_semantics() -> None:
    own, enemy = _players("CORE_EX1_193")
    assert own["zones"]["hand"]["cards"][0]["card_id"] == "STATE_TEST_DRAGON"
    assert enemy["zones"]["deck"]["count"] == 1

    own, _ = _players("CORE_KAR_061")
    assert {card["card_id"] for card in own["zones"]["hand"]["cards"]} == {
        "STATE_TEST_BEAST",
        "STATE_TEST_DRAGON",
        "STATE_TEST_MURLOC",
    }
    assert own["zones"]["deck"]["count"] == 0


def test_hero_attack_muster_and_doomsayer_resolve_in_order() -> None:
    own, _ = _players("CORE_GIL_534")
    thug = _find(own, "CORE_GIL_534")
    assert (thug["attack"], thug["health"]) == (4, 4)

    own, _ = _players("CORE_GVG_061")
    assert [minion["card_id"] for minion in _board(own)] == ["CS2_101t"] * 3
    assert own["zones"]["weapon"]["attack"] == 1
    assert own["zones"]["weapon"]["durability"] == 4

    own, enemy = _players("CORE_NEW1_021")
    assert _board(own) == []
    assert _board(enemy) == []


def test_dynamic_attack_bonuses_appear_and_disappear_with_state() -> None:
    own, _ = _players("CORE_OG_218")
    assert _find(own, "CORE_OG_218")["attack"] == 5

    own, _ = _players("CORE_EX1_414")
    assert _find(own, "CORE_EX1_414")["attack"] == 10

    own, _ = _players("CORE_UNG_928")
    assert _find(own, "CORE_UNG_928")["attack"] == 3

    registry = runtime_registry(["CORE_WON_351"])
    registry.update(SUPPORT_CARDS)
    game = Game(card_registry=registry)
    actor = game.state.active_player
    own_state = game.state.players[actor]
    own_state.board = [Minion(140_040, "CORE_WON_351", 1, 2, 2, summoned_turn=0)]
    own_state.weapon = Weapon(140_041, "STATE_TEST_WEAPON", 2, 1)
    own_state.hero_attack = 2
    game._refresh_dynamic_attack_bonuses()
    assert own_state.board[0].attack == 3
    game._destroy_weapon(actor)
    assert own_state.board[0].attack == 1
