from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict

from ..review_format import (
    REVIEW_SCHEMA_VERSION,
    render_review_document_zh,
    validate_review_document,
)
from ..store import ReviewStore
from . import GENERATED_CARDS, runtime_registry
from .rlk_709 import AUTHORING_METADATA, SCENARIO_CARD_NAMES_ZH, build_review_scenario

CARD_MODULES = {"RLK_709": "src/cardlab/authoring/generated/rlk_709.py"}
CARD_METADATA = {"RLK_709": AUTHORING_METADATA}
SCENARIO_BUILDERS = {"RLK_709": build_review_scenario}
SCENARIO_CARD_NAME_CATALOGS = {"RLK_709": SCENARIO_CARD_NAMES_ZH}


def build_review_artifact(store: ReviewStore, card_id: str) -> Dict[str, Any]:
    card = store.get_card(card_id)
    if not card["ready_to_generate"]:
        raise ValueError("card must pass authoring review and generation approval")
    try:
        definition = GENERATED_CARDS[card_id]
        metadata = CARD_METADATA[card_id]
        scenario_builder = SCENARIO_BUILDERS[card_id]
    except KeyError as error:
        raise ValueError("generated implementation is not registered: {}".format(card_id)) from error
    if card["source_version"] != metadata["source_version"]:
        raise ValueError("generated implementation source version is stale")
    if card["source_text"] != metadata["source_text_zh"]:
        raise ValueError("generated implementation source text is stale")

    scenario = scenario_builder(runtime_registry([card_id]))
    document = {
        "schema_version": REVIEW_SCHEMA_VERSION,
        "locale": "zh-CN",
        "card": {
            "card_id": card_id,
            "name_zh": card["name"],
            "source_text_zh": card["source_text"],
            "source_version": card["source_version"],
        },
        "implementation": {
            "definition": asdict(definition),
            "generator": metadata["generated_by"],
            "card_module": CARD_MODULES[card_id],
        },
        "scenario": scenario,
    }
    validate_review_document(document)
    return document


def stage_generated_card_for_review(
    store: ReviewStore,
    card_id: str,
    artifact_path: Path,
    *,
    automated_tests: str,
) -> Dict[str, Any]:
    artifact = build_review_artifact(store, card_id)
    store.upsert_card_names(
        SCENARIO_CARD_NAME_CATALOGS[card_id],
        source_kind="generated-review-scenario",
        source_version=str(artifact["card"]["source_version"]),
    )
    summary_path = artifact_path.with_name("review-summary.zh-CN.txt")
    review_text_zh = render_review_document_zh(artifact, store.card_names_zh())
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary_path.write_text(review_text_zh, encoding="utf-8")
    implementation = artifact["implementation"]
    card = artifact["card"]
    evidence = {
        "artifact_path": str(artifact_path),
        "summary_path": str(summary_path),
        "card_module": implementation["card_module"],
        "generator": implementation["generator"],
        "source_version": card["source_version"],
        "automated_tests": automated_tests,
        "scenario_document": artifact,
        "review_text_zh": review_text_zh,
    }
    current_status = str(store.get_card(card_id)["implementation_status"])
    if current_status == "under_review":
        store.set_implementation_status(
            card_id,
            "generated",
            str(implementation["generator"]),
            evidence=evidence,
            note="审核产物格式已更新，重新生成首版实现核验记录。",
        )
    elif current_status not in {"not_started", "generated", "rejected"}:
        raise ValueError(
            "cannot stage generated card from implementation status: {}".format(current_status)
        )
    if current_status != "generated":
        store.set_implementation_status(
            card_id,
            "generated",
            str(implementation["generator"]),
            evidence=evidence,
            note="根据已批准的卡牌契约生成一个有边界的首版实现。",
        )
    return store.set_implementation_status(
        card_id,
        "under_review",
        "automated-authoring-validator",
        evidence=evidence,
        note="自动检查通过，等待人工核对代码、中文说明与前后局面。",
    )
