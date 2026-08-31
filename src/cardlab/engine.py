from __future__ import annotations

import copy
import random
from dataclasses import asdict
from typing import Any, Dict, List, Mapping, Optional, Tuple

from .cards import CARDS, default_deck
from .model import (
    Action,
    ActionType,
    CardDef,
    CardType,
    GameState,
    HandCard,
    Minion,
    PlayerState,
    TargetMode,
    TargetRef,
)


class IllegalAction(ValueError):
    pass


class Game:
    """A deterministic, limited-pool Hearthstone-like rules engine.

    It intentionally models only the mechanics declared in docs/CARD_POOL.md. A seed and
    action sequence fully determine a match.
    """

    def __init__(
        self,
        seed: int = 0,
        decks: Optional[Tuple[List[str], List[str]]] = None,
        starting_player: int = 0,
        card_registry: Optional[Mapping[str, CardDef]] = None,
    ) -> None:
        self.seed = seed
        self.rng = random.Random(seed)
        self._next_entity_id = 1
        self.cards = dict(card_registry or CARDS)
        chosen = decks or (default_deck(), default_deck())
        self.state = GameState(
            players=[PlayerState(deck=list(chosen[0])), PlayerState(deck=list(chosen[1]))],
            active_player=starting_player,
        )
        self.history: List[Dict[str, Any]] = []
        self._validate_decks()
        self._setup()

    def _validate_decks(self) -> None:
        for deck in (player.deck for player in self.state.players):
            unknown = [card_id for card_id in deck if card_id not in self.cards]
            if unknown:
                raise ValueError("unknown card ids: {}".format(sorted(set(unknown))))

    def _setup(self) -> None:
        for player in self.state.players:
            self.rng.shuffle(player.deck)
        first = self.state.active_player
        second = 1 - first
        for _ in range(3):
            self._draw(first)
        for _ in range(4):
            self._draw(second)
        self._add_to_hand(second, "GAME_005")
        self._start_turn(first)

    def clone(self) -> "Game":
        return copy.deepcopy(self)

    def legal_actions(self, player: Optional[int] = None) -> List[Action]:
        if self.state.terminal:
            return []
        actor = self.state.active_player if player is None else player
        if actor != self.state.active_player:
            return []
        own = self.state.players[actor]
        actions: List[Action] = [Action.end_turn()]

        for hand_card in own.hand:
            card = self.cards[hand_card.card_id]
            if card.cost > own.mana + own.temporary_mana:
                continue
            if card.card_type == CardType.MINION and len(own.board) >= 7:
                continue
            for target in self._valid_targets(
                actor,
                card.target_mode,
                exclude_elusive=card.card_type == CardType.SPELL,
                exclude_enemy_stealth=True,
            ):
                actions.append(Action(ActionType.PLAY, hand_card.entity_id, target))
            if card.target_mode == TargetMode.NONE:
                actions.append(Action(ActionType.PLAY, hand_card.entity_id))

        enemy = 1 - actor
        taunts = [
            m
            for m in self.state.players[enemy].board
            if m.taunt and not m.stealth and m.health > 0
        ]
        attack_targets: List[TargetRef]
        if taunts:
            attack_targets = [TargetRef.minion(enemy, minion.entity_id) for minion in taunts]
        else:
            attack_targets = [TargetRef.hero(enemy)] + [
                TargetRef.minion(enemy, minion.entity_id)
                for minion in self.state.players[enemy].board
                if minion.health > 0 and not minion.stealth
            ]
        for minion in own.board:
            if minion.can_attack(self.state.turn):
                minion_targets = attack_targets
                if minion.rush and minion.summoned_turn == self.state.turn and not minion.charge:
                    minion_targets = [target for target in attack_targets if target.kind == "minion"]
                actions.extend(
                    Action(ActionType.ATTACK, minion.entity_id, target)
                    for target in minion_targets
                )

        if not own.hero_power_used and own.mana + own.temporary_mana >= 2:
            actions.extend(
                Action(ActionType.HERO_POWER, target=target)
                for target in self._valid_targets(
                    actor,
                    TargetMode.ANY_CHARACTER,
                    exclude_elusive=True,
                    exclude_enemy_stealth=True,
                )
            )
        return actions

    def apply(self, action: Action) -> None:
        if action not in self.legal_actions():
            raise IllegalAction("illegal action: {}".format(action.to_dict()))
        actor = self.state.active_player
        before = self.public_snapshot()
        if action.action_type == ActionType.END_TURN:
            self._end_turn()
        elif action.action_type == ActionType.PLAY:
            self._play_card(actor, action)
        elif action.action_type == ActionType.ATTACK:
            self._attack(actor, action)
        elif action.action_type == ActionType.HERO_POWER:
            self._spend_mana(self.state.players[actor], 2)
            self.state.players[actor].hero_power_used = True
            self._damage(action.target, 1)
            self._cleanup_deaths()
            self._check_terminal()
        else:
            raise IllegalAction("unknown action type")
        self.history.append(
            {
                "index": len(self.history),
                "actor": actor,
                "action": action.to_dict(),
                "before": before,
                "after": self.public_snapshot(),
            }
        )

    def _play_card(self, actor: int, action: Action) -> None:
        player = self.state.players[actor]
        hand_card = self._find_hand_card(actor, action.source_id)
        card = self.cards[hand_card.card_id]
        self._spend_mana(player, card.cost)
        player.hand.remove(hand_card)
        played_minion: Optional[TargetRef] = None
        if card.card_type == CardType.MINION:
            minion = Minion(
                entity_id=self._entity_id(),
                card_id=card.card_id,
                attack=card.attack,
                health=card.health,
                max_health=card.health,
                taunt=card.taunt,
                charge=card.charge,
                stealth=card.stealth,
                lifesteal=card.lifesteal,
                reborn=card.reborn,
                elusive=card.elusive,
                rush=card.rush,
                divine_shield=card.divine_shield,
                poisonous=card.poisonous,
                races=card.races,
                summoned_turn=self.state.turn,
            )
            player.board.append(minion)
            played_minion = TargetRef.minion(actor, minion.entity_id)
        player.overload_pending += card.overload
        self._resolve_effects(actor, card, action.target, played_minion)
        self._cleanup_deaths()
        self._check_terminal()

    def _resolve_effects(
        self,
        actor: int,
        card: CardDef,
        selected: Optional[TargetRef],
        played_minion: Optional[TargetRef],
    ) -> None:
        for effect in card.effects:
            if self.state.terminal:
                return
            if effect.kind == "damage":
                target = self._single_effect_target(
                    actor, effect.target, selected, played_minion
                )
                self._damage(target, effect.amount)
            elif effect.kind == "heal":
                target = self._single_effect_target(
                    actor, effect.target, selected, played_minion
                )
                self._heal(target, effect.amount)
            elif effect.kind == "buff":
                target = self._single_effect_target(
                    actor, effect.target, selected, played_minion
                )
                self._buff_minion(target, effect.attack, effect.health)
            elif effect.kind == "grant_keyword":
                target = self._single_effect_target(
                    actor, effect.target, selected, played_minion
                )
                self._grant_minion_keyword(target, effect.keyword)
            elif effect.kind == "armor":
                if effect.target != "owner_hero":
                    raise RuntimeError("unsupported armor target: {}".format(effect.target))
                self.state.players[actor].hero_armor += effect.amount
            elif effect.kind == "draw":
                for _ in range(effect.amount):
                    self._draw(actor)
            elif effect.kind == "temporary_mana":
                player = self.state.players[actor]
                room = max(0, 10 - player.mana - player.temporary_mana)
                player.temporary_mana += min(effect.amount, room)
            elif effect.kind == "random_damage":
                for _ in range(effect.repeats):
                    targets = self._enemy_characters(actor)
                    if not targets:
                        break
                    self._damage(self.rng.choice(targets), effect.amount)
                    self._cleanup_deaths()
                    self._check_terminal()
                    if self.state.terminal:
                        break
            elif effect.kind == "damage_all":
                targets = self._group_targets(actor, effect.target, played_minion)
                for target in targets:
                    self._damage(target, effect.amount)
                self._cleanup_deaths()
                self._check_terminal()
            elif effect.kind == "heal_all":
                for target in self._group_targets(actor, effect.target, played_minion):
                    self._heal(target, effect.amount)
            elif effect.kind == "buff_all":
                for target in self._group_targets(actor, effect.target, played_minion):
                    self._buff_minion(target, effect.attack, effect.health)
            elif effect.kind == "grant_keyword_all":
                for target in self._group_targets(actor, effect.target, played_minion):
                    self._grant_minion_keyword(target, effect.keyword)
            elif effect.kind == "set_health_all":
                for target in self._group_targets(actor, effect.target, played_minion):
                    minion = self._find_minion(target.player, target.entity_id)
                    minion.health = effect.amount
                    minion.max_health = effect.amount
            else:
                raise RuntimeError("unsupported effect: {}".format(effect.kind))

    @staticmethod
    def _single_effect_target(
        actor: int,
        target: str,
        selected: Optional[TargetRef],
        played_minion: Optional[TargetRef],
    ) -> Optional[TargetRef]:
        if target == "selected":
            return selected
        if target == "owner_hero":
            return TargetRef.hero(actor)
        if target == "enemy_hero":
            return TargetRef.hero(1 - actor)
        if target == "played_minion":
            return played_minion
        raise RuntimeError("unsupported single effect target: {}".format(target))

    def _group_targets(
        self,
        actor: int,
        target: str,
        played_minion: Optional[TargetRef],
    ) -> List[TargetRef]:
        if target == "enemy_characters":
            return self._enemy_characters(actor)
        if target == "enemy_minions":
            enemy = 1 - actor
            return [
                TargetRef.minion(enemy, minion.entity_id)
                for minion in self.state.players[enemy].board
                if minion.health > 0
            ]
        if target == "friendly_minions":
            return [
                TargetRef.minion(actor, minion.entity_id)
                for minion in self.state.players[actor].board
                if minion.health > 0
            ]
        if target == "friendly_characters":
            return [TargetRef.hero(actor)] + [
                TargetRef.minion(actor, minion.entity_id)
                for minion in self.state.players[actor].board
                if minion.health > 0
            ]
        if target == "all_minions":
            return [
                TargetRef.minion(player_index, minion.entity_id)
                for player_index, player in enumerate(self.state.players)
                for minion in player.board
                if minion.health > 0
            ]
        if target == "all_characters":
            return [TargetRef.hero(0), TargetRef.hero(1)] + [
                TargetRef.minion(player_index, minion.entity_id)
                for player_index, player in enumerate(self.state.players)
                for minion in player.board
                if minion.health > 0
            ]
        if target == "all_other_minions":
            return [
                TargetRef.minion(player_index, minion.entity_id)
                for player_index, player in enumerate(self.state.players)
                for minion in player.board
                if minion.health > 0
                and (
                    played_minion is None
                    or player_index != played_minion.player
                    or minion.entity_id != played_minion.entity_id
                )
            ]
        raise RuntimeError("unsupported group target: {}".format(target))

    def _attack(self, actor: int, action: Action) -> None:
        attacker = self._find_minion(actor, action.source_id)
        target = action.target
        if target is None:
            raise IllegalAction("attack requires target")
        attacker.attacks_this_turn += 1
        attacker.stealth = False
        if target.kind == "hero":
            damage_dealt = self._damage(target, attacker.attack)
        else:
            defender = self._find_minion(target.player, target.entity_id)
            defender_damage = defender.attack
            damage_dealt = self._damage(target, attacker.attack)
            defender_damage_dealt = self._damage(
                TargetRef.minion(actor, attacker.entity_id), defender_damage
            )
            if attacker.poisonous and damage_dealt > 0:
                defender.health = 0
            if defender.poisonous and defender_damage_dealt > 0:
                attacker.health = 0
            if defender.lifesteal and defender_damage_dealt > 0:
                defender_owner = self.state.players[target.player]
                defender_owner.hero_health = min(
                    30, defender_owner.hero_health + defender_damage_dealt
                )
        if attacker.lifesteal and damage_dealt > 0:
            owner = self.state.players[actor]
            owner.hero_health = min(30, owner.hero_health + damage_dealt)
        self._cleanup_deaths()
        self._check_terminal()

    def _end_turn(self) -> None:
        current = self.state.players[self.state.active_player]
        current.temporary_mana = 0
        current.overloaded_mana = 0
        self.state.active_player = 1 - self.state.active_player
        self._start_turn(self.state.active_player)

    def _start_turn(self, player_index: int) -> None:
        self.state.turn += 1
        player = self.state.players[player_index]
        player.max_mana = min(10, player.max_mana + 1)
        player.overloaded_mana = min(player.max_mana, player.overload_pending)
        player.overload_pending = 0
        player.mana = player.max_mana - player.overloaded_mana
        player.temporary_mana = 0
        player.hero_power_used = False
        for minion in player.board:
            minion.attacks_this_turn = 0
        self._draw(player_index)
        self._check_terminal()

    def _draw(self, player_index: int) -> None:
        player = self.state.players[player_index]
        if not player.deck:
            player.fatigue += 1
            player.hero_health -= player.fatigue
            return
        card_id = player.deck.pop()
        self._add_to_hand(player_index, card_id)

    def _add_to_hand(self, player_index: int, card_id: str) -> None:
        player = self.state.players[player_index]
        if len(player.hand) < 10:
            player.hand.append(HandCard(self._entity_id(), card_id))

    def _spend_mana(self, player: PlayerState, amount: int) -> None:
        temporary = min(player.temporary_mana, amount)
        player.temporary_mana -= temporary
        player.mana -= amount - temporary

    def _valid_targets(
        self,
        actor: int,
        mode: TargetMode,
        *,
        exclude_elusive: bool = False,
        exclude_enemy_stealth: bool = False,
    ) -> List[TargetRef]:
        if mode == TargetMode.NONE:
            return []
        if mode == TargetMode.FRIENDLY_MINION:
            return [
                TargetRef.minion(actor, m.entity_id)
                for m in self.state.players[actor].board
                if not exclude_elusive or not m.elusive
            ]
        if mode == TargetMode.FRIENDLY_UNDEAD:
            return [
                TargetRef.minion(actor, m.entity_id)
                for m in self.state.players[actor].board
                if "UNDEAD" in m.races and (not exclude_elusive or not m.elusive)
            ]
        if mode == TargetMode.ANY_MINION:
            return [
                TargetRef.minion(player_index, minion.entity_id)
                for player_index, player in enumerate(self.state.players)
                for minion in player.board
                if minion.health > 0
                and (not exclude_elusive or not minion.elusive)
                and (
                    not exclude_enemy_stealth
                    or player_index == actor
                    or not minion.stealth
                )
            ]
        if mode == TargetMode.ENEMY_CHARACTER:
            return self._enemy_characters(
                actor,
                exclude_elusive=exclude_elusive,
                exclude_stealth=exclude_enemy_stealth,
            )
        if mode == TargetMode.ANY_CHARACTER:
            targets = [TargetRef.hero(0), TargetRef.hero(1)]
            for player_index, player in enumerate(self.state.players):
                targets.extend(
                    TargetRef.minion(player_index, m.entity_id)
                    for m in player.board
                    if (not exclude_elusive or not m.elusive)
                    and (
                        not exclude_enemy_stealth
                        or player_index == actor
                        or not m.stealth
                    )
                )
            return targets
        raise RuntimeError("unknown target mode")

    def _enemy_characters(
        self,
        actor: int,
        *,
        exclude_elusive: bool = False,
        exclude_stealth: bool = False,
    ) -> List[TargetRef]:
        enemy = 1 - actor
        return [TargetRef.hero(enemy)] + [
            TargetRef.minion(enemy, minion.entity_id)
            for minion in self.state.players[enemy].board
            if minion.health > 0
            and (not exclude_elusive or not minion.elusive)
            and (not exclude_stealth or not minion.stealth)
        ]

    def _damage(self, target: Optional[TargetRef], amount: int) -> int:
        if target is None:
            raise IllegalAction("effect requires target")
        if target.kind == "hero":
            player = self.state.players[target.player]
            absorbed = min(player.hero_armor, amount)
            player.hero_armor -= absorbed
            player.hero_health -= amount - absorbed
            return amount
        elif target.kind == "minion":
            minion = self._find_minion(target.player, target.entity_id)
            if amount > 0 and minion.divine_shield:
                minion.divine_shield = False
                return 0
            minion.health -= amount
            return amount
        else:
            raise IllegalAction("unknown target kind")

    def _heal(self, target: Optional[TargetRef], amount: int) -> None:
        if target is None:
            raise IllegalAction("effect requires target")
        if target.kind == "hero":
            player = self.state.players[target.player]
            player.hero_health = min(30, player.hero_health + amount)
            return
        if target.kind == "minion":
            minion = self._find_minion(target.player, target.entity_id)
            minion.health = min(minion.max_health, minion.health + amount)
            return
        raise IllegalAction("unknown target kind")

    def _buff_minion(
        self, target: Optional[TargetRef], attack: int, health: int
    ) -> None:
        if target is None or target.kind != "minion":
            raise IllegalAction("buff requires a minion target")
        minion = self._find_minion(target.player, target.entity_id)
        minion.attack += attack
        minion.health += health
        minion.max_health += health

    def _grant_minion_keyword(self, target: Optional[TargetRef], keyword: str) -> None:
        if target is None or target.kind != "minion":
            raise IllegalAction("keyword effect requires a minion target")
        if keyword not in {"taunt", "elusive", "divine_shield", "poisonous"}:
            raise RuntimeError("unsupported granted keyword: {}".format(keyword))
        minion = self._find_minion(target.player, target.entity_id)
        setattr(minion, keyword, True)

    def _cleanup_deaths(self) -> None:
        for player in self.state.players:
            survivors: List[Minion] = []
            for minion in player.board:
                if minion.health > 0:
                    survivors.append(minion)
                elif minion.reborn:
                    card = self.cards[minion.card_id]
                    survivors.append(
                        Minion(
                            entity_id=self._entity_id(),
                            card_id=minion.card_id,
                            attack=card.attack,
                            health=1,
                            max_health=card.health,
                            taunt=card.taunt,
                            charge=card.charge,
                            stealth=card.stealth,
                            lifesteal=card.lifesteal,
                            reborn=False,
                            elusive=card.elusive,
                            rush=card.rush,
                            divine_shield=card.divine_shield,
                            poisonous=card.poisonous,
                            races=card.races,
                            summoned_turn=self.state.turn,
                        )
                    )
            player.board = survivors

    def _check_terminal(self) -> None:
        dead = [index for index, p in enumerate(self.state.players) if p.hero_health <= 0]
        if len(dead) == 2:
            self.state.winner = None
            self.state.terminal_reason = "draw"
        elif len(dead) == 1:
            self.state.winner = 1 - dead[0]
            self.state.terminal_reason = "hero_defeated"

    def _find_hand_card(self, player: int, entity_id: Optional[int]) -> HandCard:
        for card in self.state.players[player].hand:
            if card.entity_id == entity_id:
                return card
        raise IllegalAction("hand entity not found")

    def _find_minion(self, player: int, entity_id: Optional[int]) -> Minion:
        for minion in self.state.players[player].board:
            if minion.entity_id == entity_id:
                return minion
        raise IllegalAction("minion entity not found")

    def _entity_id(self) -> int:
        value = self._next_entity_id
        self._next_entity_id += 1
        return value

    def observation(self, player: int) -> Dict[str, Any]:
        """Return an information-safe player view; opponent hand and deck order stay hidden."""
        own = self.state.players[player]
        enemy = self.state.players[1 - player]
        return {
            "turn": self.state.turn,
            "active_player": self.state.active_player,
            "viewer": player,
            "own": self._player_public(own, include_hand=True),
            "enemy": self._player_public(enemy, include_hand=False),
            "terminal": self.state.terminal,
            "winner": self.state.winner,
        }

    def public_snapshot(self) -> Dict[str, Any]:
        return {
            "turn": self.state.turn,
            "active_player": self.state.active_player,
            "players": [self._player_public(p, include_hand=False) for p in self.state.players],
            "terminal": self.state.terminal,
            "winner": self.state.winner,
            "terminal_reason": self.state.terminal_reason,
        }

    @staticmethod
    def _player_public(player: PlayerState, include_hand: bool) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "hero_health": player.hero_health,
            "hero_armor": player.hero_armor,
            "max_mana": player.max_mana,
            "mana": player.mana,
            "temporary_mana": player.temporary_mana,
            "overload_pending": player.overload_pending,
            "overloaded_mana": player.overloaded_mana,
            "fatigue": player.fatigue,
            "hero_power_used": player.hero_power_used,
            "deck_count": len(player.deck),
            "hand_count": len(player.hand),
            "board": [asdict(minion) for minion in player.board],
        }
        if include_hand:
            data["hand"] = [asdict(card) for card in player.hand]
        return data


def play_game(
    policy_a: Any,
    policy_b: Any,
    seed: int = 0,
    max_actions: int = 500,
) -> Game:
    game = Game(seed=seed)
    policies = [policy_a, policy_b]
    for _ in range(max_actions):
        if game.state.terminal:
            break
        actor = game.state.active_player
        legal = game.legal_actions()
        action = policies[actor].choose(game.observation(actor), legal)
        game.apply(action)
    if not game.state.terminal:
        game.state.terminal_reason = "draw"
    return game
