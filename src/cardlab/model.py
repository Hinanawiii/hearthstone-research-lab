from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class CardType(str, Enum):
    MINION = "minion"
    SPELL = "spell"


class TargetMode(str, Enum):
    NONE = "none"
    ANY_CHARACTER = "any_character"
    ENEMY_CHARACTER = "enemy_character"
    FRIENDLY_MINION = "friendly_minion"


class ActionType(str, Enum):
    PLAY = "play"
    ATTACK = "attack"
    HERO_POWER = "hero_power"
    END_TURN = "end_turn"


@dataclass(frozen=True)
class Effect:
    kind: str
    amount: int = 0
    target: str = "selected"
    repeats: int = 1


@dataclass(frozen=True)
class CardDef:
    card_id: str
    name: str
    card_type: CardType
    cost: int
    attack: int = 0
    health: int = 0
    taunt: bool = False
    charge: bool = False
    target_mode: TargetMode = TargetMode.NONE
    effects: Tuple[Effect, ...] = ()
    collectible: bool = True
    stealth: bool = False
    lifesteal: bool = False
    reborn: bool = False
    elusive: bool = False
    rush: bool = False
    divine_shield: bool = False
    overload: int = 0


@dataclass
class HandCard:
    entity_id: int
    card_id: str


@dataclass
class Minion:
    entity_id: int
    card_id: str
    attack: int
    health: int
    max_health: int
    taunt: bool = False
    charge: bool = False
    attacks_this_turn: int = 0
    summoned_turn: int = 0
    stealth: bool = False
    lifesteal: bool = False
    reborn: bool = False
    elusive: bool = False
    rush: bool = False
    divine_shield: bool = False

    def can_attack(self, turn: int) -> bool:
        rested = self.summoned_turn < turn or self.charge or self.rush
        return self.attack > 0 and self.health > 0 and self.attacks_this_turn == 0 and rested


@dataclass
class PlayerState:
    hero_health: int = 30
    max_mana: int = 0
    mana: int = 0
    temporary_mana: int = 0
    fatigue: int = 0
    hero_power_used: bool = False
    deck: List[str] = field(default_factory=list)
    hand: List[HandCard] = field(default_factory=list)
    board: List[Minion] = field(default_factory=list)
    overload_pending: int = 0
    overloaded_mana: int = 0


@dataclass(frozen=True)
class TargetRef:
    player: int
    kind: str
    entity_id: Optional[int] = None

    @classmethod
    def hero(cls, player: int) -> "TargetRef":
        return cls(player=player, kind="hero")

    @classmethod
    def minion(cls, player: int, entity_id: int) -> "TargetRef":
        return cls(player=player, kind="minion", entity_id=entity_id)


@dataclass(frozen=True)
class Action:
    action_type: ActionType
    source_id: Optional[int] = None
    target: Optional[TargetRef] = None

    @classmethod
    def end_turn(cls) -> "Action":
        return cls(ActionType.END_TURN)

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "action_type": self.action_type.value,
            "source_id": self.source_id,
        }
        data["target"] = asdict(self.target) if self.target else None
        return data


@dataclass
class GameState:
    players: List[PlayerState]
    active_player: int = 0
    turn: int = 0
    winner: Optional[int] = None
    terminal_reason: Optional[str] = None

    @property
    def terminal(self) -> bool:
        return self.winner is not None or self.terminal_reason == "draw"
