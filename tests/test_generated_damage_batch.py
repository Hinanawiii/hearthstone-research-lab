from __future__ import annotations

import tempfile
from dataclasses import asdict
from pathlib import Path

import pytest

from cardlab.authoring.generated import runtime_registry
from cardlab.authoring.generated.damage_batch import (
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
    build_review_artifact,
)
from cardlab.authoring.review_format import (
    REVIEW_SCHEMA_VERSION,
    render_review_document_zh,
    validate_review_document,
)
from cardlab.authoring.store import ReviewStore


def _document(card_id: str) -> dict[str, object]:
    metadata = AUTHORING_METADATA[card_id]
    document = {
        "schema_version": REVIEW_SCHEMA_VERSION,
        "locale": "zh-CN",
        "card": {
            "card_id": card_id,
            "name_zh": metadata["name_zh"],
            "source_text_zh": metadata["source_text_zh"],
            "source_version": metadata["source_version"],
        },
        "implementation": {
            "card_module": "src/cardlab/authoring/generated/damage_batch.py",
            "generator": metadata["generated_by"],
            "definition": asdict(CARDS[card_id]),
        },
        "scenario": build_review_scenario(card_id, runtime_registry([card_id])),
    }
    return document


def test_damage_batch_contracts_and_runner_registration_are_complete() -> None:
    assert len(CARDS) == 14
    assert set(CARDS) == set(CONTRACTS) == set(AUTHORING_METADATA)
    for card_id, card in CARDS.items():
        contract = CONTRACTS[card_id]
        assert card.name == contract.name_zh
        assert card.cost == contract.cost
        assert AUTHORING_METADATA[card_id]["source_version"] == "250339"
        assert CARD_MODULES[card_id].endswith("damage_batch.py")
        assert CARD_METADATA[card_id] == AUTHORING_METADATA[card_id]
        assert card_id in SCENARIO_BUILDERS
        assert SCENARIO_CARD_NAME_CATALOGS[card_id] == SCENARIO_CARD_NAMES_ZH


@pytest.mark.parametrize("card_id", list(CARDS))
def test_each_damage_card_has_a_valid_executable_chinese_review(card_id: str) -> None:
    document = _document(card_id)
    validate_review_document(document)
    scenario = document["scenario"]
    assert scenario["assertions"]
    assert scenario["before"] != scenario["after"]
    assert scenario["special_cases"] == []
    rendered = render_review_document_zh(document, SCENARIO_CARD_NAMES_ZH)
    assert AUTHORING_METADATA[card_id]["name_zh"] in rendered
    assert "操作前" in rendered and "操作后" in rendered and "逐项核对" in rendered


def test_damage_scope_boundaries_are_visible_in_review_scenarios() -> None:
    flamestrike = build_review_scenario(
        "CORE_CS2_032", runtime_registry(["CORE_CS2_032"])
    )
    assert any(
        item["assertion_id"] == "enemy-hero-safe"
        and item["before"] == item["after"] == 30
        for item in flamestrike["assertions"]
    )

    ghoul = build_review_scenario("CORE_OG_149", runtime_registry(["CORE_OG_149"]))
    assert any(
        item["assertion_id"] == "source-excluded"
        and item["before"] == item["after"] == 3
        for item in ghoul["assertions"]
    )

    fireball = build_review_scenario("CORE_CS2_029", runtime_registry(["CORE_CS2_029"]))
    assert any(
        item["assertion_id"] == "friendly-hero-damage"
        and item["before"] == 30
        and item["after"] == 24
        for item in fireball["assertions"]
    )


def test_all_character_damage_hits_both_sides_before_death_cleanup() -> None:
    scenario = build_review_scenario("CORE_CS2_062", runtime_registry(["CORE_CS2_062"]))
    players = {item["role_zh"]: item for item in scenario["after"]["players"]}
    assert players["我方"]["hero"]["health"] == 27
    assert players["敌方"]["hero"]["health"] == 27
    assert players["我方"]["zones"]["board"][0]["health"] == 3
    assert [item["card_id"] for item in players["敌方"]["zones"]["board"]] == ["CS2_172"]
    assert players["敌方"]["zones"]["board"][0]["health"] == 4


def test_runner_builds_artifact_without_local_run_files() -> None:
    with tempfile.TemporaryDirectory() as directory:
        store = ReviewStore(Path(directory) / "review.db")
        card_id = "CORE_CS2_062"
        metadata = AUTHORING_METADATA[card_id]
        store.upsert_card(
            card_id,
            metadata["name_zh"],
            metadata["source_text_zh"],
            source_version=metadata["source_version"],
        )
        store.set_interview_complete(card_id, True)
        store.approve_generation(card_id, "human-reviewer")
        artifact = build_review_artifact(store, card_id)
        assert artifact["card"]["card_id"] == card_id
