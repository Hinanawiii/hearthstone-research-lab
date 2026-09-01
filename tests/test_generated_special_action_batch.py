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
from cardlab.authoring.generated.special_action_batch import (
    AUTHORING_METADATA,
    CARDS,
    CONTRACTS,
    SCENARIO_CARD_NAMES_ZH,
    SUPPORT_CARDS,
    TOKEN_CARDS,
    build_review_scenario,
)
from cardlab.authoring.review_format import (
    REVIEW_SCHEMA_VERSION,
    render_review_document_zh,
    validate_review_document,
)
from cardlab.engine import Game
from cardlab.model import Action, ActionType, HandCard, TargetRef

EXPECTED_CARD_IDS = {
    "CORE_BOT_576",
    "CORE_BT_480",
    "CORE_BT_491",
    "CORE_BT_801",
    "CORE_EX1_002",
    "CORE_EX1_005",
    "CORE_EX1_131",
    "CORE_EX1_134",
    "CORE_SW_072",
    "CORE_SW_429",
}

TRADEABLE_CARD_IDS = {
    "CORE_EX1_002",
    "CORE_EX1_005",
    "CORE_SW_072",
    "CORE_SW_429",
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
            "card_module": "src/cardlab/authoring/generated/special_action_batch.py",
            "generator": metadata["generated_by"],
            "definition": asdict(CARDS[card_id]),
        },
        "scenario": build_review_scenario(card_id, runtime_registry([card_id])),
    }


def _players(card_id: str) -> tuple[dict[str, object], dict[str, object]]:
    players = build_review_scenario(card_id, runtime_registry([card_id]))["after"]["players"]
    return players[0], players[1]


def _board(player: dict[str, object]) -> list[dict[str, object]]:
    return player["zones"]["board"]


def _find(player: dict[str, object], card_id: str) -> dict[str, object]:
    return next(item for item in _board(player) if item["card_id"] == card_id)


def test_special_action_batch_registration_is_complete() -> None:
    assert set(CARDS) == set(CONTRACTS) == set(AUTHORING_METADATA) == EXPECTED_CARD_IDS
    assert set(TOKEN_CARDS) <= set(runtime_registry([]))
    for card_id in CARDS:
        assert CARD_MODULES[card_id].endswith("special_action_batch.py")
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


@pytest.mark.parametrize("card_id", sorted(TRADEABLE_CARD_IDS))
def test_trade_pays_one_draws_a_different_card_and_shuffles_the_source(
    card_id: str,
) -> None:
    registry = runtime_registry([card_id])
    registry.update(SUPPORT_CARDS)
    game = Game(seed=17, card_registry=registry)
    actor = game.state.active_player
    own = game.state.players[actor]
    own.mana = own.max_mana = 10
    own.hand = [HandCard(180_001, card_id)]
    own.deck = ["SPECIAL_TEST_DRAW"]
    trade = Action(ActionType.TRADE, 180_001)
    assert trade in game.legal_actions()
    game.apply(trade)
    assert own.mana == 9
    assert [card.card_id for card in own.hand] == ["SPECIAL_TEST_DRAW"]
    assert own.deck == [card_id]
    assert own.cards_played_this_turn == 0


def test_tradeable_cards_keep_their_normal_play_effects() -> None:
    own, enemy = _players("CORE_SW_072")
    assert enemy["zones"]["weapon"] is None
    assert _find(own, "CORE_SW_072")["health"] == 4

    own, _ = _players("CORE_SW_429")
    turtles = [minion for minion in _board(own) if minion["card_id"] == "SW_429t"]
    assert len(turtles) == 2
    assert all("嘲讽" in minion["mechanics_zh"] for minion in turtles)

    _, enemy = _players("CORE_EX1_002")
    assert _board(enemy) == []

    _, enemy = _players("CORE_EX1_005")
    assert _board(enemy) == []


def test_outcast_uses_the_left_or_right_hand_edge() -> None:
    own, _ = _players("CORE_BT_480")
    assert own["zones"]["deck"]["count"] == 1
    assert own["zones"]["hand"]["count"] == 2

    own, _ = _players("CORE_BT_491")
    assert own["zones"]["deck"]["count"] == 0
    assert own["zones"]["hand"]["count"] == 3

    registry = runtime_registry(["CORE_BT_480"])
    registry.update(SUPPORT_CARDS)
    game = Game(card_registry=registry)
    actor = game.state.active_player
    own_state = game.state.players[actor]
    own_state.mana = own_state.max_mana = 10
    own_state.deck = ["SPECIAL_TEST_DRAW"]
    own_state.hand = [
        HandCard(180_010, "SPECIAL_TEST_MINION"),
        HandCard(180_011, "CORE_BT_480"),
        HandCard(180_012, "SPECIAL_TEST_MINION"),
    ]
    game.apply(Action(ActionType.PLAY, 180_011))
    assert own_state.deck == ["SPECIAL_TEST_DRAW"]


def test_eye_beam_outcast_changes_cost_but_not_damage_or_lifesteal() -> None:
    own, enemy = _players("CORE_BT_801")
    assert own["resources"]["mana"] == 2
    assert own["hero"]["health"] == 28
    assert _find(enemy, "SPECIAL_TEST_MINION")["health"] == 1


def test_combo_requires_an_earlier_card_in_the_same_turn() -> None:
    own, _ = _players("CORE_EX1_131")
    assert [minion["card_id"] for minion in _board(own)] == [
        "CORE_EX1_131",
        "EX1_131t",
    ]

    _, enemy = _players("CORE_EX1_134")
    assert enemy["hero"]["health"] == 27

    own, _ = _players("CORE_BOT_576")
    assert _find(own, "SPECIAL_TEST_MINION")["attack"] == 6

    registry = runtime_registry(["CORE_EX1_134"])
    registry.update(SUPPORT_CARDS)
    game = Game(card_registry=registry)
    actor = game.state.active_player
    own_state = game.state.players[actor]
    own_state.mana = own_state.max_mana = 10
    own_state.hand = [HandCard(180_020, "CORE_EX1_134")]
    assert Action(ActionType.PLAY, 180_020) in game.legal_actions()
    assert Action(ActionType.PLAY, 180_020, TargetRef.hero(1 - actor)) not in game.legal_actions()
