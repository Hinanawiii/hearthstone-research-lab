from __future__ import annotations

import tempfile
from dataclasses import asdict
from pathlib import Path

import pytest

from cardlab.authoring.generated import runtime_registry
from cardlab.authoring.generated.runner import (
    CARD_METADATA,
    CARD_MODULES,
    SCENARIO_BUILDERS,
    SCENARIO_CARD_NAME_CATALOGS,
    build_review_artifact,
)
from cardlab.authoring.generated.status_batch import (
    AUTHORING_METADATA,
    CARDS,
    SCENARIO_CARD_NAMES_ZH,
    build_review_scenario,
)
from cardlab.authoring.review_format import (
    REVIEW_SCHEMA_VERSION,
    render_review_document_zh,
    validate_review_document,
)
from cardlab.authoring.store import ReviewStore

EXPECTED_CARD_IDS = {
    "CORE_EX1_169",
    "RLK_048",
    "CORE_CS2_009",
    "CORE_EX1_011",
    "CORE_ULD_191",
    "CORE_GIL_622",
    "CORE_EX1_362",
    "CORE_EX1_619",
    "CORE_AT_055",
    "CORE_CS1_112",
    "CORE_AT_064",
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
            "card_module": "src/cardlab/authoring/generated/status_batch.py",
            "generator": metadata["generated_by"],
            "definition": asdict(CARDS[card_id]),
        },
        "scenario": build_review_scenario(card_id, runtime_registry([card_id])),
    }


def test_status_batch_contracts_and_runner_registration_are_complete() -> None:
    assert set(CARDS) == set(AUTHORING_METADATA) == EXPECTED_CARD_IDS
    for card_id in CARDS:
        assert AUTHORING_METADATA[card_id]["source_version"] == "250339"
        assert CARD_MODULES[card_id].endswith("status_batch.py")
        assert CARD_METADATA[card_id] == AUTHORING_METADATA[card_id]
        assert card_id in SCENARIO_BUILDERS
        assert SCENARIO_CARD_NAME_CATALOGS[card_id] == SCENARIO_CARD_NAMES_ZH


@pytest.mark.parametrize("card_id", list(CARDS))
def test_each_status_card_has_a_valid_executable_chinese_review(card_id: str) -> None:
    document = _document(card_id)
    validate_review_document(document)
    scenario = document["scenario"]
    assert scenario["assertions"]
    assert scenario["before"] != scenario["after"]
    assert scenario["special_cases"] == []
    rendered = render_review_document_zh(document, SCENARIO_CARD_NAMES_ZH)
    assert AUTHORING_METADATA[card_id]["name_zh"] in rendered
    assert "操作前" in rendered and "操作后" in rendered and "逐项核对" in rendered


def test_target_scope_and_fixed_hero_effects_are_explicit() -> None:
    mark = build_review_scenario("CORE_CS2_009", runtime_registry(["CORE_CS2_009"]))
    assert any(
        item["assertion_id"] == "enemy-minion-is-valid"
        and item["before"] == [4, 5]
        and item["after"] == [6, 8]
        for item in mark["assertions"]
    )

    heal = build_review_scenario("CORE_AT_055", runtime_registry(["CORE_AT_055"]))
    assert any(
        item["assertion_id"] == "enemy-hero-healed"
        and item["before"] == 25
        and item["after"] == 30
        for item in heal["assertions"]
    )

    lifedrinker = build_review_scenario(
        "CORE_GIL_622", runtime_registry(["CORE_GIL_622"])
    )
    assert any(
        item["assertion_id"] == "enemy-hero-damaged"
        and item["after"] == 22
        for item in lifedrinker["assertions"]
    )
    assert any(
        item["assertion_id"] == "owner-hero-healed"
        and item["after"] == 25
        for item in lifedrinker["assertions"]
    )


def test_armor_absorbs_later_damage_before_health() -> None:
    scenario = build_review_scenario("CORE_AT_064", runtime_registry(["CORE_AT_064"]))
    own_after = next(
        item for item in scenario["after"]["players"] if item["role_zh"] == "我方"
    )
    assert own_after["hero"]["health"] == 19
    assert own_after["hero"]["armor"] == 3

    from cardlab.engine import Game
    from cardlab.model import Action, ActionType, HandCard, TargetRef

    game = Game(card_registry=runtime_registry(["CORE_AT_064"]))
    actor = game.state.active_player
    player = game.state.players[actor]
    player.hero_health = 22
    player.mana = 10
    player.hand = [HandCard(94_000, "CORE_AT_064")]
    game.apply(Action(ActionType.PLAY, 94_000, TargetRef.hero(actor)))
    game._damage(TargetRef.hero(actor), 5)
    assert player.hero_armor == 0
    assert player.hero_health == 17


def test_runner_builds_status_artifact_without_local_run_files() -> None:
    with tempfile.TemporaryDirectory() as directory:
        store = ReviewStore(Path(directory) / "review.db")
        card_id = "RLK_048"
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

