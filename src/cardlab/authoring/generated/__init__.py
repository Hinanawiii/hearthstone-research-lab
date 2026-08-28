from __future__ import annotations

from typing import Dict, Iterable

from ...cards import CARDS
from ...model import CardDef
from .core_cs2_023 import CARD as CORE_CS2_023
from .core_cs2_179 import CARD as CORE_CS2_179
from .core_ds1_185 import CARD as CORE_DS1_185
from .rlk_709 import CARD as RLK_709

GENERATED_CARDS: Dict[str, CardDef] = {
    card.card_id: card
    for card in (RLK_709, CORE_DS1_185, CORE_CS2_023, CORE_CS2_179)
}


def runtime_registry(card_ids: Iterable[str]) -> Dict[str, CardDef]:
    registry = dict(CARDS)
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
    "GENERATED_CARDS",
    "RLK_709",
    "runtime_registry",
]
