from __future__ import annotations

from dataclasses import asdict

import pytest

from cardlab.authoring.generated import runtime_registry
from cardlab.authoring.generated.event_trigger_batch import (
    AUTHORING_METADATA,
    CARDS,
    CONTRACTS,
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

EXPECTED_CARD_IDS = {
    "CORE_BT_351",
    "CORE_BT_493",
    "CORE_BT_510",
    "CORE_DRG_256",
    "CORE_EX1_007",
    "CORE_EX1_509",
    "CORE_EX1_559",
    "CORE_EX1_604",
    "CORE_GVG_103",
    "CORE_ICC_210",
    "CORE_NEW1_020",
    "CORE_NX2_028",
    "CORE_RLK_083",
    "CORE_TTN_843",
    "CORE_ULD_133",
    "CORE_WC_042",
    "CORE_YOP_034",
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
            "card_module": "src/cardlab/authoring/generated/event_trigger_batch.py",
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


def test_event_trigger_batch_registration_is_complete() -> None:
    assert set(CARDS) == set(CONTRACTS) == set(AUTHORING_METADATA) == EXPECTED_CARD_IDS
    assert set(TOKEN_CARDS) <= set(runtime_registry([]))
    for card_id in CARDS:
        assert CARD_MODULES[card_id].endswith("event_trigger_batch.py")
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


def test_damage_and_global_damage_listeners_fire() -> None:
    own, _ = _players("CORE_EX1_007")
    assert own["zones"]["hand"]["count"] == 1
    assert _find(own, "CORE_EX1_007")["health"] == 3

    own, enemy = _players("CORE_EX1_604")
    assert _find(own, "CORE_EX1_604")["attack"] == 3
    assert _find(enemy, "EVENT_TEST_MINION")["health"] == 5


def test_hero_attack_listeners_do_not_need_to_own_the_weapon() -> None:
    own, enemy = _players("CORE_BT_351")
    assert _find(own, "CORE_BT_351")["attack"] == 2
    assert enemy["hero"]["health"] == 28

    own, _ = _players("CORE_NX2_028")
    assert own["hero"]["armor"] == 4
    assert own["zones"]["hand"]["count"] == 1
    assert own["zones"]["deck"]["count"] == 0


def test_attacked_listener_fires_only_from_the_defending_minion() -> None:
    own, enemy = _players("CORE_BT_510")
    assert own["hero"]["health"] == 29
    assert _find(own, "EVENT_TEST_MINION")["health"] == 2
    assert _find(enemy, "CORE_BT_510")["health"] == 5


def test_play_and_summon_race_listeners_are_separate() -> None:
    own, _ = _players("CORE_EX1_509")
    assert _find(own, "CORE_EX1_509")["attack"] == 2
    assert _find(own, "EVENT_TEST_MURLOC")["attack"] == 2

    own, _ = _players("CORE_WC_042")
    assert _find(own, "CORE_WC_042")["attack"] == 2
    assert _find(own, "EVENT_TEST_ELEMENTAL")["attack"] == 2


def test_turn_start_and_turn_end_listeners_fire() -> None:
    own, _ = _players("CORE_GVG_103")
    assert _find(own, "CORE_GVG_103")["attack"] == 2

    own, _ = _players("CORE_ICC_210")
    friend = _find(own, "EVENT_TEST_MINION")
    assert (friend["attack"], friend["health"], friend["max_health"]) == (2, 7, 7)

    own, _ = _players("CORE_ULD_133")
    assert own["zones"]["hand"]["count"] == 1
    assert own["zones"]["deck"]["count"] == 0

    _, enemy = _players("CORE_YOP_034")
    assert _board(enemy) == []

    _, enemy = _players("CORE_BT_493")
    assert enemy["hero"]["health"] == 24


def test_hero_power_and_spell_listeners_fire_after_the_action() -> None:
    _, enemy = _players("CORE_DRG_256")
    assert enemy["hero"]["health"] == 24

    own, _ = _players("CORE_EX1_559")
    assert [card["card_id"] for card in own["zones"]["hand"]["cards"]] == ["CS2_029"]

    own, enemy = _players("CORE_NEW1_020")
    assert _find(own, "CORE_NEW1_020")["health"] == 1
    assert _find(own, "EVENT_TEST_MINION")["health"] == 5
    assert _find(enemy, "EVENT_TEST_MINION")["health"] == 5

    _, enemy = _players("CORE_RLK_083")
    assert enemy["hero"]["health"] == 29
    assert _find(enemy, "EVENT_TEST_MINION")["health"] == 5


def test_draw_listener_summons_the_rush_demon() -> None:
    own, _ = _players("CORE_TTN_843")
    token = _find(own, "TTN_843t1")
    assert token["attack"] == 1
    assert token["health"] == 1
    assert "突袭" in token["mechanics_zh"]
    assert own["zones"]["deck"]["count"] == 0
