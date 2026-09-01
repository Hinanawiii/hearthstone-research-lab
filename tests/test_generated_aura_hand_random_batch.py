from __future__ import annotations

from dataclasses import asdict

import pytest

from cardlab.authoring.generated import runtime_registry
from cardlab.authoring.generated.aura_hand_random_batch import (
    AUTHORING_METADATA,
    CARDS,
    CONTRACTS,
    SCENARIO_CARD_NAMES_ZH,
    SUPPORT_CARDS,
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
from cardlab.model import HandCard, Minion

EXPECTED_CARD_IDS = {
    "CORE_BAR_311",
    "CORE_CATA_007",
    "CORE_CFM_753",
    "CORE_CS2_122",
    "CORE_CS2_222",
    "CORE_EX1_082",
    "CORE_EX1_162",
    "CORE_EX1_507",
    "CORE_LOOT_373",
    "CORE_NEW1_027",
    "CORE_WW_329",
    "CS3_025",
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
            "card_module": "src/cardlab/authoring/generated/aura_hand_random_batch.py",
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


def test_aura_hand_random_batch_registration_is_complete() -> None:
    assert set(CARDS) == set(CONTRACTS) == set(AUTHORING_METADATA) == EXPECTED_CARD_IDS
    for card_id in CARDS:
        assert CARD_MODULES[card_id].endswith("aura_hand_random_batch.py")
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


def test_hand_buffs_are_persisted_on_hand_entities_and_used_when_played() -> None:
    own, _ = _players("CORE_CFM_753")
    hand_card = own["zones"]["hand"]["cards"][0]
    assert (hand_card["attack_bonus"], hand_card["health_bonus"]) == (1, 1)

    own, _ = _players("CORE_WW_329")
    hand = {card["card_id"]: card for card in own["zones"]["hand"]["cards"]}
    assert (hand["AURA_TEST_TAUNT"]["attack_bonus"], hand["AURA_TEST_TAUNT"]["health_bonus"]) == (
        2,
        2,
    )
    assert (hand["AURA_TEST_MINION"]["attack_bonus"], hand["AURA_TEST_MINION"]["health_bonus"]) == (
        0,
        0,
    )

    registry = runtime_registry(["CORE_CFM_753"])
    registry.update(SUPPORT_CARDS)
    game = Game(card_registry=registry)
    actor = game.state.active_player
    own_state = game.state.players[actor]
    own_state.mana = own_state.max_mana = 10
    own_state.hand = [HandCard(160_001, "AURA_TEST_MINION", 1, 1)]
    game.apply(game.legal_actions()[1])
    assert (own_state.board[0].attack, own_state.board[0].health) == (3, 5)


def test_lothrax_buffs_hand_when_attack_is_declared() -> None:
    own, _ = _players("CS3_025")
    hand_card = own["zones"]["hand"]["cards"][0]
    assert (hand_card["attack_bonus"], hand_card["health_bonus"]) == (1, 1)


def test_random_split_effects_preserve_total_damage_or_healing() -> None:
    own, enemy = _players("CORE_EX1_082")
    assert (30 - own["hero"]["health"]) + (30 - enemy["hero"]["health"]) == 3
    assert _find(own, "CORE_EX1_082")["health"] == 2

    own, enemy = _players("CORE_BAR_311")
    assert own["hero"]["health"] == 24
    assert _board(enemy) == []

    own, _ = _players("CORE_LOOT_373")
    assert own["hero"]["health"] == 30

    own, enemy = _players("CORE_CATA_007")
    assert _board(enemy) == []
    assert own["zones"]["hand"]["count"] == 2
    assert own["zones"]["deck"]["count"] == 0


@pytest.mark.parametrize(
    ("card_id", "support_id", "expected"),
    [
        ("CORE_CS2_122", "AURA_TEST_MINION", (3, 4, 4)),
        ("CORE_EX1_507", "AURA_TEST_MURLOC", (4, 3, 3)),
        ("CORE_NEW1_027", "AURA_TEST_PIRATE", (3, 4, 4)),
        ("CORE_CS2_222", "AURA_TEST_MINION", (3, 5, 5)),
        ("CORE_EX1_162", "AURA_TEST_MINION", (3, 4, 4)),
    ],
)
def test_each_aura_buffs_only_its_intended_recipient(
    card_id: str, support_id: str, expected: tuple[int, int, int]
) -> None:
    own, _ = _players(card_id)
    recipient = _find(own, support_id)
    assert (recipient["attack"], recipient["health"], recipient["max_health"]) == expected
    source = _find(own, card_id)
    assert source["attack"] == CARDS[card_id].attack
    assert source["health"] == CARDS[card_id].health


def test_health_aura_is_removed_when_its_source_leaves_play() -> None:
    registry = runtime_registry(["CORE_CS2_222"])
    registry.update(SUPPORT_CARDS)
    game = Game(card_registry=registry)
    actor = game.state.active_player
    own = game.state.players[actor]
    own.board = [
        Minion(160_010, "AURA_TEST_MINION", 2, 4, 4, summoned_turn=0),
        Minion(160_011, "CORE_CS2_222", 7, 7, 7, summoned_turn=0),
    ]
    game._refresh_dynamic_attack_bonuses()
    assert (own.board[0].attack, own.board[0].health) == (3, 5)
    own.board[1].health = 0
    game._cleanup_deaths()
    assert (own.board[0].attack, own.board[0].health, own.board[0].max_health) == (
        2,
        4,
        4,
    )
