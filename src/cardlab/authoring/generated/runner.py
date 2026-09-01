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
from .advanced_status_batch import (
    AUTHORING_METADATA as ADVANCED_STATUS_BATCH_METADATA,
)
from .advanced_status_batch import (
    SCENARIO_CARD_NAMES_ZH as ADVANCED_STATUS_BATCH_CARD_NAMES,
)
from .advanced_status_batch import (
    build_review_scenario as build_advanced_status_batch_scenario,
)
from .composite_spell_batch import (
    AUTHORING_METADATA as COMPOSITE_SPELL_BATCH_METADATA,
)
from .composite_spell_batch import (
    SCENARIO_CARD_NAMES_ZH as COMPOSITE_SPELL_BATCH_CARD_NAMES,
)
from .composite_spell_batch import (
    build_review_scenario as build_composite_spell_batch_scenario,
)
from .conditional_weapon_batch import (
    AUTHORING_METADATA as CONDITIONAL_WEAPON_BATCH_METADATA,
)
from .conditional_weapon_batch import (
    SCENARIO_CARD_NAMES_ZH as CONDITIONAL_WEAPON_BATCH_CARD_NAMES,
)
from .conditional_weapon_batch import (
    build_review_scenario as build_conditional_weapon_batch_scenario,
)
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
from .deathrattle_batch import (
    AUTHORING_METADATA as DEATHRATTLE_BATCH_METADATA,
)
from .deathrattle_batch import (
    SCENARIO_CARD_NAMES_ZH as DEATHRATTLE_BATCH_CARD_NAMES,
)
from .deathrattle_batch import (
    build_review_scenario as build_deathrattle_batch_scenario,
)
from .dynamic_zone_batch import AUTHORING_METADATA as DYNAMIC_ZONE_BATCH_METADATA
from .dynamic_zone_batch import (
    SCENARIO_CARD_NAMES_ZH as DYNAMIC_ZONE_BATCH_CARD_NAMES,
)
from .dynamic_zone_batch import (
    build_review_scenario as build_dynamic_zone_batch_scenario,
)
from .event_trigger_batch import AUTHORING_METADATA as EVENT_TRIGGER_BATCH_METADATA
from .event_trigger_batch import (
    SCENARIO_CARD_NAMES_ZH as EVENT_TRIGGER_BATCH_CARD_NAMES,
)
from .event_trigger_batch import (
    build_review_scenario as build_event_trigger_batch_scenario,
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
from .status_batch import (
    AUTHORING_METADATA as STATUS_BATCH_METADATA,
)
from .status_batch import (
    SCENARIO_CARD_NAMES_ZH as STATUS_BATCH_CARD_NAMES,
)
from .status_batch import (
    build_review_scenario as build_status_batch_scenario,
)
from .summon_batch import AUTHORING_METADATA as SUMMON_BATCH_METADATA
from .summon_batch import SCENARIO_CARD_NAMES_ZH as SUMMON_BATCH_CARD_NAMES
from .summon_batch import build_review_scenario as build_summon_batch_scenario
from .tribe_poison_batch import (
    AUTHORING_METADATA as TRIBE_POISON_BATCH_METADATA,
)
from .tribe_poison_batch import (
    SCENARIO_CARD_NAMES_ZH as TRIBE_POISON_BATCH_CARD_NAMES,
)
from .tribe_poison_batch import (
    build_review_scenario as build_tribe_poison_batch_scenario,
)
from .weapon_batch import AUTHORING_METADATA as WEAPON_BATCH_METADATA
from .weapon_batch import SCENARIO_CARD_NAMES_ZH as WEAPON_BATCH_CARD_NAMES
from .weapon_batch import build_review_scenario as build_weapon_batch_scenario

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
SCENARIO_BUILDERS: Dict[str, Callable[[Dict[str, CardDef]], Dict[str, Any]]] = {
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
    CARD_MODULES[keyword_card_id] = "src/cardlab/authoring/generated/keyword_batch.py"
    CARD_METADATA[keyword_card_id] = keyword_metadata
    SCENARIO_BUILDERS[keyword_card_id] = partial(build_keyword_batch_scenario, keyword_card_id)
    SCENARIO_CARD_NAME_CATALOGS[keyword_card_id] = KEYWORD_BATCH_CARD_NAMES

for damage_card_id, damage_metadata in DAMAGE_BATCH_METADATA.items():
    CARD_MODULES[damage_card_id] = "src/cardlab/authoring/generated/damage_batch.py"
    CARD_METADATA[damage_card_id] = damage_metadata
    SCENARIO_BUILDERS[damage_card_id] = partial(build_damage_batch_scenario, damage_card_id)
    SCENARIO_CARD_NAME_CATALOGS[damage_card_id] = DAMAGE_BATCH_CARD_NAMES

for status_card_id, status_metadata in STATUS_BATCH_METADATA.items():
    CARD_MODULES[status_card_id] = "src/cardlab/authoring/generated/status_batch.py"
    CARD_METADATA[status_card_id] = status_metadata
    SCENARIO_BUILDERS[status_card_id] = partial(build_status_batch_scenario, status_card_id)
    SCENARIO_CARD_NAME_CATALOGS[status_card_id] = STATUS_BATCH_CARD_NAMES

for tribe_card_id, tribe_metadata in TRIBE_POISON_BATCH_METADATA.items():
    CARD_MODULES[tribe_card_id] = "src/cardlab/authoring/generated/tribe_poison_batch.py"
    CARD_METADATA[tribe_card_id] = tribe_metadata
    SCENARIO_BUILDERS[tribe_card_id] = partial(build_tribe_poison_batch_scenario, tribe_card_id)
    SCENARIO_CARD_NAME_CATALOGS[tribe_card_id] = TRIBE_POISON_BATCH_CARD_NAMES

for advanced_card_id, advanced_metadata in ADVANCED_STATUS_BATCH_METADATA.items():
    CARD_MODULES[advanced_card_id] = "src/cardlab/authoring/generated/advanced_status_batch.py"
    CARD_METADATA[advanced_card_id] = advanced_metadata
    SCENARIO_BUILDERS[advanced_card_id] = partial(
        build_advanced_status_batch_scenario, advanced_card_id
    )
    SCENARIO_CARD_NAME_CATALOGS[advanced_card_id] = ADVANCED_STATUS_BATCH_CARD_NAMES

for weapon_card_id, weapon_metadata in WEAPON_BATCH_METADATA.items():
    CARD_MODULES[weapon_card_id] = "src/cardlab/authoring/generated/weapon_batch.py"
    CARD_METADATA[weapon_card_id] = weapon_metadata
    SCENARIO_BUILDERS[weapon_card_id] = partial(build_weapon_batch_scenario, weapon_card_id)
    SCENARIO_CARD_NAME_CATALOGS[weapon_card_id] = WEAPON_BATCH_CARD_NAMES

for (
    conditional_weapon_card_id,
    conditional_weapon_metadata,
) in CONDITIONAL_WEAPON_BATCH_METADATA.items():
    CARD_MODULES[conditional_weapon_card_id] = (
        "src/cardlab/authoring/generated/conditional_weapon_batch.py"
    )
    CARD_METADATA[conditional_weapon_card_id] = conditional_weapon_metadata
    SCENARIO_BUILDERS[conditional_weapon_card_id] = partial(
        build_conditional_weapon_batch_scenario, conditional_weapon_card_id
    )
    SCENARIO_CARD_NAME_CATALOGS[conditional_weapon_card_id] = CONDITIONAL_WEAPON_BATCH_CARD_NAMES

for summon_card_id, summon_metadata in SUMMON_BATCH_METADATA.items():
    CARD_MODULES[summon_card_id] = "src/cardlab/authoring/generated/summon_batch.py"
    CARD_METADATA[summon_card_id] = summon_metadata
    SCENARIO_BUILDERS[summon_card_id] = partial(build_summon_batch_scenario, summon_card_id)
    SCENARIO_CARD_NAME_CATALOGS[summon_card_id] = SUMMON_BATCH_CARD_NAMES

for deathrattle_card_id, deathrattle_metadata in DEATHRATTLE_BATCH_METADATA.items():
    CARD_MODULES[deathrattle_card_id] = "src/cardlab/authoring/generated/deathrattle_batch.py"
    CARD_METADATA[deathrattle_card_id] = deathrattle_metadata
    SCENARIO_BUILDERS[deathrattle_card_id] = partial(
        build_deathrattle_batch_scenario, deathrattle_card_id
    )
    SCENARIO_CARD_NAME_CATALOGS[deathrattle_card_id] = DEATHRATTLE_BATCH_CARD_NAMES

for composite_card_id, composite_metadata in COMPOSITE_SPELL_BATCH_METADATA.items():
    CARD_MODULES[composite_card_id] = "src/cardlab/authoring/generated/composite_spell_batch.py"
    CARD_METADATA[composite_card_id] = composite_metadata
    SCENARIO_BUILDERS[composite_card_id] = partial(
        build_composite_spell_batch_scenario, composite_card_id
    )
    SCENARIO_CARD_NAME_CATALOGS[composite_card_id] = COMPOSITE_SPELL_BATCH_CARD_NAMES

for dynamic_card_id, dynamic_metadata in DYNAMIC_ZONE_BATCH_METADATA.items():
    CARD_MODULES[dynamic_card_id] = "src/cardlab/authoring/generated/dynamic_zone_batch.py"
    CARD_METADATA[dynamic_card_id] = dynamic_metadata
    SCENARIO_BUILDERS[dynamic_card_id] = partial(build_dynamic_zone_batch_scenario, dynamic_card_id)
    SCENARIO_CARD_NAME_CATALOGS[dynamic_card_id] = DYNAMIC_ZONE_BATCH_CARD_NAMES

for event_card_id, event_metadata in EVENT_TRIGGER_BATCH_METADATA.items():
    CARD_MODULES[event_card_id] = "src/cardlab/authoring/generated/event_trigger_batch.py"
    CARD_METADATA[event_card_id] = event_metadata
    SCENARIO_BUILDERS[event_card_id] = partial(build_event_trigger_batch_scenario, event_card_id)
    SCENARIO_CARD_NAME_CATALOGS[event_card_id] = EVENT_TRIGGER_BATCH_CARD_NAMES


def build_review_artifact(store: ReviewStore, card_id: str) -> Dict[str, Any]:
    card = store.get_card(card_id)
    if not card["ready_to_generate"]:
        raise ValueError("card must pass authoring review and generation approval")
    try:
        definition = GENERATED_CARDS[card_id]
        metadata = CARD_METADATA[card_id]
        scenario_builder = SCENARIO_BUILDERS[card_id]
    except KeyError as error:
        raise ValueError(
            "generated implementation is not registered: {}".format(card_id)
        ) from error
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
