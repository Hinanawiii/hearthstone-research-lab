from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class CardType(str, Enum):
    MINION = "minion"
    SPELL = "spell"
    WEAPON = "weapon"
    LOCATION = "location"


class TargetMode(str, Enum):
    NONE = "none"
    ANY_CHARACTER = "any_character"
    ANY_MINION = "any_minion"
    ENEMY_CHARACTER = "enemy_character"
    ENEMY_MINION = "enemy_minion"
    FRIENDLY_MINION = "friendly_minion"
    FRIENDLY_CHARACTER = "friendly_character"
    FRIENDLY_UNDEAD = "friendly_undead"
    DAMAGED_ENEMY_MINION = "damaged_enemy_minion"
    UNDAMAGED_MINION = "undamaged_minion"
    ENEMY_TAUNT_MINION = "enemy_taunt_minion"
    HIGH_ATTACK_MINION = "high_attack_minion"


class ActionType(str, Enum):
    PLAY = "play"
    TRADE = "trade"
    ATTACK = "attack"
    HERO_ATTACK = "hero_attack"
    HERO_POWER = "hero_power"
    DISCOVER = "discover"
    END_TURN = "end_turn"


@dataclass(frozen=True)
class Effect:
    kind: str
    amount: int = 0
    target: str = "selected"
    repeats: int = 1
    attack: int = 0
    health: int = 0
    keyword: str = ""
    keywords: Tuple[str, ...] = ()
    race: str = ""
    card_id: str = ""
    card_ids: Tuple[str, ...] = ()
    corpse_cost: int = 0


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
    on_damage_effects: Tuple[Effect, ...] = ()
    deathrattle_effects: Tuple[Effect, ...] = ()
    on_owner_spell_cast_effects: Tuple[Effect, ...] = ()
    on_owner_hero_power_effects: Tuple[Effect, ...] = ()
    on_owner_hero_attack_effects: Tuple[Effect, ...] = ()
    on_owner_turn_end_effects: Tuple[Effect, ...] = ()
    on_owner_turn_start_effects: Tuple[Effect, ...] = ()
    on_each_turn_start_effects: Tuple[Effect, ...] = ()
    on_owner_draw_effects: Tuple[Effect, ...] = ()
    on_friendly_play_effects: Tuple[Effect, ...] = ()
    on_friendly_play_race: str = ""
    on_owner_spell_cast_school: str = ""
    on_friendly_summon_effects: Tuple[Effect, ...] = ()
    on_friendly_summon_race: str = ""
    on_any_minion_damaged_effects: Tuple[Effect, ...] = ()
    on_attacked_effects: Tuple[Effect, ...] = ()
    on_attack_effects: Tuple[Effect, ...] = ()
    collectible: bool = True
    stealth: bool = False
    lifesteal: bool = False
    reborn: bool = False
    elusive: bool = False
    rush: bool = False
    divine_shield: bool = False
    poisonous: bool = False
    races: Tuple[str, ...] = ()
    durability: int = 0
    requires_weapon: bool = False
    target_condition: str = ""
    target_optional_if_unavailable: bool = False
    overload: int = 0
    spell_school: str = ""
    damaged_attack_bonus: int = 0
    opponent_turn_attack_bonus: int = 0
    weapon_attack_bonus: int = 0
    charge_if_weapon: bool = False
    freezes_damaged_characters: bool = False
    aura_attack: int = 0
    aura_health: int = 0
    aura_race: str = ""
    aura_adjacent_only: bool = False
    tradeable: bool = False
    outcast_effects: Tuple[Effect, ...] = ()
    outcast_cost: int = -1
    combo_effects: Tuple[Effect, ...] = ()
    choose_one_effects: Tuple[Tuple[Effect, ...], ...] = ()
    choose_one_target_modes: Tuple[TargetMode, ...] = ()
    leaves_corpse: bool = True
    summon_multiplier: int = 1
    rarity: str = ""
    casts_when_drawn: bool = False
    runes: Tuple[str, ...] = ()
    spends_corpses: bool = False
    corpse_gain_multiplier: int = 1
    cost_reduction_by_weapon_attack: bool = False
    resummon_killed_minions_on_death: bool = False
    weapon_attack_equals_armor: bool = False
    weapon_cannot_attack_heroes: bool = False
    prevents_hero_damage_by_losing_durability: bool = False
    randomizes_character_targets: bool = False


@dataclass
class HandCard:
    entity_id: int
    card_id: str
    attack_bonus: int = 0
    health_bonus: int = 0
    cost_modifier: int = 0
    outside_starting_deck: bool = False


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
    poisonous: bool = False
    races: Tuple[str, ...] = ()
    frozen: bool = False
    temporary_attack: int = 0
    temporary_attack_expires_turn: Optional[int] = None
    active_damaged_attack_bonus: int = 0
    active_opponent_turn_attack_bonus: int = 0
    active_weapon_attack_bonus: int = 0
    active_aura_attack_bonus: int = 0
    active_aura_health_bonus: int = 0
    attached_deathrattle_effects: Tuple[Effect, ...] = ()

    def can_attack_ignoring_freeze(self, turn: int) -> bool:
        rested = self.summoned_turn < turn or self.charge or self.rush
        return self.attack > 0 and self.health > 0 and self.attacks_this_turn == 0 and rested

    def can_attack(self, turn: int) -> bool:
        return not self.frozen and self.can_attack_ignoring_freeze(turn)


@dataclass
class Weapon:
    entity_id: int
    card_id: str
    attack: int
    durability: int
    lifesteal: bool = False
    cannot_attack_heroes: bool = False
    killed_minion_card_ids: Tuple[str, ...] = ()


@dataclass
class Location:
    entity_id: int
    card_id: str
    durability: int
    cooldown: int = 0


@dataclass
class PlayerState:
    hero_health: int = 30
    hero_armor: int = 0
    hero_attack: int = 0
    hero_temporary_attack: int = 0
    hero_attacks_this_turn: int = 0
    hero_frozen: bool = False
    max_mana: int = 0
    mana: int = 0
    temporary_mana: int = 0
    fatigue: int = 0
    hero_power_used: bool = False
    deck: List[str] = field(default_factory=list)
    deck_outside_starting: List[bool] = field(default_factory=list)
    hand: List[HandCard] = field(default_factory=list)
    board: List[Minion] = field(default_factory=list)
    weapon: Optional[Weapon] = None
    locations: List[Location] = field(default_factory=list)
    overload_pending: int = 0
    overloaded_mana: int = 0
    cards_played_this_turn: int = 0
    corpses: int = 0
    graveyard: List[str] = field(default_factory=list)
    friendly_undead_died_since_last_turn: bool = False
    spells_played_this_turn: List[str] = field(default_factory=list)
    spells_played_previous_turn: List[str] = field(default_factory=list)


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
    choice: Optional[int] = None

    @classmethod
    def end_turn(cls) -> "Action":
        return cls(ActionType.END_TURN)

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "action_type": self.action_type.value,
            "source_id": self.source_id,
        }
        data["target"] = asdict(self.target) if self.target else None
        data["choice"] = self.choice
        return data


@dataclass
class GameState:
    players: List[PlayerState]
    active_player: int = 0
    turn: int = 0
    winner: Optional[int] = None
    terminal_reason: Optional[str] = None
    pending_discover_player: Optional[int] = None
    pending_discover_options: Tuple[str, ...] = ()
    pending_discover_from_deck: bool = False
    pending_discover_attack_bonus: int = 0
    pending_discover_health_bonus: int = 0
    pending_discover_heal_by_cost: bool = False

    @property
    def terminal(self) -> bool:
        return self.winner is not None or self.terminal_reason == "draw"
