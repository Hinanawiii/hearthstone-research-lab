from __future__ import annotations

from typing import Dict, Iterable

from ...cards import CARDS
from ...model import CardDef
from .rlk_709 import CARD as RLK_709

GENERATED_CARDS: Dict[str, CardDef] = {RLK_709.card_id: RLK_709}


def runtime_registry(card_ids: Iterable[str]) -> Dict[str, CardDef]:
    registry = dict(CARDS)
    for card_id in card_ids:
        try:
            registry[card_id] = GENERATED_CARDS[card_id]
        except KeyError as error:
            raise ValueError("unknown generated card: {}".format(card_id)) from error
    return registry


__all__ = ["GENERATED_CARDS", "RLK_709", "runtime_registry"]
