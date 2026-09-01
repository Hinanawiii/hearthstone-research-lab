from __future__ import annotations

from dataclasses import fields
from typing import Dict, Iterable, Iterator, Tuple

from ...cards import CARDS
from ...model import CardDef, Effect
from .advanced_status_batch import CARDS as ADVANCED_STATUS_BATCH_CARDS
from .aura_hand_random_batch import CARDS as AURA_HAND_RANDOM_BATCH_CARDS
from .choose_one_batch import CARDS as CHOOSE_ONE_BATCH_CARDS
from .choose_one_batch import TOKEN_CARDS as CHOOSE_ONE_BATCH_TOKEN_CARDS
from .composite_spell_batch import CARDS as COMPOSITE_SPELL_BATCH_CARDS
from .composite_unique_batch import CARDS as COMPOSITE_UNIQUE_BATCH_CARDS
from .composite_unique_batch import TOKEN_CARDS as COMPOSITE_UNIQUE_BATCH_TOKEN_CARDS
from .conditional_state_batch import CARDS as CONDITIONAL_STATE_BATCH_CARDS
from .conditional_state_batch import TOKEN_CARDS as CONDITIONAL_STATE_BATCH_TOKEN_CARDS
from .conditional_weapon_batch import CARDS as CONDITIONAL_WEAPON_BATCH_CARDS
from .core_cs2_023 import CARD as CORE_CS2_023
from .core_cs2_179 import CARD as CORE_CS2_179
from .core_ds1_185 import CARD as CORE_DS1_185
from .corpse_batch import CARDS as CORPSE_BATCH_CARDS
from .corpse_batch import TOKEN_CARDS as CORPSE_BATCH_TOKEN_CARDS
from .damage_batch import CARDS as DAMAGE_BATCH_CARDS
from .death_history_batch import CARDS as DEATH_HISTORY_BATCH_CARDS
from .death_history_batch import TOKEN_CARDS as DEATH_HISTORY_BATCH_TOKEN_CARDS
from .deathrattle_batch import CARDS as DEATHRATTLE_BATCH_CARDS
from .deathrattle_batch import TOKEN_CARDS as DEATHRATTLE_BATCH_TOKEN_CARDS
from .discovery_generation_batch import CARDS as DISCOVERY_GENERATION_BATCH_CARDS
from .dynamic_zone_batch import CARDS as DYNAMIC_ZONE_BATCH_CARDS
from .dynamic_zone_batch import TOKEN_CARDS as DYNAMIC_ZONE_BATCH_TOKEN_CARDS
from .event_history_mechanics_batch import CARDS as EVENT_HISTORY_MECHANICS_BATCH_CARDS
from .event_history_mechanics_batch import (
    TOKEN_CARDS as EVENT_HISTORY_MECHANICS_BATCH_TOKEN_CARDS,
)
from .event_trigger_batch import CARDS as EVENT_TRIGGER_BATCH_CARDS
from .event_trigger_batch import TOKEN_CARDS as EVENT_TRIGGER_BATCH_TOKEN_CARDS
from .hand_history_unique_batch import CARDS as HAND_HISTORY_UNIQUE_BATCH_CARDS
from .hero_weapon_mechanics_batch import CARDS as HERO_WEAPON_MECHANICS_BATCH_CARDS
from .keyword_batch import CARDS as KEYWORD_BATCH_CARDS
from .random_summon_batch import CARDS as RANDOM_SUMMON_BATCH_CARDS
from .random_summon_batch import TOKEN_CARDS as RANDOM_SUMMON_BATCH_TOKEN_CARDS
from .rlk_709 import CARD as RLK_709
from .rune_location_batch import CARDS as RUNE_LOCATION_BATCH_CARDS
from .secret_batch import CARDS as SECRET_BATCH_CARDS
from .secret_batch import TOKEN_CARDS as SECRET_BATCH_TOKEN_CARDS
from .special_action_batch import CARDS as SPECIAL_ACTION_BATCH_CARDS
from .special_action_batch import TOKEN_CARDS as SPECIAL_ACTION_BATCH_TOKEN_CARDS
from .special_zone_mechanics_batch import CARDS as SPECIAL_ZONE_MECHANICS_BATCH_CARDS
from .status_batch import CARDS as STATUS_BATCH_CARDS
from .summon_batch import CARDS as SUMMON_BATCH_CARDS
from .summon_batch import TOKEN_CARDS as SUMMON_BATCH_TOKEN_CARDS
from .tribe_poison_batch import CARDS as TRIBE_POISON_BATCH_CARDS
from .weapon_batch import CARDS as WEAPON_BATCH_CARDS
from .zone_summon_batch import CARDS as ZONE_SUMMON_BATCH_CARDS

GENERATED_CARDS: Dict[str, CardDef] = {
    card.card_id: card for card in (RLK_709, CORE_DS1_185, CORE_CS2_023, CORE_CS2_179)
}
GENERATED_CARDS.update(KEYWORD_BATCH_CARDS)
GENERATED_CARDS.update(DAMAGE_BATCH_CARDS)
GENERATED_CARDS.update(STATUS_BATCH_CARDS)
GENERATED_CARDS.update(TRIBE_POISON_BATCH_CARDS)
GENERATED_CARDS.update(ADVANCED_STATUS_BATCH_CARDS)
GENERATED_CARDS.update(AURA_HAND_RANDOM_BATCH_CARDS)
GENERATED_CARDS.update(WEAPON_BATCH_CARDS)
GENERATED_CARDS.update(CONDITIONAL_WEAPON_BATCH_CARDS)
GENERATED_CARDS.update(SUMMON_BATCH_CARDS)
GENERATED_CARDS.update(DEATHRATTLE_BATCH_CARDS)
GENERATED_CARDS.update(DISCOVERY_GENERATION_BATCH_CARDS)
GENERATED_CARDS.update(COMPOSITE_SPELL_BATCH_CARDS)
GENERATED_CARDS.update(COMPOSITE_UNIQUE_BATCH_CARDS)
GENERATED_CARDS.update(CHOOSE_ONE_BATCH_CARDS)
GENERATED_CARDS.update(CONDITIONAL_STATE_BATCH_CARDS)
GENERATED_CARDS.update(DYNAMIC_ZONE_BATCH_CARDS)
GENERATED_CARDS.update(EVENT_TRIGGER_BATCH_CARDS)
GENERATED_CARDS.update(EVENT_HISTORY_MECHANICS_BATCH_CARDS)
GENERATED_CARDS.update(HERO_WEAPON_MECHANICS_BATCH_CARDS)
GENERATED_CARDS.update(HAND_HISTORY_UNIQUE_BATCH_CARDS)
GENERATED_CARDS.update(SPECIAL_ACTION_BATCH_CARDS)
GENERATED_CARDS.update(SPECIAL_ZONE_MECHANICS_BATCH_CARDS)
GENERATED_CARDS.update(CORPSE_BATCH_CARDS)
GENERATED_CARDS.update(RANDOM_SUMMON_BATCH_CARDS)
GENERATED_CARDS.update(ZONE_SUMMON_BATCH_CARDS)
GENERATED_CARDS.update(DEATH_HISTORY_BATCH_CARDS)
GENERATED_CARDS.update(RUNE_LOCATION_BATCH_CARDS)
GENERATED_CARDS.update(SECRET_BATCH_CARDS)

GENERATED_TOKEN_CARDS: Dict[str, CardDef] = dict(SUMMON_BATCH_TOKEN_CARDS)
GENERATED_TOKEN_CARDS.update(CHOOSE_ONE_BATCH_TOKEN_CARDS)
GENERATED_TOKEN_CARDS.update(CONDITIONAL_STATE_BATCH_TOKEN_CARDS)
GENERATED_TOKEN_CARDS.update(DEATHRATTLE_BATCH_TOKEN_CARDS)
GENERATED_TOKEN_CARDS.update(DYNAMIC_ZONE_BATCH_TOKEN_CARDS)
GENERATED_TOKEN_CARDS.update(EVENT_TRIGGER_BATCH_TOKEN_CARDS)
GENERATED_TOKEN_CARDS.update(EVENT_HISTORY_MECHANICS_BATCH_TOKEN_CARDS)
GENERATED_TOKEN_CARDS.update(SPECIAL_ACTION_BATCH_TOKEN_CARDS)
GENERATED_TOKEN_CARDS.update(CORPSE_BATCH_TOKEN_CARDS)
GENERATED_TOKEN_CARDS.update(RANDOM_SUMMON_BATCH_TOKEN_CARDS)
GENERATED_TOKEN_CARDS.update(DEATH_HISTORY_BATCH_TOKEN_CARDS)
GENERATED_TOKEN_CARDS.update(SECRET_BATCH_TOKEN_CARDS)
GENERATED_TOKEN_CARDS.update(COMPOSITE_UNIQUE_BATCH_TOKEN_CARDS)


def _iter_effects(value: object) -> Iterator[Effect]:
    if isinstance(value, Effect):
        yield value
    elif isinstance(value, tuple):
        for item in value:
            yield from _iter_effects(item)


def referenced_card_ids(card: CardDef) -> Tuple[str, ...]:
    referenced = set()
    for field in fields(CardDef):
        for effect in _iter_effects(getattr(card, field.name)):
            if effect.card_id:
                referenced.add(effect.card_id)
            referenced.update(effect.card_ids)
    return tuple(sorted(referenced))


def generated_dependencies(card_id: str) -> Dict[str, CardDef]:
    try:
        card = GENERATED_CARDS[card_id]
    except KeyError as error:
        raise ValueError("unknown generated card: {}".format(card_id)) from error
    available = dict(CARDS)
    available.update(GENERATED_TOKEN_CARDS)
    available.update(GENERATED_CARDS)
    dependencies: Dict[str, CardDef] = {}
    pending = list(referenced_card_ids(card))
    while pending:
        dependency_id = pending.pop(0)
        if dependency_id == card_id:
            continue
        if dependency_id in dependencies:
            continue
        try:
            dependencies[dependency_id] = available[dependency_id]
        except KeyError as error:
            raise ValueError(
                "generated card {} references undefined dependency {}".format(
                    card_id, dependency_id
                )
            ) from error
        pending.extend(referenced_card_ids(dependencies[dependency_id]))
    return dependencies


def runtime_registry(card_ids: Iterable[str]) -> Dict[str, CardDef]:
    registry = dict(CARDS)
    registry.update(GENERATED_TOKEN_CARDS)
    for card_id in card_ids:
        try:
            registry[card_id] = GENERATED_CARDS[card_id]
        except KeyError as error:
            raise ValueError("unknown generated card: {}".format(card_id)) from error
        registry.update(generated_dependencies(card_id))
    return registry


__all__ = [
    "CORE_CS2_023",
    "CORE_CS2_179",
    "CORE_DS1_185",
    "ADVANCED_STATUS_BATCH_CARDS",
    "AURA_HAND_RANDOM_BATCH_CARDS",
    "CONDITIONAL_STATE_BATCH_CARDS",
    "CONDITIONAL_STATE_BATCH_TOKEN_CARDS",
    "CONDITIONAL_WEAPON_BATCH_CARDS",
    "CORPSE_BATCH_CARDS",
    "CORPSE_BATCH_TOKEN_CARDS",
    "COMPOSITE_SPELL_BATCH_CARDS",
    "COMPOSITE_UNIQUE_BATCH_CARDS",
    "COMPOSITE_UNIQUE_BATCH_TOKEN_CARDS",
    "CHOOSE_ONE_BATCH_CARDS",
    "CHOOSE_ONE_BATCH_TOKEN_CARDS",
    "DAMAGE_BATCH_CARDS",
    "DEATHRATTLE_BATCH_CARDS",
    "DEATHRATTLE_BATCH_TOKEN_CARDS",
    "DISCOVERY_GENERATION_BATCH_CARDS",
    "DEATH_HISTORY_BATCH_CARDS",
    "DEATH_HISTORY_BATCH_TOKEN_CARDS",
    "DYNAMIC_ZONE_BATCH_CARDS",
    "DYNAMIC_ZONE_BATCH_TOKEN_CARDS",
    "EVENT_TRIGGER_BATCH_CARDS",
    "EVENT_TRIGGER_BATCH_TOKEN_CARDS",
    "EVENT_HISTORY_MECHANICS_BATCH_CARDS",
    "EVENT_HISTORY_MECHANICS_BATCH_TOKEN_CARDS",
    "GENERATED_CARDS",
    "GENERATED_TOKEN_CARDS",
    "HERO_WEAPON_MECHANICS_BATCH_CARDS",
    "HAND_HISTORY_UNIQUE_BATCH_CARDS",
    "KEYWORD_BATCH_CARDS",
    "RANDOM_SUMMON_BATCH_CARDS",
    "RANDOM_SUMMON_BATCH_TOKEN_CARDS",
    "RLK_709",
    "RUNE_LOCATION_BATCH_CARDS",
    "SECRET_BATCH_CARDS",
    "SECRET_BATCH_TOKEN_CARDS",
    "SPECIAL_ACTION_BATCH_CARDS",
    "SPECIAL_ACTION_BATCH_TOKEN_CARDS",
    "SPECIAL_ZONE_MECHANICS_BATCH_CARDS",
    "STATUS_BATCH_CARDS",
    "SUMMON_BATCH_CARDS",
    "SUMMON_BATCH_TOKEN_CARDS",
    "TRIBE_POISON_BATCH_CARDS",
    "WEAPON_BATCH_CARDS",
    "ZONE_SUMMON_BATCH_CARDS",
    "generated_dependencies",
    "referenced_card_ids",
    "runtime_registry",
]
