from __future__ import annotations

from typing import Dict, Iterable

from ...cards import CARDS
from ...model import CardDef
from .advanced_status_batch import CARDS as ADVANCED_STATUS_BATCH_CARDS
from .composite_spell_batch import CARDS as COMPOSITE_SPELL_BATCH_CARDS
from .conditional_weapon_batch import CARDS as CONDITIONAL_WEAPON_BATCH_CARDS
from .core_cs2_023 import CARD as CORE_CS2_023
from .core_cs2_179 import CARD as CORE_CS2_179
from .core_ds1_185 import CARD as CORE_DS1_185
from .damage_batch import CARDS as DAMAGE_BATCH_CARDS
from .deathrattle_batch import CARDS as DEATHRATTLE_BATCH_CARDS
from .deathrattle_batch import TOKEN_CARDS as DEATHRATTLE_BATCH_TOKEN_CARDS
from .keyword_batch import CARDS as KEYWORD_BATCH_CARDS
from .rlk_709 import CARD as RLK_709
from .status_batch import CARDS as STATUS_BATCH_CARDS
from .summon_batch import CARDS as SUMMON_BATCH_CARDS
from .summon_batch import TOKEN_CARDS as SUMMON_BATCH_TOKEN_CARDS
from .tribe_poison_batch import CARDS as TRIBE_POISON_BATCH_CARDS
from .weapon_batch import CARDS as WEAPON_BATCH_CARDS

GENERATED_CARDS: Dict[str, CardDef] = {
    card.card_id: card
    for card in (RLK_709, CORE_DS1_185, CORE_CS2_023, CORE_CS2_179)
}
GENERATED_CARDS.update(KEYWORD_BATCH_CARDS)
GENERATED_CARDS.update(DAMAGE_BATCH_CARDS)
GENERATED_CARDS.update(STATUS_BATCH_CARDS)
GENERATED_CARDS.update(TRIBE_POISON_BATCH_CARDS)
GENERATED_CARDS.update(ADVANCED_STATUS_BATCH_CARDS)
GENERATED_CARDS.update(WEAPON_BATCH_CARDS)
GENERATED_CARDS.update(CONDITIONAL_WEAPON_BATCH_CARDS)
GENERATED_CARDS.update(SUMMON_BATCH_CARDS)
GENERATED_CARDS.update(DEATHRATTLE_BATCH_CARDS)
GENERATED_CARDS.update(COMPOSITE_SPELL_BATCH_CARDS)

GENERATED_TOKEN_CARDS: Dict[str, CardDef] = dict(SUMMON_BATCH_TOKEN_CARDS)
GENERATED_TOKEN_CARDS.update(DEATHRATTLE_BATCH_TOKEN_CARDS)


def runtime_registry(card_ids: Iterable[str]) -> Dict[str, CardDef]:
    registry = dict(CARDS)
    registry.update(GENERATED_TOKEN_CARDS)
    for card_id in card_ids:
        try:
            registry[card_id] = GENERATED_CARDS[card_id]
        except KeyError as error:
            raise ValueError("unknown generated card: {}".format(card_id)) from error
    return registry


__all__ = [
    "CORE_CS2_023",
    "CORE_CS2_179",
    "CORE_DS1_185",
    "ADVANCED_STATUS_BATCH_CARDS",
    "CONDITIONAL_WEAPON_BATCH_CARDS",
    "COMPOSITE_SPELL_BATCH_CARDS",
    "DAMAGE_BATCH_CARDS",
    "DEATHRATTLE_BATCH_CARDS",
    "DEATHRATTLE_BATCH_TOKEN_CARDS",
    "GENERATED_CARDS",
    "GENERATED_TOKEN_CARDS",
    "KEYWORD_BATCH_CARDS",
    "RLK_709",
    "STATUS_BATCH_CARDS",
    "SUMMON_BATCH_CARDS",
    "SUMMON_BATCH_TOKEN_CARDS",
    "TRIBE_POISON_BATCH_CARDS",
    "WEAPON_BATCH_CARDS",
    "runtime_registry",
]
