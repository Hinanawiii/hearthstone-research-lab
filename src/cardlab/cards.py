from __future__ import annotations

from typing import Dict, List

from .model import CardDef, CardType, Effect, TargetMode

CARD_POOL_VERSION = "legacy-mage-v1"


def _pool() -> List[CardDef]:
    return [
        CardDef("CS2_231", "Wisp", CardType.MINION, 0, 1, 1),
        CardDef(
            "CS2_189",
            "Elven Archer",
            CardType.MINION,
            1,
            1,
            1,
            target_mode=TargetMode.ANY_CHARACTER,
            effects=(Effect("damage", 1),),
        ),
        CardDef("CS1_042", "Goldshire Footman", CardType.MINION, 1, 1, 2, taunt=True),
        CardDef("CS2_172", "Bloodfen Raptor", CardType.MINION, 2, 3, 2),
        CardDef("CS2_120", "River Crocolisk", CardType.MINION, 2, 2, 3),
        CardDef(
            "EX1_015",
            "Novice Engineer",
            CardType.MINION,
            2,
            1,
            1,
            effects=(Effect("draw", 1, target="owner"),),
        ),
        CardDef("CS2_121", "Frostwolf Grunt", CardType.MINION, 2, 2, 2, taunt=True),
        CardDef("CS2_124", "Wolfrider", CardType.MINION, 3, 3, 1, charge=True),
        CardDef("CS2_182", "Chillwind Yeti", CardType.MINION, 4, 4, 5),
        CardDef("CS2_179", "Sen'jin Shieldmasta", CardType.MINION, 4, 3, 5, taunt=True),
        CardDef(
            "CS2_147",
            "Gnomish Inventor",
            CardType.MINION,
            4,
            2,
            4,
            effects=(Effect("draw", 1, target="owner"),),
        ),
        CardDef("CS2_200", "Boulderfist Ogre", CardType.MINION, 6, 6, 7),
        CardDef(
            "CS2_029",
            "Fireball",
            CardType.SPELL,
            4,
            target_mode=TargetMode.ANY_CHARACTER,
            effects=(Effect("damage", 6),),
        ),
        CardDef(
            "CS2_023",
            "Arcane Intellect",
            CardType.SPELL,
            3,
            effects=(Effect("draw", 2, target="owner"),),
        ),
        CardDef(
            "EX1_277",
            "Arcane Missiles",
            CardType.SPELL,
            1,
            effects=(Effect("random_damage", 1, target="enemy_character", repeats=3),),
        ),
        CardDef(
            "GAME_005",
            "The Coin",
            CardType.SPELL,
            0,
            effects=(Effect("temporary_mana", 1, target="owner"),),
            collectible=False,
        ),
    ]


CARDS: Dict[str, CardDef] = {card.card_id: card for card in _pool()}
DECK_CARD_IDS = tuple(card.card_id for card in CARDS.values() if card.collectible)


def default_deck() -> List[str]:
    """Return the symmetric 30-card reference deck (two copies per collectible card)."""
    return [card_id for card_id in DECK_CARD_IDS for _ in range(2)]

