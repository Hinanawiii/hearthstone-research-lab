from __future__ import annotations

import json
from dataclasses import asdict
from functools import partial
from pathlib import Path
from typing import Any, Callable, Dict, Mapping, Optional

from ...model import CardDef
from ..review_format import (
    REVIEW_SCHEMA_VERSION,
    render_review_document_zh,
    validate_review_document,
)
from ..store import ReviewStore
from . import GENERATED_CARDS, runtime_registry
from .core_cs2_023 import (
    AUTHORING_METADATA as CORE_CS2_023_METADATA,
)
from .core_cs2_023 import (
    SCENARIO_CARD_NAMES_ZH as CORE_CS2_023_CARD_NAMES,
)
from .core_cs2_023 import (
    build_review_scenario as build_core_cs2_023_scenario,
)
from .core_cs2_179 import (
    AUTHORING_METADATA as CORE_CS2_179_METADATA,
)
from .core_cs2_179 import (
    SCENARIO_CARD_NAMES_ZH as CORE_CS2_179_CARD_NAMES,
)
from .core_cs2_179 import (
    build_review_scenario as build_core_cs2_179_scenario,
)
from .core_ds1_185 import (
    AUTHORING_METADATA as CORE_DS1_185_METADATA,
)
from .core_ds1_185 import (
    SCENARIO_CARD_NAMES_ZH as CORE_DS1_185_CARD_NAMES,
)
from .core_ds1_185 import (
    build_review_scenario as build_core_ds1_185_scenario,
)
from .damage_batch import (
    AUTHORING_METADATA as DAMAGE_BATCH_METADATA,
)
from .damage_batch import (
    SCENARIO_CARD_NAMES_ZH as DAMAGE_BATCH_CARD_NAMES,
)
from .damage_batch import (
    build_review_scenario as build_damage_batch_scenario,
)
from .keyword_batch import (
    AUTHORING_METADATA as KEYWORD_BATCH_METADATA,
)
from .keyword_batch import (
    SCENARIO_CARD_NAMES_ZH as KEYWORD_BATCH_CARD_NAMES,
)
from .keyword_batch import (
    build_review_scenario as build_keyword_batch_scenario,
)
from .rlk_709 import AUTHORING_METADATA, SCENARIO_CARD_NAMES_ZH, build_review_scenario

CARD_MODULES: Dict[str, str] = {
    "RLK_709": "src/cardlab/authoring/generated/rlk_709.py",
    "CORE_DS1_185": "src/cardlab/authoring/generated/core_ds1_185.py",
    "CORE_CS2_023": "src/cardlab/authoring/generated/core_cs2_023.py",
    "CORE_CS2_179": "src/cardlab/authoring/generated/core_cs2_179.py",
}
CARD_METADATA: Dict[str, Mapping[str, Any]] = {
    "RLK_709": AUTHORING_METADATA,
    "CORE_DS1_185": CORE_DS1_185_METADATA,
    "CORE_CS2_023": CORE_CS2_023_METADATA,
    "CORE_CS2_179": CORE_CS2_179_METADATA,
}
SCENARIO_BUILDERS: Dict[
    str, Callable[[Dict[str, CardDef]], Dict[str, Any]]
] = {
    "RLK_709": build_review_scenario,
    "CORE_DS1_185": build_core_ds1_185_scenario,
    "CORE_CS2_023": build_core_cs2_023_scenario,
    "CORE_CS2_179": build_core_cs2_179_scenario,
}
SCENARIO_CARD_NAME_CATALOGS: Dict[str, Mapping[str, str]] = {
    "RLK_709": SCENARIO_CARD_NAMES_ZH,
    "CORE_DS1_185": CORE_DS1_185_CARD_NAMES,
    "CORE_CS2_023": CORE_CS2_023_CARD_NAMES,
    "CORE_CS2_179": CORE_CS2_179_CARD_NAMES,
}

for keyword_card_id, keyword_metadata in KEYWORD_BATCH_METADATA.items():
    CARD_MODULES[keyword_card_id] = (
        "src/cardlab/authoring/generated/keyword_batch.py"
    )
    CARD_METADATA[keyword_card_id] = keyword_metadata
    SCENARIO_BUILDERS[keyword_card_id] = partial(
        build_keyword_batch_scenario, keyword_card_id
    )
    SCENARIO_CARD_NAME_CATALOGS[keyword_card_id] = KEYWORD_BATCH_CARD_NAMES

for damage_card_id, damage_metadata in DAMAGE_BATCH_METADATA.items():
    CARD_MODULES[damage_card_id] = (
        "src/cardlab/authoring/generated/damage_batch.py"
    )
    CARD_METADATA[damage_card_id] = damage_metadata
    SCENARIO_BUILDERS[damage_card_id] = partial(
        build_damage_batch_scenario, damage_card_id
    )
    SCENARIO_CARD_NAME_CATALOGS[damage_card_id] = DAMAGE_BATCH_CARD_NAMES


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
    generation_usage: Optional[Mapping[str, Any]] = None,
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
    if generation_usage:
        evidence["generation_usage"] = dict(generation_usage)
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
