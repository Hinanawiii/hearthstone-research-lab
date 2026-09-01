from __future__ import annotations

import copy
import random
from dataclasses import asdict
from functools import partial
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

from .cards import CARDS, default_deck
from .model import (
    Action,
    ActionType,
    CardDef,
    CardType,
    Effect,
    GameState,
    HandCard,
    Location,
    Minion,
    PlayerState,
    TargetMode,
    TargetRef,
    Weapon,
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
        self._pending_damage_triggers: List[Tuple[int, Tuple[Effect, ...], TargetRef]] = []
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
        if self.state.pending_discover_player is not None:
            if actor != self.state.pending_discover_player:
                return []
            return [
                Action(ActionType.DISCOVER, choice=index)
                for index in range(len(self.state.pending_discover_options))
            ]
        own = self.state.players[actor]
        actions: List[Action] = [Action.end_turn()]

        for hand_card in own.hand:
            card = self.cards[hand_card.card_id]
            effective_cost = self._effective_card_cost(actor, hand_card, card)
            uses_health = card.pays_health_if_healed and own.healed_this_turn
            can_pay = (
                own.hero_health > effective_cost
                if uses_health
                else effective_cost <= own.mana + own.temporary_mana
            )
            if can_pay:
                if not card.requires_weapon or own.weapon is not None:
                    if card.card_type not in {CardType.MINION, CardType.LOCATION} or (
                        len(own.board) + len(own.locations) < 7
                    ):
                        if card.choose_one_effects:
                            if len(card.choose_one_effects) != len(card.choose_one_target_modes):
                                raise RuntimeError("choose-one effects and target modes differ")
                            if self._choose_both_active(actor):
                                combined_modes = [
                                    mode
                                    for mode in card.choose_one_target_modes
                                    if mode != TargetMode.NONE
                                ]
                                if combined_modes:
                                    combined_targets: List[TargetRef] = []
                                    for mode in combined_modes:
                                        for target in self._valid_targets(
                                            actor,
                                            mode,
                                            exclude_elusive=card.card_type == CardType.SPELL,
                                            exclude_enemy_stealth=True,
                                        ):
                                            if target not in combined_targets:
                                                combined_targets.append(target)
                                    actions.extend(
                                        Action(
                                            ActionType.PLAY,
                                            hand_card.entity_id,
                                            target,
                                            -1,
                                        )
                                        for target in combined_targets
                                    )
                                else:
                                    actions.append(
                                        Action(
                                            ActionType.PLAY,
                                            hand_card.entity_id,
                                            choice=-1,
                                        )
                                    )
                                continue
                            for choice, target_mode in enumerate(card.choose_one_target_modes):
                                targets = self._valid_targets(
                                    actor,
                                    target_mode,
                                    exclude_elusive=card.card_type == CardType.SPELL,
                                    exclude_enemy_stealth=True,
                                )
                                actions.extend(
                                    Action(
                                        ActionType.PLAY,
                                        hand_card.entity_id,
                                        target,
                                        choice,
                                    )
                                    for target in targets
                                )
                                if target_mode == TargetMode.NONE:
                                    actions.append(
                                        Action(
                                            ActionType.PLAY,
                                            hand_card.entity_id,
                                            choice=choice,
                                        )
                                    )
                        else:
                            target_mode = self._effective_target_mode(actor, card)
                            targets = self._valid_targets(
                                actor,
                                target_mode,
                                exclude_elusive=card.card_type == CardType.SPELL,
                                exclude_enemy_stealth=True,
                            )
                            for target in targets:
                                actions.append(Action(ActionType.PLAY, hand_card.entity_id, target))
                            if target_mode == TargetMode.NONE or (
                                card.target_optional_if_unavailable and not targets
                            ):
                                actions.append(Action(ActionType.PLAY, hand_card.entity_id))
            if card.tradeable and own.deck and own.mana + own.temporary_mana >= 1:
                actions.append(Action(ActionType.TRADE, hand_card.entity_id))

        attack_targets = self._attack_targets(actor)
        for location in own.locations:
            if location.cooldown > 0 or location.durability <= 0:
                continue
            definition = self.cards.get(location.card_id)
            if definition is None:
                continue
            targets = self._valid_targets(
                actor,
                definition.target_mode,
                exclude_elusive=False,
                exclude_enemy_stealth=True,
            )
            actions.extend(
                Action(ActionType.LOCATION, location.entity_id, target) for target in targets
            )
            if definition.target_mode == TargetMode.NONE:
                actions.append(Action(ActionType.LOCATION, location.entity_id))
        for minion in own.board:
            if minion.can_attack(self.state.turn):
                minion_targets = attack_targets
                if minion.rush and minion.summoned_turn == self.state.turn and not minion.charge:
                    minion_targets = [
                        target for target in attack_targets if target.kind == "minion"
                    ]
                actions.extend(
                    Action(ActionType.ATTACK, minion.entity_id, target) for target in minion_targets
                )
        if own.hero_attack > 0 and own.hero_attacks_this_turn == 0 and not own.hero_frozen:
            hero_attack_targets = attack_targets
            if own.weapon is not None and own.weapon.cannot_attack_heroes:
                hero_attack_targets = [
                    target for target in attack_targets if target.kind == "minion"
                ]
            actions.extend(
                Action(
                    ActionType.HERO_ATTACK,
                    own.weapon.entity_id if own.weapon is not None else None,
                    target,
                )
                for target in hero_attack_targets
            )

        hero_power_cost = 2 + own.next_hero_power_cost_increase
        if not own.hero_power_used and own.mana + own.temporary_mana >= hero_power_cost:
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
        action = self._randomize_action_target(actor, action)
        if action.action_type == ActionType.END_TURN:
            self._end_turn()
        elif action.action_type == ActionType.PLAY:
            self._play_card(actor, action)
        elif action.action_type == ActionType.TRADE:
            self._trade_card(actor, action)
        elif action.action_type == ActionType.ATTACK:
            self._attack(actor, action)
        elif action.action_type == ActionType.HERO_ATTACK:
            self._hero_attack(actor, action)
        elif action.action_type == ActionType.HERO_POWER:
            hero_power_cost = 2 + self.state.players[actor].next_hero_power_cost_increase
            self._spend_mana(self.state.players[actor], hero_power_cost)
            self.state.players[actor].next_hero_power_cost_increase = 0
            self.state.players[actor].hero_power_used = True
            self._damage(action.target, 1)
            self._resolve_damage_triggers()
            self._cleanup_deaths()
            self._resolve_board_triggers("owner_hero_power", owner=actor)
            self._cleanup_deaths()
            self._check_terminal()
        elif action.action_type == ActionType.DISCOVER:
            self._resolve_discover(actor, action)
        elif action.action_type == ActionType.LOCATION:
            self._activate_location(actor, action)
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
        was_outcast = self._is_outcast(player, hand_card)
        combo_active = player.cards_played_this_turn > 0
        effective_cost = self._effective_card_cost(actor, hand_card, card)
        if card.pays_health_if_healed and player.healed_this_turn:
            player.hero_health -= effective_cost
        else:
            self._spend_mana(player, effective_cost)
        player.hand.remove(hand_card)
        self._consume_cost_modifiers(player, card)
        played_minion: Optional[TargetRef] = None
        if card.card_type == CardType.MINION:
            minion = Minion(
                entity_id=self._entity_id(),
                card_id=card.card_id,
                attack=card.attack + hand_card.attack_bonus,
                health=card.health + hand_card.health_bonus,
                max_health=card.health + hand_card.health_bonus,
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
            self._refresh_dynamic_attack_bonuses()
        elif card.card_type == CardType.WEAPON:
            self._equip_weapon(actor, card.card_id)
        elif card.card_type == CardType.LOCATION:
            player.locations.append(
                Location(
                    entity_id=self._entity_id(),
                    card_id=card.card_id,
                    durability=card.durability,
                )
            )
        player.overload_pending += card.overload
        self._resolve_effects(actor, card, action.target, played_minion)
        spell_damage_bonus = self._spell_damage(actor) if card.card_type == CardType.SPELL else 0
        if card.choose_one_effects:
            if action.choice is None:
                raise IllegalAction("choose-one card requires a choice")
            choices = (
                card.choose_one_effects
                if action.choice == -1
                else (card.choose_one_effects[action.choice],)
            )
            for choice_effects in choices:
                self._resolve_effect_sequence(
                    actor,
                    choice_effects,
                    action.target,
                    played_minion,
                    spell_damage_bonus=spell_damage_bonus,
                )
        if was_outcast and card.outcast_effects:
            self._resolve_effect_sequence(
                actor,
                card.outcast_effects,
                action.target,
                played_minion,
                spell_damage_bonus=spell_damage_bonus,
            )
        if combo_active and card.combo_effects:
            self._resolve_effect_sequence(
                actor,
                card.combo_effects,
                action.target,
                played_minion,
                spell_damage_bonus=spell_damage_bonus,
            )
        player.cards_played_this_turn += 1
        self._cleanup_deaths()
        if card.card_type == CardType.SPELL:
            self._resolve_board_triggers(
                "owner_spell_cast",
                owner=actor,
                played_spell_school=card.spell_school,
            )
            self._resolve_board_triggers(
                "any_spell_cast",
                triggering_player=actor,
                triggering_card_id=card.card_id,
            )
            self._transform_dynamic_hand_cards(actor, card.card_id)
        elif card.card_type == CardType.MINION:
            player.minion_types_played_this_turn.extend(
                race for race in card.races if race not in player.minion_types_played_this_turn
            )
            self._resolve_board_triggers(
                "friendly_summon",
                owner=actor,
                exclude_entity=played_minion.entity_id if played_minion else None,
                played_races=card.races,
            )
            self._resolve_board_triggers(
                "friendly_play",
                owner=actor,
                exclude_entity=played_minion.entity_id if played_minion else None,
                played_races=card.races,
            )
        if card.card_type == CardType.SPELL:
            player.spells_played_this_turn.append(card.card_id)
        self._cleanup_deaths()
        self._check_terminal()

    def _trade_card(self, actor: int, action: Action) -> None:
        player = self.state.players[actor]
        hand_card = self._find_hand_card(actor, action.source_id)
        card = self.cards[hand_card.card_id]
        if not card.tradeable or not player.deck:
            raise IllegalAction("card cannot be traded")
        self._spend_mana(player, 1)
        player.hand.remove(hand_card)
        self._draw(actor)
        insertion_index = self.rng.randrange(len(player.deck) + 1)
        self._ensure_deck_origin_flags(player)
        player.deck.insert(insertion_index, hand_card.card_id)
        player.deck_outside_starting.insert(insertion_index, hand_card.outside_starting_deck)
        self._check_terminal()

    def _activate_location(self, actor: int, action: Action) -> None:
        location = self._find_location(actor, action.source_id)
        if location.cooldown > 0 or location.durability <= 0:
            raise IllegalAction("location is not ready")
        definition = self.cards[location.card_id]
        self._resolve_effect_sequence(actor, definition.effects, action.target, None)
        location.durability -= 1
        location.cooldown = 1
        if location.durability <= 0:
            self.state.players[actor].locations.remove(location)
        self._cleanup_deaths()
        self._check_terminal()

    def _resolve_discover(self, actor: int, action: Action) -> None:
        if self.state.pending_discover_player != actor or action.choice is None:
            raise IllegalAction("no discover choice is pending")
        options = self.state.pending_discover_options
        if action.choice < 0 or action.choice >= len(options):
            raise IllegalAction("discover choice is out of range")
        chosen_card_id = options[action.choice]
        from_deck = self.state.pending_discover_from_deck
        attack_bonus = self.state.pending_discover_attack_bonus
        health_bonus = self.state.pending_discover_health_bonus
        heal_by_cost = self.state.pending_discover_heal_by_cost
        cost_modifier = self.state.pending_discover_cost_modifier
        summon_choice = self.state.pending_discover_summon
        freeze_choice = self.state.pending_discover_freeze
        special_tags = self.state.pending_discover_special_tags
        self.state.pending_discover_player = None
        self.state.pending_discover_options = ()
        self.state.pending_discover_from_deck = False
        self.state.pending_discover_attack_bonus = 0
        self.state.pending_discover_health_bonus = 0
        self.state.pending_discover_heal_by_cost = False
        self.state.pending_discover_cost_modifier = 0
        self.state.pending_discover_summon = False
        self.state.pending_discover_freeze = False
        self.state.pending_discover_special_tags = ()
        player = self.state.players[actor]
        if from_deck and chosen_card_id in player.deck:
            self._ensure_deck_origin_flags(player)
            deck_index = player.deck.index(chosen_card_id)
            player.deck.pop(deck_index)
            chosen_outside_starting = player.deck_outside_starting.pop(deck_index)
        else:
            chosen_outside_starting = False
        if summon_choice:
            summoned = self._summon(actor, chosen_card_id)
            if summoned is not None and freeze_choice:
                summoned.frozen = True
        elif len(player.hand) < 10:
            player.hand.append(
                HandCard(
                    self._entity_id(),
                    chosen_card_id,
                    attack_bonus=attack_bonus,
                    health_bonus=health_bonus,
                    cost_modifier=cost_modifier,
                    outside_starting_deck=chosen_outside_starting,
                    special_tags=special_tags,
                )
            )
        if heal_by_cost:
            player.hero_health = min(
                30,
                player.hero_health + self.cards[chosen_card_id].cost,
            )
        if self.state.pending_discover_queue:
            next_candidates = self.state.pending_discover_queue.pop(0)
            self._start_discover(actor, next_candidates)

    def _resolve_effects(
        self,
        actor: int,
        card: CardDef,
        selected: Optional[TargetRef],
        played_minion: Optional[TargetRef],
    ) -> None:
        spell_damage_bonus = self._spell_damage(actor) if card.card_type == CardType.SPELL else 0
        self._resolve_effect_sequence(
            actor,
            card.effects,
            selected,
            played_minion,
            spell_damage_bonus=spell_damage_bonus,
        )

    def _resolve_effect_sequence(
        self,
        actor: int,
        effects: Tuple[Effect, ...],
        selected: Optional[TargetRef],
        played_minion: Optional[TargetRef],
        source_snapshot: Optional[Minion] = None,
        spell_damage_bonus: int = 0,
        event_player: Optional[int] = None,
        event_card_id: str = "",
    ) -> None:
        summoned_entities: List[TargetRef] = []
        for effect in effects:
            if self.state.terminal:
                return
            if effect.kind == "grant_keyword_summoned" and not summoned_entities:
                continue
            if effect.corpse_cost and effect.kind not in {
                "spend_corpses_summon",
                "spend_corpses_summon_source_copy",
            }:
                player = self.state.players[actor]
                if player.corpses < effect.corpse_cost:
                    continue
                player.corpses -= effect.corpse_cost
            if effect.kind == "damage":
                target = self._single_effect_target(actor, effect.target, selected, played_minion)
                self._damage(target, effect.amount + spell_damage_bonus)
                self._resolve_damage_triggers()
            elif effect.kind == "lifesteal_damage":
                target = self._single_effect_target(actor, effect.target, selected, played_minion)
                damage_dealt = self._damage(target, effect.amount + spell_damage_bonus)
                self._resolve_damage_triggers()
                if damage_dealt > 0:
                    player = self.state.players[actor]
                    player.hero_health = min(30, player.hero_health + damage_dealt)
            elif effect.kind == "heal":
                target = self._single_effect_target(actor, effect.target, selected, played_minion)
                self._heal(target, effect.amount)
            elif effect.kind == "buff":
                target = self._single_effect_target(actor, effect.target, selected, played_minion)
                self._buff_minion(target, effect.attack, effect.health)
            elif effect.kind == "grant_keyword":
                target = self._single_effect_target(actor, effect.target, selected, played_minion)
                self._grant_minion_keyword(target, effect.keyword)
            elif effect.kind == "freeze":
                target = self._single_effect_target(actor, effect.target, selected, played_minion)
                self._freeze(target)
            elif effect.kind == "temporary_buff":
                target = self._single_effect_target(actor, effect.target, selected, played_minion)
                self._temporary_attack_buff(target, effect.attack)
            elif effect.kind == "swap_stats":
                target = self._single_effect_target(actor, effect.target, selected, played_minion)
                self._swap_minion_attack_and_health(target)
            elif effect.kind == "armor":
                if effect.target != "owner_hero":
                    raise RuntimeError("unsupported armor target: {}".format(effect.target))
                self.state.players[actor].hero_armor += effect.amount
                self._refresh_dynamic_attack_bonuses()
            elif effect.kind == "weapon_buff":
                self._buff_weapon(actor, effect.attack, effect.amount)
            elif effect.kind == "weapon_buff_if_friendly_race":
                if any(effect.race in minion.races for minion in self.state.players[actor].board):
                    self._buff_weapon(actor, effect.attack, effect.amount)
            elif effect.kind == "buff_attack_by_weapon":
                weapon = self.state.players[actor].weapon
                if weapon is not None:
                    target = self._single_effect_target(
                        actor, effect.target, selected, played_minion
                    )
                    self._buff_minion(target, weapon.attack, 0)
            elif effect.kind == "damage_if_weapon":
                if self.state.players[actor].weapon is not None and selected is not None:
                    self._damage(selected, effect.amount)
                    self._resolve_damage_triggers()
            elif effect.kind == "damage_by_hero_attack":
                if selected is not None:
                    self._damage(selected, self.state.players[actor].hero_attack)
                    self._resolve_damage_triggers()
            elif effect.kind == "summon":
                summon_multiplier = self._summon_multiplier(actor)
                for _ in range(effect.amount * summon_multiplier):
                    summoned = self._summon(actor, effect.card_id)
                    if summoned is None:
                        break
                    summoned_entities.append(TargetRef.minion(actor, summoned.entity_id))
            elif effect.kind == "summon_sequence":
                summon_multiplier = self._summon_multiplier(actor)
                for card_id in effect.card_ids:
                    for _ in range(summon_multiplier):
                        summoned = self._summon(actor, card_id)
                        if summoned is None:
                            break
                        summoned_entities.append(TargetRef.minion(actor, summoned.entity_id))
            elif effect.kind == "summon_random":
                summon_candidates = [
                    card_id
                    for card_id in effect.card_ids
                    if card_id in self.cards and self.cards[card_id].card_type == CardType.MINION
                ]
                if summon_candidates:
                    for _ in range(self._summon_multiplier(actor)):
                        summoned = self._summon(actor, self.rng.choice(summon_candidates))
                        if summoned is None:
                            break
                        summoned_entities.append(TargetRef.minion(actor, summoned.entity_id))
            elif effect.kind == "summon_random_hand_cost":
                cost = len(self.state.players[actor].hand)
                for _ in range(self._summon_multiplier(actor)):
                    summoned = self._summon_random_collectible_minion(actor, cost)
                    if summoned is None:
                        break
                    summoned_entities.append(TargetRef.minion(actor, summoned.entity_id))
            elif effect.kind == "summon_random_cost_spend_corpses":
                player = self.state.players[actor]
                spent = min(effect.amount, player.corpses)
                player.corpses -= spent
                for _ in range(self._summon_multiplier(actor)):
                    summoned = self._summon_random_collectible_minion(actor, spent)
                    if summoned is None:
                        break
                    summoned_entities.append(TargetRef.minion(actor, summoned.entity_id))
            elif effect.kind == "summon_random_deck_minion_cost_at_most":
                player = self.state.players[actor]
                for _ in range(self._summon_multiplier(actor)):
                    deck_candidates = [
                        index
                        for index, card_id in enumerate(player.deck)
                        if card_id in self.cards
                        and self.cards[card_id].card_type == CardType.MINION
                        and self.cards[card_id].cost <= effect.amount
                    ]
                    if not deck_candidates or len(player.board) >= 7:
                        break
                    self._ensure_deck_origin_flags(player)
                    deck_index = self.rng.choice(deck_candidates)
                    card_id = player.deck.pop(deck_index)
                    player.deck_outside_starting.pop(deck_index)
                    summoned = self._summon(actor, card_id)
                    if summoned is None:
                        break
                    summoned_entities.append(TargetRef.minion(actor, summoned.entity_id))
            elif effect.kind == "summon_random_opponent_hand_minion":
                opponent = self.state.players[1 - actor]
                for _ in range(self._summon_multiplier(actor)):
                    hand_candidates = [
                        hand_card
                        for hand_card in opponent.hand
                        if hand_card.card_id in self.cards
                        and self.cards[hand_card.card_id].card_type == CardType.MINION
                    ]
                    if not hand_candidates or len(opponent.board) >= 7:
                        break
                    chosen_hand_card = self.rng.choice(hand_candidates)
                    opponent.hand.remove(chosen_hand_card)
                    summoned = self._summon(
                        1 - actor,
                        chosen_hand_card.card_id,
                        attack_bonus=chosen_hand_card.attack_bonus,
                        health_bonus=chosen_hand_card.health_bonus,
                    )
                    if summoned is not None:
                        summoned_entities.append(TargetRef.minion(1 - actor, summoned.entity_id))
            elif effect.kind == "summon_random_demon_from_hand_and_deck":
                player = self.state.players[actor]
                summon_multiplier = self._summon_multiplier(actor)
                for _ in range(summon_multiplier):
                    hand_candidates = [
                        hand_card
                        for hand_card in player.hand
                        if hand_card.card_id in self.cards
                        and "DEMON" in self.cards[hand_card.card_id].races
                    ]
                    if not hand_candidates or len(player.board) >= 7:
                        break
                    chosen_hand_card = self.rng.choice(hand_candidates)
                    player.hand.remove(chosen_hand_card)
                    summoned = self._summon(
                        actor,
                        chosen_hand_card.card_id,
                        attack_bonus=chosen_hand_card.attack_bonus,
                        health_bonus=chosen_hand_card.health_bonus,
                    )
                    if summoned is not None:
                        summoned_entities.append(TargetRef.minion(actor, summoned.entity_id))
                for _ in range(summon_multiplier):
                    deck_candidates = [
                        index
                        for index, card_id in enumerate(player.deck)
                        if card_id in self.cards and "DEMON" in self.cards[card_id].races
                    ]
                    if not deck_candidates or len(player.board) >= 7:
                        break
                    self._ensure_deck_origin_flags(player)
                    deck_index = self.rng.choice(deck_candidates)
                    card_id = player.deck.pop(deck_index)
                    player.deck_outside_starting.pop(deck_index)
                    summoned = self._summon(actor, card_id)
                    if summoned is not None:
                        summoned_entities.append(TargetRef.minion(actor, summoned.entity_id))
            elif effect.kind == "grant_keyword_summoned":
                for target in summoned_entities:
                    if any(
                        minion.entity_id == target.entity_id
                        for minion in self.state.players[actor].board
                    ):
                        self._grant_minion_keyword(target, effect.keyword)
            elif effect.kind == "gain_corpses":
                self._gain_corpses(actor, effect.amount)
            elif effect.kind == "add_random_race_to_hand":
                race_candidates = [
                    card.card_id
                    for card in self.cards.values()
                    if card.collectible
                    and card.card_type == CardType.MINION
                    and effect.race in card.races
                ]
                if race_candidates:
                    for _ in range(max(1, effect.amount)):
                        self._add_to_hand(actor, self.rng.choice(race_candidates))
            elif effect.kind == "add_random_from_pool":
                pool_card_ids = [card_id for card_id in effect.card_ids if card_id in self.cards]
                if pool_card_ids:
                    for _ in range(max(1, effect.amount)):
                        self._add_to_hand(actor, self.rng.choice(pool_card_ids))
            elif effect.kind == "copy_event_card_to_other_player":
                if event_player is not None and event_card_id in self.cards:
                    self._add_to_hand(1 - event_player, event_card_id)
            elif effect.kind == "copy_event_card_cost_one":
                if event_card_id in self.cards and len(self.state.players[actor].hand) < 10:
                    event_definition = self.cards[event_card_id]
                    self.state.players[actor].hand.append(
                        HandCard(
                            self._entity_id(),
                            event_card_id,
                            cost_modifier=1 - event_definition.cost,
                        )
                    )
            elif effect.kind == "shuffle_into_deck":
                player = self.state.players[actor]
                self._ensure_deck_origin_flags(player)
                player.deck.extend(effect.card_id for _ in range(effect.amount))
                player.deck_outside_starting.extend(True for _ in range(effect.amount))
                shuffled = list(zip(player.deck, player.deck_outside_starting))
                self.rng.shuffle(shuffled)
                player.deck = [card_id for card_id, _ in shuffled]
                player.deck_outside_starting = [flag for _, flag in shuffled]
            elif effect.kind == "discover_from_pool":
                self._start_discover(actor, effect.card_ids)
            elif effect.kind == "discover_from_deck":
                self._start_discover(
                    actor,
                    tuple(self.state.players[actor].deck),
                    from_deck=True,
                )
            elif effect.kind == "discover_from_pool_if_hand_race":
                if any(
                    hand_card.card_id in self.cards
                    and effect.race in self.cards[hand_card.card_id].races
                    for hand_card in self.state.players[actor].hand
                ):
                    self._start_discover(actor, effect.card_ids)
            elif effect.kind == "discover_from_pool_if_other_friendly_race":
                played_entity_id = played_minion.entity_id if played_minion else None
                if any(
                    minion.entity_id != played_entity_id
                    and effect.race in minion.races
                    and minion.health > 0
                    for minion in self.state.players[actor].board
                ):
                    self._start_discover(actor, effect.card_ids)
            elif effect.kind == "discover_from_pool_heal_by_cost":
                self._start_discover(actor, effect.card_ids, heal_by_cost=True)
            elif effect.kind == "discover_from_pool_buff":
                self._start_discover(
                    actor,
                    effect.card_ids,
                    attack_bonus=effect.attack,
                    health_bonus=effect.health,
                )
            elif effect.kind == "discover_from_pool_cost_discount":
                self._start_discover(
                    actor,
                    effect.card_ids,
                    cost_modifier=-effect.amount,
                )
            elif effect.kind == "discover_from_pool_summon_frozen":
                self._start_discover(
                    actor,
                    effect.card_ids,
                    summon_choice=True,
                    freeze_choice=True,
                )
            elif effect.kind == "discover_beast_with_dark_gift_kindred":
                kindred_active = (
                    "BEAST" in self.state.players[actor].minion_types_played_previous_turn
                )
                self._start_discover(
                    actor,
                    effect.card_ids,
                    cost_modifier=-1 if kindred_active else 0,
                    special_tags=("dark_gift", "rewind_eligible"),
                )
            elif effect.kind == "discover_from_pool_if_selected_dead":
                if selected is None or selected.kind != "minion":
                    raise RuntimeError("conditional discover requires a minion target")
                selected_minion = self._find_minion(selected.player, selected.entity_id)
                if selected_minion.health <= 0:
                    self._start_discover(actor, effect.card_ids)
            elif effect.kind == "discover_from_pool_if_undead_died":
                if self.state.players[actor].friendly_undead_died_since_last_turn:
                    self._start_discover(actor, effect.card_ids)
            elif effect.kind == "summon_up_to_corpses":
                player = self.state.players[actor]
                summon_count = min(effect.amount, player.corpses)
                for _ in range(summon_count):
                    successful_summons = 0
                    for _ in range(self._summon_multiplier(actor)):
                        summoned = self._summon(actor, effect.card_id)
                        if summoned is None:
                            break
                        successful_summons += 1
                        summoned_entities.append(TargetRef.minion(actor, summoned.entity_id))
                    if not successful_summons:
                        break
                    player.corpses -= 1
            elif effect.kind == "random_damage_spend_up_to_corpses":
                player = self.state.players[actor]
                spent = min(effect.amount, player.corpses)
                player.corpses -= spent
                for _ in range(spent):
                    targets = self._enemy_characters(actor)
                    if not targets:
                        break
                    self._damage(self.rng.choice(targets), effect.attack)
                    self._resolve_damage_triggers()
                    self._cleanup_deaths()
                    self._check_terminal()
                    if self.state.terminal:
                        break
            elif effect.kind == "random_damage_source_attack":
                if source_snapshot is None:
                    raise RuntimeError("source-attack damage requires a death snapshot")
                for _ in range(max(0, source_snapshot.attack)):
                    targets = self._enemy_characters(actor)
                    if not targets:
                        break
                    self._damage(self.rng.choice(targets), 1)
                    self._resolve_damage_triggers()
                    self._cleanup_deaths()
                    self._check_terminal()
                    if self.state.terminal:
                        break
            elif effect.kind == "random_buff_other_friendly_source_attack":
                if source_snapshot is None:
                    raise RuntimeError("source-attack buff requires a death snapshot")
                candidates = [
                    minion for minion in self.state.players[actor].board if minion.health > 0
                ]
                if candidates:
                    chosen = self.rng.choice(candidates)
                    self._buff_minion(
                        TargetRef.minion(actor, chosen.entity_id),
                        source_snapshot.attack,
                        0,
                    )
            elif effect.kind == "resurrect_highest_cost_friendly":
                graveyard_candidates = [
                    card_id
                    for card_id in self.state.players[actor].graveyard
                    if card_id in self.cards and self.cards[card_id].card_type == CardType.MINION
                ]
                if graveyard_candidates:
                    highest_cost = max(self.cards[card_id].cost for card_id in graveyard_candidates)
                    highest_candidates = [
                        card_id
                        for card_id in graveyard_candidates
                        if self.cards[card_id].cost == highest_cost
                    ]
                    self._summon(actor, self.rng.choice(highest_candidates))
            elif effect.kind == "summon_random_rarity":
                rarity_candidates = [
                    card.card_id
                    for card in self.cards.values()
                    if card.collectible
                    and card.card_type == CardType.MINION
                    and card.rarity == effect.keyword
                ]
                if rarity_candidates:
                    for _ in range(self._summon_multiplier(actor)):
                        summoned = self._summon(actor, self.rng.choice(rarity_candidates))
                        if summoned is None:
                            break
                        summoned_entities.append(TargetRef.minion(actor, summoned.entity_id))
            elif effect.kind == "summon_copy_if_selected_dead":
                if selected is None or selected.kind != "minion":
                    raise RuntimeError("copy summon requires a selected minion")
                minion = self._find_minion(selected.player, selected.entity_id)
                if minion.health <= 0:
                    self._summon(actor, minion.card_id)
            elif effect.kind == "draw":
                for _ in range(effect.amount):
                    self._draw(actor)
            elif effect.kind == "draw_with_cost_discount":
                before_ids = {card.entity_id for card in self.state.players[actor].hand}
                self._draw(actor)
                for hand_card in self.state.players[actor].hand:
                    if hand_card.entity_id not in before_ids:
                        hand_card.cost_modifier -= effect.amount
            elif effect.kind == "draw_if_hand_empty":
                if not self.state.players[actor].hand:
                    for _ in range(effect.amount):
                        self._draw(actor)
            elif effect.kind in {"draw_if_selected_dead", "draw_if_selected_survives"}:
                if selected is None or selected.kind != "minion":
                    raise RuntimeError("conditional draw requires a selected minion")
                minion = self._find_minion(selected.player, selected.entity_id)
                should_draw = (
                    minion.health <= 0
                    if effect.kind == "draw_if_selected_dead"
                    else minion.health > 0
                )
                if should_draw:
                    for _ in range(effect.amount):
                        self._draw(actor)
            elif effect.kind == "draw_each_player":
                for player_index in range(len(self.state.players)):
                    for _ in range(effect.amount):
                        self._draw(player_index)
            elif effect.kind == "add_to_hand":
                for _ in range(effect.amount):
                    self._add_to_hand(actor, effect.card_id)
            elif effect.kind == "add_to_opponent_hand":
                for _ in range(effect.amount):
                    self._add_to_hand(1 - actor, effect.card_id)
            elif effect.kind == "fill_hand":
                while len(self.state.players[actor].hand) < 10:
                    self._add_to_hand(actor, effect.card_id)
            elif effect.kind == "discard_random":
                player = self.state.players[actor]
                for _ in range(effect.amount):
                    if not player.hand:
                        break
                    player.hand.remove(self.rng.choice(player.hand))
            elif effect.kind == "remove_enemy_deck_top":
                enemy_player = self.state.players[1 - actor]
                enemy_deck = enemy_player.deck
                self._ensure_deck_origin_flags(enemy_player)
                for _ in range(effect.amount):
                    if not enemy_deck:
                        break
                    enemy_deck.pop()
                    enemy_player.deck_outside_starting.pop()
            elif effect.kind == "draw_highest_cost_minion":
                self._draw_filtered(
                    actor,
                    lambda definition: definition.card_type == CardType.MINION,
                    highest_cost=True,
                )
            elif effect.kind == "draw_spell_school":
                self._draw_filtered(
                    actor,
                    partial(self._matches_spell_school, spell_school=effect.keyword),
                )
            elif effect.kind == "draw_race":
                self._draw_filtered(
                    actor,
                    partial(self._matches_race, race=effect.race),
                )
            elif effect.kind == "draw_spends_corpses":
                self._draw_filtered(actor, lambda definition: definition.spends_corpses)
            elif effect.kind == "copy_random_enemy_deck":
                enemy_deck = self.state.players[1 - actor].deck
                if enemy_deck:
                    self._add_to_hand(actor, self.rng.choice(enemy_deck))
            elif effect.kind == "destroy_outside_starting_deck":
                for affected_player in self.state.players:
                    self._ensure_deck_origin_flags(affected_player)
                    kept = [
                        (card_id, outside)
                        for card_id, outside in zip(
                            affected_player.deck,
                            affected_player.deck_outside_starting,
                        )
                        if not outside
                    ]
                    affected_player.deck = [card_id for card_id, _ in kept]
                    affected_player.deck_outside_starting = [outside for _, outside in kept]
            elif effect.kind == "return_previous_turn_spells":
                for card_id in self.state.players[actor].spells_played_previous_turn:
                    self._add_to_hand(actor, card_id)
            elif effect.kind == "add_random_spell_opponent_deck_top":
                spell_pool_ids = [
                    card_id
                    for card_id in effect.card_ids
                    if card_id in self.cards and self.cards[card_id].card_type == CardType.SPELL
                ]
                if spell_pool_ids:
                    opponent = self.state.players[1 - actor]
                    self._ensure_deck_origin_flags(opponent)
                    opponent.deck.append(self.rng.choice(spell_pool_ids))
                    opponent.deck_outside_starting.append(True)
            elif effect.kind == "equip_weapon":
                self._equip_weapon(actor, effect.card_id)
            elif effect.kind == "destroy_enemy_weapon":
                self._destroy_weapon(1 - actor)
            elif effect.kind == "grant_next_demon_discount":
                self.state.players[actor].next_demon_discount += effect.amount
            elif effect.kind == "grant_next_demon_cost_zero_this_turn":
                self.state.players[actor].next_demon_cost_zero_this_turn = True
            elif effect.kind == "grant_next_outcast_discount":
                self.state.players[actor].next_outcast_discount += effect.amount
            elif effect.kind == "tax_opponent_spells":
                opponent = self.state.players[1 - actor]
                opponent.spell_tax_remaining_turns = max(
                    opponent.spell_tax_remaining_turns,
                    effect.amount,
                )
            elif effect.kind == "tax_opponent_next_hero_power":
                self.state.players[1 - actor].next_hero_power_cost_increase += effect.amount
            elif effect.kind == "grant_next_combo_discount_this_turn":
                self.state.players[actor].next_combo_discount_this_turn += effect.amount
            elif effect.kind == "grant_next_spell_discount_this_turn":
                self.state.players[actor].next_spell_discount_this_turn += effect.amount
            elif effect.kind == "temporary_mana":
                player = self.state.players[actor]
                room = max(0, 10 - player.mana - player.temporary_mana)
                player.temporary_mana += min(effect.amount, room)
            elif effect.kind == "temporary_hero_attack":
                player = self.state.players[actor]
                player.hero_attack += effect.attack
                player.hero_temporary_attack += effect.attack
            elif effect.kind == "buff_health_by_hand_count":
                if played_minion is None:
                    raise RuntimeError("hand-count buff requires its played minion")
                amount = len(self.state.players[actor].hand) * effect.health
                self._buff_minion(played_minion, 0, amount)
            elif effect.kind == "lose_health_by_enemy_hand_count":
                if played_minion is None:
                    raise RuntimeError("enemy hand-count loss requires its played minion")
                minion = self._find_minion(actor, played_minion.entity_id)
                minion.health -= len(self.state.players[1 - actor].hand) * effect.amount
                self._refresh_dynamic_attack_bonuses()
            elif effect.kind == "buff_other_friendly_race":
                if played_minion is None:
                    raise RuntimeError("race buff requires its played minion")
                for minion in self.state.players[actor].board:
                    if minion.entity_id == played_minion.entity_id or minion.health <= 0:
                        continue
                    if effect.race in minion.races:
                        self._buff_minion(
                            TargetRef.minion(actor, minion.entity_id),
                            effect.attack,
                            effect.health,
                        )
            elif effect.kind == "buff_if_hand_spell_school":
                if any(
                    hand_card.card_id in self.cards
                    and self.cards[hand_card.card_id].card_type == CardType.SPELL
                    and self.cards[hand_card.card_id].spell_school == effect.keyword
                    for hand_card in self.state.players[actor].hand
                ):
                    target = self._single_effect_target(
                        actor, effect.target, selected, played_minion
                    )
                    self._buff_minion(target, effect.attack, effect.health)
            elif effect.kind == "buff_hand_minions":
                for hand_card in self.state.players[actor].hand:
                    definition = self.cards.get(hand_card.card_id)
                    if definition is None or definition.card_type != CardType.MINION:
                        continue
                    if effect.keyword == "TAUNT" and not definition.taunt:
                        continue
                    hand_card.attack_bonus += effect.attack
                    hand_card.health_bonus += effect.health
            elif effect.kind == "random_damage":
                for _ in range(effect.repeats):
                    targets = self._enemy_characters(actor)
                    if not targets:
                        break
                    self._damage(self.rng.choice(targets), effect.amount)
                    self._resolve_damage_triggers()
                    self._cleanup_deaths()
                    self._check_terminal()
                    if self.state.terminal:
                        break
            elif effect.kind == "random_damage_other_characters":
                for _ in range(effect.repeats):
                    targets = self._group_targets(actor, "all_characters", played_minion)
                    if played_minion is not None:
                        targets = [target for target in targets if target != played_minion]
                    if not targets:
                        break
                    self._damage(self.rng.choice(targets), effect.amount)
                    self._resolve_damage_triggers()
                    self._cleanup_deaths()
                    self._check_terminal()
                    if self.state.terminal:
                        break
            elif effect.kind == "random_lifesteal_damage_minions":
                for _ in range(effect.repeats):
                    candidates = [
                        minion
                        for minion in self.state.players[1 - actor].board
                        if minion.health > 0
                    ]
                    if not candidates:
                        break
                    chosen = self.rng.choice(candidates)
                    dealt = self._damage(
                        TargetRef.minion(1 - actor, chosen.entity_id), effect.amount
                    )
                    self._resolve_damage_triggers()
                    self._cleanup_deaths()
                    if dealt > 0:
                        player = self.state.players[actor]
                        player.hero_health = min(30, player.hero_health + dealt)
            elif effect.kind == "random_heal_friendly":
                for _ in range(effect.repeats):
                    heal_targets: List[TargetRef] = []
                    player = self.state.players[actor]
                    if player.hero_health < 30:
                        heal_targets.append(TargetRef.hero(actor))
                    heal_targets.extend(
                        TargetRef.minion(actor, minion.entity_id)
                        for minion in player.board
                        if 0 < minion.health < minion.max_health
                    )
                    if not heal_targets:
                        break
                    self._heal(self.rng.choice(heal_targets), effect.amount)
            elif effect.kind == "damage_two_random_enemy_minions_draw_deaths":
                candidates = [
                    minion for minion in self.state.players[1 - actor].board if minion.health > 0
                ]
                chosen_minions = self.rng.sample(candidates, min(2, len(candidates)))
                for minion in chosen_minions:
                    self._damage(TargetRef.minion(1 - actor, minion.entity_id), effect.amount)
                self._resolve_damage_triggers()
                deaths = sum(minion.health <= 0 for minion in chosen_minions)
                self._cleanup_deaths()
                for _ in range(deaths):
                    self._draw(actor)
            elif effect.kind == "random_damage_distinct":
                targets = self._enemy_characters(actor)
                for _ in range(min(effect.repeats, len(targets))):
                    target = self.rng.choice(targets)
                    targets.remove(target)
                    self._damage(target, effect.amount)
                    self._resolve_damage_triggers()
                    self._cleanup_deaths()
                    self._check_terminal()
                    if self.state.terminal:
                        break
            elif effect.kind == "random_damage_minion":
                candidates = [
                    minion for minion in self.state.players[1 - actor].board if minion.health > 0
                ]
                if candidates:
                    chosen = self.rng.choice(candidates)
                    self._damage(TargetRef.minion(1 - actor, chosen.entity_id), effect.amount)
                    self._resolve_damage_triggers()
                    self._cleanup_deaths()
                    self._check_terminal()
            elif effect.kind == "random_buff_other_friendly":
                source_entity = (
                    played_minion.entity_id
                    if played_minion is not None
                    and played_minion.kind == "minion"
                    and played_minion.player == actor
                    else None
                )
                candidates = [
                    minion
                    for minion in self.state.players[actor].board
                    if minion.health > 0 and minion.entity_id != source_entity
                ]
                if candidates:
                    chosen = self.rng.choice(candidates)
                    self._buff_minion(
                        TargetRef.minion(actor, chosen.entity_id),
                        effect.attack,
                        effect.health,
                    )
            elif effect.kind == "random_buff_distinct_races":
                remaining = [
                    minion
                    for minion in self.state.players[actor].board
                    if minion.health > 0
                    and (played_minion is None or minion.entity_id != played_minion.entity_id)
                ]
                used_races = set()
                for _ in range(effect.amount):
                    eligible = [
                        (minion, race)
                        for minion in remaining
                        for race in (minion.races or ("NO_RACE",))
                        if race not in used_races
                    ]
                    if not eligible:
                        break
                    chosen, chosen_race = self.rng.choice(eligible)
                    self._buff_minion(
                        TargetRef.minion(actor, chosen.entity_id),
                        effect.attack,
                        effect.health,
                    )
                    used_races.add(chosen_race)
                    remaining = [
                        minion for minion in remaining if minion.entity_id != chosen.entity_id
                    ]
            elif effect.kind == "random_buff_hand_minion":
                hand_minion_candidates = [
                    hand_card
                    for hand_card in self.state.players[actor].hand
                    if hand_card.card_id in self.cards
                    and self.cards[hand_card.card_id].card_type == CardType.MINION
                ]
                if hand_minion_candidates:
                    chosen_hand_minion = self.rng.choice(hand_minion_candidates)
                    chosen_hand_minion.attack_bonus += effect.attack
                    chosen_hand_minion.health_bonus += effect.health
            elif effect.kind == "buff_source_if_healed_this_turn":
                if self.state.players[actor].healed_this_turn and played_minion is not None:
                    self._buff_minion(played_minion, effect.attack, effect.health)
            elif effect.kind == "spend_corpses_summon":
                player = self.state.players[actor]
                if player.corpses >= effect.corpse_cost and len(player.board) < 7:
                    player.corpses -= effect.corpse_cost
                    self._summon(actor, effect.card_id)
            elif effect.kind == "spend_corpses_summon_source_copy":
                player = self.state.players[actor]
                if (
                    played_minion is not None
                    and player.corpses >= effect.corpse_cost
                    and len(player.board) < 7
                ):
                    copy_source = self._find_minion(actor, played_minion.entity_id)
                    player.corpses -= effect.corpse_cost
                    self._summon_copy(actor, copy_source)
            elif effect.kind == "source_attacks_lowest_health_enemy":
                if played_minion is not None:
                    attack_source = next(
                        (
                            minion
                            for minion in self.state.players[actor].board
                            if minion.entity_id == played_minion.entity_id and minion.health > 0
                        ),
                        None,
                    )
                    if attack_source is not None:
                        enemy = 1 - actor
                        target_pool = [
                            (self.state.players[enemy].hero_health, TargetRef.hero(enemy))
                        ] + [
                            (minion.health, TargetRef.minion(enemy, minion.entity_id))
                            for minion in self.state.players[enemy].board
                            if minion.health > 0
                        ]
                        lowest = min(health for health, _ in target_pool)
                        target = self.rng.choice(
                            [target for health, target in target_pool if health == lowest]
                        )
                        self._attack(
                            actor,
                            Action(ActionType.ATTACK, attack_source.entity_id, target),
                        )
            elif effect.kind == "all_enemy_minions_attack_source":
                if played_minion is not None:
                    enemy = 1 - actor
                    source_entity_id = played_minion.entity_id
                    if source_entity_id is None:
                        continue
                    attacker_ids = [
                        minion.entity_id
                        for minion in self.state.players[enemy].board
                        if minion.health > 0
                    ]
                    for attacker_id in attacker_ids:
                        source_alive = any(
                            minion.entity_id == source_entity_id and minion.health > 0
                            for minion in self.state.players[actor].board
                        )
                        attacker_alive = any(
                            minion.entity_id == attacker_id and minion.health > 0
                            for minion in self.state.players[enemy].board
                        )
                        if not source_alive or not attacker_alive:
                            break
                        self._attack(
                            enemy,
                            Action(
                                ActionType.ATTACK,
                                attacker_id,
                                TargetRef.minion(actor, source_entity_id),
                            ),
                        )
            elif effect.kind == "gain_permanent_end_turn_enemy_damage":
                self.state.players[actor].end_turn_enemy_damage += effect.amount
            elif effect.kind == "attach_same_cost_deathrattle_other_friendly":
                source_entity_id = played_minion.entity_id if played_minion else None
                for minion in self.state.players[actor].board:
                    if minion.entity_id == source_entity_id or minion.health <= 0:
                        continue
                    minion.attached_deathrattle_effects += (
                        Effect("summon_random_same_cost_as_source_snapshot"),
                    )
            elif effect.kind == "summon_random_same_cost_as_source_snapshot":
                if source_snapshot is not None:
                    snapshot_definition = self.cards.get(source_snapshot.card_id)
                    if snapshot_definition is not None:
                        self._summon_random_collectible_minion(actor, snapshot_definition.cost)
            elif effect.kind == "summon_from_deck_race":
                player = self.state.players[actor]
                for _ in range(effect.amount):
                    deck_race_candidates = [
                        index
                        for index, card_id in enumerate(player.deck)
                        if card_id in self.cards and effect.race in self.cards[card_id].races
                    ]
                    if not deck_race_candidates or len(player.board) >= 7:
                        break
                    self._ensure_deck_origin_flags(player)
                    deck_index = self.rng.choice(deck_race_candidates)
                    card_id = player.deck.pop(deck_index)
                    player.deck_outside_starting.pop(deck_index)
                    self._summon(actor, card_id)
            elif effect.kind == "random_grant_keywords_friendly":
                candidates = [
                    minion for minion in self.state.players[actor].board if minion.health > 0
                ]
                if candidates:
                    chosen = self.rng.choice(candidates)
                    target = TargetRef.minion(actor, chosen.entity_id)
                    for keyword in effect.keywords:
                        self._grant_minion_keyword(target, keyword)
            elif effect.kind == "return_random_friendly_minion_to_hand_discount":
                player = self.state.players[actor]
                candidates = [minion for minion in player.board if minion.health > 0]
                if candidates:
                    chosen = self.rng.choice(candidates)
                    player.board.remove(chosen)
                    if len(player.hand) < 10:
                        player.hand.append(
                            HandCard(
                                entity_id=self._entity_id(),
                                card_id=chosen.card_id,
                                cost_modifier=-effect.amount,
                            )
                        )
                    self._refresh_dynamic_attack_bonuses()
            elif effect.kind == "source_attacks_selected":
                if played_minion is None or selected is None:
                    continue
                selected_attack_source = next(
                    (
                        minion
                        for minion in self.state.players[actor].board
                        if minion.entity_id == played_minion.entity_id and minion.health > 0
                    ),
                    None,
                )
                target_exists = selected.kind == "hero" or any(
                    minion.entity_id == selected.entity_id and minion.health > 0
                    for minion in self.state.players[selected.player].board
                )
                if selected_attack_source is not None and target_exists:
                    self._attack(
                        actor,
                        Action(
                            ActionType.ATTACK,
                            selected_attack_source.entity_id,
                            selected,
                        ),
                    )
            elif effect.kind == "draw_if_unused_mana":
                player = self.state.players[actor]
                if player.mana + player.temporary_mana > 0:
                    for _ in range(effect.amount):
                        self._draw(actor)
            elif effect.kind == "damage_all":
                targets = self._group_targets(actor, effect.target, played_minion)
                for target in targets:
                    self._damage(target, effect.amount)
                self._resolve_damage_triggers()
                self._cleanup_deaths()
                self._check_terminal()
            elif effect.kind == "heal_all":
                for target in self._group_targets(actor, effect.target, played_minion):
                    self._heal(target, effect.amount)
            elif effect.kind == "buff_all":
                for target in self._group_targets(actor, effect.target, played_minion):
                    self._buff_minion(target, effect.attack, effect.health)
            elif effect.kind == "buff_and_attach_deathrattle":
                target = self._single_effect_target(actor, effect.target, selected, played_minion)
                if target is None or target.kind != "minion":
                    raise RuntimeError("attached deathrattle requires a minion target")
                self._buff_minion(target, effect.attack, effect.health)
                self._grant_minion_keyword(target, "taunt")
                minion = self._find_minion(target.player, target.entity_id)
                minion.attached_deathrattle_effects += (
                    Effect("summon", 1, target="owner", card_id=effect.card_id),
                )
            elif effect.kind == "grant_keyword_all":
                for target in self._group_targets(actor, effect.target, played_minion):
                    self._grant_minion_keyword(target, effect.keyword)
            elif effect.kind == "freeze_all":
                for target in self._group_targets(actor, effect.target, played_minion):
                    self._freeze(target)
            elif effect.kind == "set_health_all":
                for target in self._group_targets(actor, effect.target, played_minion):
                    minion = self._find_minion(target.player, target.entity_id)
                    minion.health = effect.amount
                    minion.max_health = effect.amount
            elif effect.kind == "destroy":
                target = self._single_effect_target(actor, effect.target, selected, played_minion)
                if target is None or target.kind != "minion":
                    raise RuntimeError("destroy requires a selected minion")
                self._find_minion(target.player, target.entity_id).health = 0
            elif effect.kind == "destroy_highest_attack_enemy":
                candidates = [
                    minion for minion in self.state.players[1 - actor].board if minion.health > 0
                ]
                if candidates:
                    highest = max(minion.attack for minion in candidates)
                    chosen = self.rng.choice(
                        [minion for minion in candidates if minion.attack == highest]
                    )
                    chosen.health = 0
            elif effect.kind == "destroy_random_enemy_minion":
                candidates = [
                    minion for minion in self.state.players[1 - actor].board if minion.health > 0
                ]
                if candidates:
                    self.rng.choice(candidates).health = 0
            elif effect.kind == "destroy_and_gain_health":
                if selected is None or selected.kind != "minion" or played_minion is None:
                    raise RuntimeError("health stealing destroy requires source and target")
                target_minion = self._find_minion(selected.player, selected.entity_id)
                health = max(0, target_minion.health)
                target_minion.health = 0
                self._buff_minion(played_minion, 0, health)
            elif effect.kind == "destroy_and_damage_owner_by_health":
                if selected is None or selected.kind != "minion":
                    raise RuntimeError("rift destroy requires a selected minion")
                target_minion = self._find_minion(selected.player, selected.entity_id)
                health = max(0, target_minion.health)
                target_minion.health = 0
                self._damage(TargetRef.hero(actor), health)
            elif effect.kind == "return_random_enemy_minion_to_hand":
                enemy = 1 - actor
                candidates = [
                    minion for minion in self.state.players[enemy].board if minion.health > 0
                ]
                if candidates:
                    chosen = self.rng.choice(candidates)
                    self.state.players[enemy].board.remove(chosen)
                    self._add_to_hand(enemy, chosen.card_id)
            elif effect.kind == "damage_all_if_hand_race":
                if any(
                    effect.race in self.cards[hand_card.card_id].races
                    for hand_card in self.state.players[actor].hand
                    if hand_card.card_id in self.cards
                ):
                    targets = self._group_targets(actor, effect.target, played_minion)
                    for target in targets:
                        self._damage(target, effect.amount)
                    self._resolve_damage_triggers()
                    self._cleanup_deaths()
                    self._check_terminal()
            elif effect.kind == "transform":
                target = self._single_effect_target(actor, effect.target, selected, played_minion)
                self._transform_minion(target, effect.card_id)
            elif effect.kind == "destroy_all_attack_at_least":
                for player in self.state.players:
                    for minion in player.board:
                        if minion.attack >= effect.amount:
                            minion.health = 0
            elif effect.kind == "destroy_all":
                for target in self._group_targets(actor, effect.target, played_minion):
                    if target.kind == "minion":
                        self._find_minion(target.player, target.entity_id).health = 0
            elif effect.kind == "destroy_all_minions_and_locations":
                for player in self.state.players:
                    for minion in player.board:
                        minion.health = 0
                    player.locations = []
            elif effect.kind == "summon_random_cost":
                for _ in range(effect.amount):
                    if self._summon_random_collectible_minion(actor, effect.attack) is None:
                        break
            elif effect.kind == "destroy_location":
                if selected is None or selected.kind != "location":
                    raise RuntimeError("destroy location requires a selected location")
                location = self._find_location(selected.player, selected.entity_id)
                self.state.players[selected.player].locations.remove(location)
            elif effect.kind == "silence":
                self._silence_minion(selected)
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

    def _attack_targets(self, actor: int) -> List[TargetRef]:
        enemy = 1 - actor
        ignores_taunt = any(
            definition is not None and definition.ignores_taunt_for_friendly_attacks
            for minion in self.state.players[actor].board
            if minion.health > 0
            for definition in (self.cards.get(minion.card_id),)
        )
        taunts = [
            minion
            for minion in self.state.players[enemy].board
            if minion.taunt and not minion.stealth and minion.health > 0
        ]
        if taunts and not ignores_taunt:
            return [TargetRef.minion(enemy, minion.entity_id) for minion in taunts]
        return [TargetRef.hero(enemy)] + [
            TargetRef.minion(enemy, minion.entity_id)
            for minion in self.state.players[enemy].board
            if minion.health > 0 and not minion.stealth
        ]

    def _randomize_action_target(self, actor: int, action: Action) -> Action:
        if action.target is None or not any(
            definition is not None and definition.randomizes_character_targets
            for player in self.state.players
            for minion in player.board
            if minion.health > 0
            for definition in (self.cards.get(minion.card_id),)
        ):
            return action
        candidates: List[TargetRef]
        if action.action_type == ActionType.PLAY:
            hand_card = self._find_hand_card(actor, action.source_id)
            card = self.cards[hand_card.card_id]
            candidates = self._valid_targets(
                actor,
                self._effective_target_mode(actor, card),
                exclude_elusive=card.card_type == CardType.SPELL,
                exclude_enemy_stealth=True,
            )
        elif action.action_type == ActionType.HERO_POWER:
            candidates = self._valid_targets(
                actor,
                TargetMode.ANY_CHARACTER,
                exclude_elusive=True,
                exclude_enemy_stealth=True,
            )
        elif action.action_type == ActionType.ATTACK:
            candidates = [TargetRef.hero(0), TargetRef.hero(1)] + [
                TargetRef.minion(player_index, minion.entity_id)
                for player_index, player in enumerate(self.state.players)
                for minion in player.board
                if minion.health > 0 and minion.entity_id != action.source_id
            ]
        elif action.action_type == ActionType.HERO_ATTACK:
            candidates = [TargetRef.hero(1 - actor)] + [
                TargetRef.minion(player_index, minion.entity_id)
                for player_index, player in enumerate(self.state.players)
                for minion in player.board
                if minion.health > 0
            ]
        else:
            return action
        if not candidates:
            return action
        return Action(
            action.action_type,
            action.source_id,
            self.rng.choice(candidates),
            action.choice,
        )

    def _attack(self, actor: int, action: Action) -> None:
        attacker = self._find_minion(actor, action.source_id)
        target = action.target
        if target is None:
            raise IllegalAction("attack requires target")
        self._resolve_board_triggers("attacks", owner=actor, only_entity=attacker.entity_id)
        attacker.attacks_this_turn += 1
        attacker.stealth = False
        killed_defender = False
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
            killed_defender = defender.health <= 0
            if defender.lifesteal and defender_damage_dealt > 0:
                defender_owner = self.state.players[target.player]
                defender_owner.hero_health = min(
                    30, defender_owner.hero_health + defender_damage_dealt
                )
            defender_card = self.cards.get(defender.card_id)
            if (
                defender_card is not None
                and defender_card.freezes_damaged_characters
                and defender_damage_dealt > 0
            ):
                self._freeze(TargetRef.minion(actor, attacker.entity_id))
        attacker_card = self.cards.get(attacker.card_id)
        if (
            attacker_card is not None
            and attacker_card.freezes_damaged_characters
            and damage_dealt > 0
        ):
            self._freeze(target)
        self._resolve_damage_triggers()
        if target.kind == "minion":
            self._resolve_board_triggers(
                "attacked",
                owner=target.player,
                only_entity=target.entity_id,
            )
        if attacker.lifesteal and damage_dealt > 0:
            owner = self.state.players[actor]
            owner.hero_health = min(30, owner.hero_health + damage_dealt)
        if killed_defender:
            self._resolve_board_triggers(
                "attack_kill",
                owner=actor,
                only_entity=attacker.entity_id,
            )
        self._cleanup_deaths()
        self._check_terminal()

    def _hero_attack(self, actor: int, action: Action) -> None:
        player = self.state.players[actor]
        weapon = player.weapon
        if weapon is not None and weapon.entity_id != action.source_id:
            raise IllegalAction("weapon entity not found")
        if weapon is None and action.source_id is not None:
            raise IllegalAction("unarmed hero attack has no source entity")
        target = action.target
        if target is None:
            raise IllegalAction("hero attack requires target")
        player.hero_attacks_this_turn += 1
        defender_card_id: Optional[str] = None
        if target.kind == "minion":
            defender_card_id = self._find_minion(target.player, target.entity_id).card_id
        damage_dealt = self._damage(target, player.hero_attack)
        if target.kind == "hero":
            retaliation = 0
        else:
            retaliation = self._find_minion(target.player, target.entity_id).attack
        self._damage(TargetRef.hero(actor), retaliation)
        self._resolve_damage_triggers()
        if (
            weapon is not None
            and defender_card_id is not None
            and self._find_minion(target.player, target.entity_id).health <= 0
        ):
            weapon_card = self.cards.get(weapon.card_id)
            if weapon_card is not None and weapon_card.resummon_killed_minions_on_death:
                weapon.killed_minion_card_ids += (defender_card_id,)
        if weapon is not None and weapon.lifesteal and damage_dealt > 0:
            player.hero_health = min(30, player.hero_health + damage_dealt)
        if weapon is not None and player.weapon is weapon:
            weapon.durability -= 1
            if weapon.durability <= 0:
                self._destroy_weapon(actor)
        self._cleanup_deaths()
        self._resolve_board_triggers("owner_hero_attack", owner=actor, selected_event_target=target)
        self._cleanup_deaths()
        self._check_terminal()

    def _end_turn(self) -> None:
        current = self.state.players[self.state.active_player]
        self._resolve_board_triggers("owner_turn_end", owner=self.state.active_player)
        self._cleanup_deaths()
        if current.end_turn_enemy_damage > 0:
            self._damage(
                TargetRef.hero(1 - self.state.active_player),
                current.end_turn_enemy_damage,
            )
        self._check_terminal()
        if self.state.terminal:
            return
        for minion in current.board:
            if minion.frozen and minion.can_attack_ignoring_freeze(self.state.turn):
                minion.frozen = False
        if current.hero_frozen and current.hero_attack > 0 and current.hero_attacks_this_turn == 0:
            current.hero_frozen = False
        for player in self.state.players:
            for minion in player.board:
                if minion.temporary_attack_expires_turn == self.state.turn:
                    minion.attack -= minion.temporary_attack
                    minion.temporary_attack = 0
                    minion.temporary_attack_expires_turn = None
        current.hero_attack -= current.hero_temporary_attack
        current.hero_temporary_attack = 0
        current.temporary_mana = 0
        current.overloaded_mana = 0
        current.friendly_undead_died_since_last_turn = False
        current.healed_this_turn = False
        current.next_demon_cost_zero_this_turn = False
        current.next_combo_discount_this_turn = 0
        current.next_spell_discount_this_turn = 0
        if current.spell_tax_remaining_turns > 0:
            current.spell_tax_remaining_turns -= 1
        current.spells_played_previous_turn = list(current.spells_played_this_turn)
        current.spells_played_this_turn = []
        current.minion_types_played_previous_turn = list(current.minion_types_played_this_turn)
        current.minion_types_played_this_turn = []
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
        player.hero_attacks_this_turn = 0
        player.cards_played_this_turn = 0
        for minion in player.board:
            minion.attacks_this_turn = 0
        for location in player.locations:
            location.cooldown = max(0, location.cooldown - 1)
        self._refresh_dynamic_attack_bonuses()
        self._resolve_board_triggers("owner_turn_start", owner=player_index)
        self._cleanup_deaths()
        self._check_terminal()
        if self.state.terminal:
            return
        self._resolve_board_triggers("each_turn_start")
        self._cleanup_deaths()
        self._check_terminal()
        if self.state.terminal:
            return
        self._draw(player_index)
        self._check_terminal()

    def _draw(self, player_index: int) -> None:
        player = self.state.players[player_index]
        if not player.deck:
            player.fatigue += 1
            self._damage(TargetRef.hero(player_index), player.fatigue)
            self._check_terminal()
            return
        self._ensure_deck_origin_flags(player)
        card_id = player.deck.pop()
        outside_starting = player.deck_outside_starting.pop()
        card = self.cards.get(card_id)
        if card is not None and card.casts_when_drawn:
            self._resolve_board_triggers("owner_draw", owner=player_index)
            self._resolve_effect_sequence(player_index, card.effects, None, None)
            self._cleanup_deaths()
            self._check_terminal()
            if not self.state.terminal:
                self._draw(player_index)
            return
        self._add_to_hand(
            player_index,
            card_id,
            outside_starting_deck=outside_starting,
        )
        self._resolve_board_triggers("owner_draw", owner=player_index)
        self._resolve_board_triggers(
            "opponent_draw",
            owner=1 - player_index,
            triggering_player=player_index,
            triggering_card_id=card_id,
        )

    def _add_to_hand(
        self,
        player_index: int,
        card_id: str,
        *,
        outside_starting_deck: bool = False,
    ) -> None:
        player = self.state.players[player_index]
        if len(player.hand) < 10:
            player.hand.append(
                HandCard(
                    self._entity_id(),
                    card_id,
                    outside_starting_deck=outside_starting_deck,
                )
            )

    def _draw_filtered(
        self,
        player_index: int,
        predicate: Callable[[CardDef], bool],
        *,
        highest_cost: bool = False,
    ) -> None:
        player = self.state.players[player_index]
        candidates = [
            (index, self.cards[card_id])
            for index, card_id in enumerate(player.deck)
            if card_id in self.cards and predicate(self.cards[card_id])
        ]
        if not candidates:
            return
        if highest_cost:
            highest = max(definition.cost for _, definition in candidates)
            candidates = [item for item in candidates if item[1].cost == highest]
        index, definition = self.rng.choice(candidates)
        self._ensure_deck_origin_flags(player)
        player.deck.pop(index)
        outside_starting = player.deck_outside_starting.pop(index)
        self._add_to_hand(
            player_index,
            definition.card_id,
            outside_starting_deck=outside_starting,
        )
        self._resolve_board_triggers("owner_draw", owner=player_index)
        self._resolve_board_triggers(
            "opponent_draw",
            owner=1 - player_index,
            triggering_player=player_index,
            triggering_card_id=definition.card_id,
        )

    @staticmethod
    def _matches_spell_school(definition: CardDef, *, spell_school: str) -> bool:
        return definition.card_type == CardType.SPELL and definition.spell_school == spell_school

    @staticmethod
    def _matches_race(definition: CardDef, *, race: str) -> bool:
        return definition.card_type == CardType.MINION and race in definition.races

    def _spend_mana(self, player: PlayerState, amount: int) -> None:
        temporary = min(player.temporary_mana, amount)
        player.temporary_mana -= temporary
        player.mana -= amount - temporary

    @staticmethod
    def _ensure_deck_origin_flags(player: PlayerState) -> None:
        if len(player.deck_outside_starting) < len(player.deck):
            player.deck_outside_starting.extend(
                False for _ in range(len(player.deck) - len(player.deck_outside_starting))
            )
        elif len(player.deck_outside_starting) > len(player.deck):
            player.deck_outside_starting = player.deck_outside_starting[: len(player.deck)]

    @staticmethod
    def _is_outcast(player: PlayerState, hand_card: HandCard) -> bool:
        return bool(player.hand) and (
            player.hand[0].entity_id == hand_card.entity_id
            or player.hand[-1].entity_id == hand_card.entity_id
        )

    def _effective_card_cost(self, actor: int, hand_card: HandCard, card: CardDef) -> int:
        player = self.state.players[actor]
        cost = card.cost + hand_card.cost_modifier
        if card.outcast_cost >= 0 and self._is_outcast(player, hand_card):
            cost = card.outcast_cost
        if card.cost_reduction_by_weapon_attack:
            weapon = self.state.players[actor].weapon
            if weapon is not None:
                cost -= weapon.attack
        if "DEMON" in card.races:
            if player.next_demon_cost_zero_this_turn:
                cost = 0
            else:
                cost -= player.next_demon_discount
        if card.is_outcast_card or card.outcast_effects or card.outcast_cost >= 0:
            cost -= player.next_outcast_discount
        if card.is_combo_card or card.combo_effects:
            cost -= player.next_combo_discount_this_turn
        if card.card_type == CardType.SPELL:
            cost -= player.next_spell_discount_this_turn
            if player.spell_tax_remaining_turns > 0:
                cost += 1
        return max(0, cost)

    @staticmethod
    def _consume_cost_modifiers(player: PlayerState, card: CardDef) -> None:
        if "DEMON" in card.races:
            if player.next_demon_cost_zero_this_turn:
                player.next_demon_cost_zero_this_turn = False
            elif player.next_demon_discount:
                player.next_demon_discount = 0
        if card.is_outcast_card or card.outcast_effects or card.outcast_cost >= 0:
            player.next_outcast_discount = 0
        if card.is_combo_card or card.combo_effects:
            player.next_combo_discount_this_turn = 0
        if card.card_type == CardType.SPELL:
            player.next_spell_discount_this_turn = 0

    def _choose_both_active(self, actor: int) -> bool:
        return any(
            definition is not None and definition.choose_both_for_friendly
            for minion in self.state.players[actor].board
            if minion.health > 0
            for definition in (self.cards.get(minion.card_id),)
        )

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
        if mode == TargetMode.FRIENDLY_CHARACTER:
            return [TargetRef.hero(actor)] + [
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
        if mode == TargetMode.ENEMY_MINION:
            enemy = 1 - actor
            return [
                TargetRef.minion(enemy, minion.entity_id)
                for minion in self.state.players[enemy].board
                if minion.health > 0
                and (not exclude_elusive or not minion.elusive)
                and (not exclude_enemy_stealth or not minion.stealth)
            ]
        if mode == TargetMode.ENEMY_LOCATION:
            enemy = 1 - actor
            return [
                TargetRef(enemy, "location", location.entity_id)
                for location in self.state.players[enemy].locations
                if location.durability > 0
            ]
        if mode == TargetMode.ENEMY_TAUNT_MINION:
            enemy = 1 - actor
            return [
                TargetRef.minion(enemy, minion.entity_id)
                for minion in self.state.players[enemy].board
                if minion.health > 0
                and minion.taunt
                and (not exclude_elusive or not minion.elusive)
                and (not exclude_enemy_stealth or not minion.stealth)
            ]
        if mode == TargetMode.HIGH_ATTACK_MINION:
            return [
                TargetRef.minion(player_index, minion.entity_id)
                for player_index, player in enumerate(self.state.players)
                for minion in player.board
                if minion.health > 0
                and minion.attack >= 7
                and (not exclude_elusive or not minion.elusive)
                and (not exclude_enemy_stealth or player_index == actor or not minion.stealth)
            ]
        if mode == TargetMode.DAMAGED_ENEMY_MINION:
            enemy = 1 - actor
            return [
                TargetRef.minion(enemy, minion.entity_id)
                for minion in self.state.players[enemy].board
                if minion.health > 0
                and minion.health < minion.max_health
                and (not exclude_elusive or not minion.elusive)
                and (not exclude_enemy_stealth or not minion.stealth)
            ]
        if mode == TargetMode.UNDAMAGED_MINION:
            return [
                TargetRef.minion(player_index, minion.entity_id)
                for player_index, player in enumerate(self.state.players)
                for minion in player.board
                if minion.health > 0
                and minion.health == minion.max_health
                and (not exclude_elusive or not minion.elusive)
                and (not exclude_enemy_stealth or player_index == actor or not minion.stealth)
            ]
        if mode == TargetMode.ANY_MINION:
            return [
                TargetRef.minion(player_index, minion.entity_id)
                for player_index, player in enumerate(self.state.players)
                for minion in player.board
                if minion.health > 0
                and (not exclude_elusive or not minion.elusive)
                and (not exclude_enemy_stealth or player_index == actor or not minion.stealth)
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
                    and (not exclude_enemy_stealth or player_index == actor or not m.stealth)
                )
            return targets
        raise RuntimeError("unknown target mode")

    def _effective_target_mode(self, actor: int, card: CardDef) -> TargetMode:
        if not card.target_condition:
            return card.target_mode
        if card.target_condition == "weapon_equipped":
            if self.state.players[actor].weapon is None:
                return TargetMode.NONE
            return card.target_mode
        if card.target_condition == "combo_active":
            if self.state.players[actor].cards_played_this_turn == 0:
                return TargetMode.NONE
            return card.target_mode
        raise RuntimeError("unknown target condition: {}".format(card.target_condition))

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
            if amount > 0 and any(
                definition is not None and definition.grants_hero_immunity
                for minion in player.board
                if minion.health > 0
                for definition in (self.cards.get(minion.card_id),)
            ):
                return 0
            weapon = player.weapon
            weapon_card = self.cards.get(weapon.card_id) if weapon is not None else None
            if (
                amount > 0
                and weapon is not None
                and weapon_card is not None
                and weapon_card.prevents_hero_damage_by_losing_durability
            ):
                weapon.durability -= 1
                if weapon.durability <= 0:
                    self._destroy_weapon(target.player)
                return 0
            absorbed = min(player.hero_armor, amount)
            player.hero_armor -= absorbed
            player.hero_health -= amount - absorbed
            self._refresh_dynamic_attack_bonuses()
            return amount
        elif target.kind == "minion":
            minion = self._find_minion(target.player, target.entity_id)
            if amount > 0 and minion.divine_shield:
                minion.divine_shield = False
                self._resolve_board_triggers(
                    "friendly_divine_shield_lost",
                    owner=target.player,
                )
                return 0
            minion.health -= amount
            self._refresh_dynamic_attack_bonuses()
            card = self.cards.get(minion.card_id)
            if amount > 0 and card is not None and card.on_damage_effects:
                self._pending_damage_triggers.append(
                    (
                        target.player,
                        card.on_damage_effects,
                        TargetRef.minion(target.player, minion.entity_id),
                    )
                )
            if amount > 0:
                self._resolve_board_triggers("any_minion_damaged")
            return amount
        else:
            raise IllegalAction("unknown target kind")

    def _resolve_damage_triggers(self) -> None:
        while self._pending_damage_triggers:
            actor, effects, source = self._pending_damage_triggers.pop(0)
            self._resolve_effect_sequence(actor, effects, None, source)

    def _resolve_board_triggers(
        self,
        event: str,
        *,
        owner: Optional[int] = None,
        exclude_entity: Optional[int] = None,
        only_entity: Optional[int] = None,
        played_races: Tuple[str, ...] = (),
        played_spell_school: str = "",
        selected_event_target: Optional[TargetRef] = None,
        triggering_player: Optional[int] = None,
        triggering_card_id: str = "",
    ) -> None:
        effect_fields = {
            "owner_spell_cast": "on_owner_spell_cast_effects",
            "any_spell_cast": "on_any_spell_cast_effects",
            "opponent_draw": "on_opponent_draw_effects",
            "friendly_death": "on_friendly_death_effects",
            "friendly_divine_shield_lost": "on_friendly_divine_shield_lost_effects",
            "owner_hero_power": "on_owner_hero_power_effects",
            "owner_hero_attack": "on_owner_hero_attack_effects",
            "owner_turn_end": "on_owner_turn_end_effects",
            "owner_turn_start": "on_owner_turn_start_effects",
            "each_turn_start": "on_each_turn_start_effects",
            "owner_draw": "on_owner_draw_effects",
            "friendly_play": "on_friendly_play_effects",
            "friendly_summon": "on_friendly_summon_effects",
            "any_minion_damaged": "on_any_minion_damaged_effects",
            "attacked": "on_attacked_effects",
            "attacks": "on_attack_effects",
            "attack_kill": "on_attack_kill_effects",
        }
        try:
            effect_field = effect_fields[event]
        except KeyError as error:
            raise RuntimeError("unsupported board event: {}".format(event)) from error

        listeners: List[Tuple[int, int, Tuple[Effect, ...]]] = []
        for player_index, player in enumerate(self.state.players):
            if owner is not None and player_index != owner:
                continue
            for minion in player.board:
                if minion.health <= 0:
                    continue
                if exclude_entity is not None and minion.entity_id == exclude_entity:
                    continue
                if only_entity is not None and minion.entity_id != only_entity:
                    continue
                definition = self.cards.get(minion.card_id)
                if definition is None:
                    continue
                effects = getattr(definition, effect_field)
                if not effects:
                    continue
                if event == "friendly_play":
                    required_race = definition.on_friendly_play_race
                    if required_race and required_race not in played_races:
                        continue
                if event == "owner_spell_cast":
                    required_school = definition.on_owner_spell_cast_school
                    if required_school and required_school != played_spell_school:
                        continue
                if event == "friendly_summon":
                    required_race = definition.on_friendly_summon_race
                    if required_race and required_race not in played_races:
                        continue
                if event == "friendly_death":
                    required_race = definition.on_friendly_death_race
                    if required_race and required_race not in played_races:
                        continue
                listeners.append((player_index, minion.entity_id, effects))

        for player_index, entity_id, effects in listeners:
            listener = next(
                (
                    minion
                    for minion in self.state.players[player_index].board
                    if minion.entity_id == entity_id and minion.health > 0
                ),
                None,
            )
            if listener is None:
                continue
            self._resolve_effect_sequence(
                player_index,
                effects,
                selected_event_target,
                TargetRef.minion(player_index, entity_id),
                event_player=triggering_player,
                event_card_id=triggering_card_id,
            )

    def _refresh_dynamic_attack_bonuses(self) -> None:
        for player_index, player in enumerate(self.state.players):
            if player.weapon is not None:
                weapon_definition = self.cards.get(player.weapon.card_id)
                if weapon_definition is not None and weapon_definition.weapon_attack_equals_armor:
                    player.weapon.attack = player.hero_armor
                    player.hero_attack = player.hero_armor + player.hero_temporary_attack
            for recipient_index, minion in enumerate(player.board):
                desired_aura_attack = 0
                desired_aura_health = 0
                for source_index, source in enumerate(player.board):
                    if source.entity_id == minion.entity_id or source.health <= 0:
                        continue
                    source_definition = self.cards.get(source.card_id)
                    if source_definition is None:
                        continue
                    if (
                        source_definition.aura_race
                        and source_definition.aura_race not in minion.races
                    ):
                        continue
                    if (
                        source_definition.aura_adjacent_only
                        and abs(source_index - recipient_index) != 1
                    ):
                        continue
                    desired_aura_attack += source_definition.aura_attack
                    desired_aura_health += source_definition.aura_health
                minion.attack += desired_aura_attack - minion.active_aura_attack_bonus
                health_difference = desired_aura_health - minion.active_aura_health_bonus
                minion.health += health_difference
                minion.max_health += health_difference
                minion.active_aura_attack_bonus = desired_aura_attack
                minion.active_aura_health_bonus = desired_aura_health

                definition = self.cards.get(minion.card_id)
                if definition is None:
                    continue
                desired_damaged = (
                    definition.damaged_attack_bonus if 0 < minion.health < minion.max_health else 0
                )
                desired_opponent_turn = (
                    definition.opponent_turn_attack_bonus
                    if self.state.active_player != player_index
                    else 0
                )
                desired_weapon = definition.weapon_attack_bonus if player.weapon is not None else 0
                minion.attack += desired_damaged - minion.active_damaged_attack_bonus
                minion.attack += desired_opponent_turn - minion.active_opponent_turn_attack_bonus
                minion.attack += desired_weapon - minion.active_weapon_attack_bonus
                minion.active_damaged_attack_bonus = desired_damaged
                minion.active_opponent_turn_attack_bonus = desired_opponent_turn
                minion.active_weapon_attack_bonus = desired_weapon
                if definition.charge_if_weapon:
                    minion.charge = definition.charge or player.weapon is not None

    def _heal(self, target: Optional[TargetRef], amount: int) -> None:
        if target is None:
            raise IllegalAction("effect requires target")
        if target.kind == "hero":
            player = self.state.players[target.player]
            before = player.hero_health
            player.hero_health = min(30, player.hero_health + amount)
            if player.hero_health > before:
                player.healed_this_turn = True
            return
        if target.kind == "minion":
            minion = self._find_minion(target.player, target.entity_id)
            before = minion.health
            minion.health = min(minion.max_health, minion.health + amount)
            if minion.health > before:
                self.state.players[target.player].healed_this_turn = True
            self._refresh_dynamic_attack_bonuses()
            return
        raise IllegalAction("unknown target kind")

    def _buff_minion(self, target: Optional[TargetRef], attack: int, health: int) -> None:
        if target is None or target.kind != "minion":
            raise IllegalAction("buff requires a minion target")
        minion = self._find_minion(target.player, target.entity_id)
        minion.attack += attack
        minion.health += health
        minion.max_health += health
        self._refresh_dynamic_attack_bonuses()

    def _grant_minion_keyword(self, target: Optional[TargetRef], keyword: str) -> None:
        if target is None or target.kind != "minion":
            raise IllegalAction("keyword effect requires a minion target")
        if keyword not in {"taunt", "elusive", "divine_shield", "poisonous", "reborn"}:
            raise RuntimeError("unsupported granted keyword: {}".format(keyword))
        minion = self._find_minion(target.player, target.entity_id)
        setattr(minion, keyword, True)

    def _buff_weapon(self, actor: int, attack: int, durability: int) -> None:
        player = self.state.players[actor]
        if player.weapon is None:
            raise IllegalAction("weapon effect requires an equipped weapon")
        player.weapon.attack += attack
        player.weapon.durability += durability
        player.hero_attack = player.weapon.attack + player.hero_temporary_attack

    def _transform_minion(self, target: Optional[TargetRef], card_id: str) -> None:
        if target is None or target.kind != "minion":
            raise IllegalAction("transform requires a minion target")
        try:
            card = self.cards[card_id]
        except KeyError as error:
            raise RuntimeError("unknown transform result: {}".format(card_id)) from error
        if card.card_type != CardType.MINION:
            raise RuntimeError("transform result must be a minion: {}".format(card_id))
        minion = self._find_minion(target.player, target.entity_id)
        minion.card_id = card.card_id
        minion.attack = card.attack
        minion.health = card.health
        minion.max_health = card.health
        minion.taunt = card.taunt
        minion.charge = card.charge
        minion.stealth = card.stealth
        minion.lifesteal = card.lifesteal
        minion.reborn = card.reborn
        minion.elusive = card.elusive
        minion.rush = card.rush
        minion.divine_shield = card.divine_shield
        minion.poisonous = card.poisonous
        minion.races = card.races
        minion.frozen = False
        minion.temporary_attack = 0
        minion.temporary_attack_expires_turn = None
        minion.active_damaged_attack_bonus = 0
        minion.active_opponent_turn_attack_bonus = 0
        minion.active_weapon_attack_bonus = 0
        minion.active_aura_attack_bonus = 0
        minion.active_aura_health_bonus = 0
        self._refresh_dynamic_attack_bonuses()

    def _silence_minion(self, target: Optional[TargetRef]) -> None:
        if target is None or target.kind != "minion":
            raise IllegalAction("silence requires a minion target")
        minion = self._find_minion(target.player, target.entity_id)
        definition = self.cards[minion.card_id]
        damage_taken = max(0, minion.max_health - minion.health)
        minion.attack = definition.attack
        minion.max_health = definition.health
        minion.health = definition.health - damage_taken
        minion.taunt = False
        minion.charge = False
        minion.stealth = False
        minion.lifesteal = False
        minion.reborn = False
        minion.elusive = False
        minion.rush = False
        minion.divine_shield = False
        minion.poisonous = False
        minion.frozen = False
        minion.temporary_attack = 0
        minion.temporary_attack_expires_turn = None
        minion.active_damaged_attack_bonus = 0
        minion.active_opponent_turn_attack_bonus = 0
        minion.active_weapon_attack_bonus = 0
        minion.active_aura_attack_bonus = 0
        minion.active_aura_health_bonus = 0
        minion.attached_deathrattle_effects = ()
        self._refresh_dynamic_attack_bonuses()

    def _destroy_weapon(self, actor: int) -> None:
        player = self.state.players[actor]
        weapon = player.weapon
        if weapon is None:
            return
        player.weapon = None
        player.hero_attack = player.hero_temporary_attack
        self._refresh_dynamic_attack_bonuses()
        card = self.cards.get(weapon.card_id)
        if card is not None and card.resummon_killed_minions_on_death:
            for card_id in weapon.killed_minion_card_ids:
                if self._summon(actor, card_id) is None:
                    break
        if card is not None and card.deathrattle_effects:
            self._resolve_effect_sequence(
                actor,
                card.deathrattle_effects,
                None,
                TargetRef(actor, "weapon", weapon.entity_id),
            )

    def _equip_weapon(self, actor: int, card_id: str) -> None:
        try:
            card = self.cards[card_id]
        except KeyError as error:
            raise RuntimeError("unknown equipped weapon: {}".format(card_id)) from error
        if card.card_type != CardType.WEAPON:
            raise RuntimeError("equip effect requires a weapon card: {}".format(card_id))
        player = self.state.players[actor]
        if player.weapon is not None:
            self._destroy_weapon(actor)
        player.weapon = Weapon(
            entity_id=self._entity_id(),
            card_id=card.card_id,
            attack=card.attack,
            durability=card.durability,
            lifesteal=card.lifesteal,
            cannot_attack_heroes=card.weapon_cannot_attack_heroes,
        )
        player.hero_attack = card.attack + player.hero_temporary_attack
        self._refresh_dynamic_attack_bonuses()

    def _summon(
        self,
        actor: int,
        card_id: str,
        *,
        attack_bonus: int = 0,
        health_bonus: int = 0,
    ) -> Optional[Minion]:
        player = self.state.players[actor]
        if len(player.board) >= 7:
            return None
        try:
            card = self.cards[card_id]
        except KeyError as error:
            raise RuntimeError("unknown summoned card: {}".format(card_id)) from error
        if card.card_type != CardType.MINION:
            raise RuntimeError("summon effect requires a minion card: {}".format(card_id))
        minion = Minion(
            entity_id=self._entity_id(),
            card_id=card.card_id,
            attack=card.attack + attack_bonus,
            health=card.health + health_bonus,
            max_health=card.health + health_bonus,
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
        self._refresh_dynamic_attack_bonuses()
        self._resolve_board_triggers(
            "friendly_summon",
            owner=actor,
            exclude_entity=minion.entity_id,
            played_races=card.races,
        )
        return minion

    def _summon_copy(self, actor: int, source: Minion) -> Optional[Minion]:
        player = self.state.players[actor]
        if len(player.board) >= 7:
            return None
        copy_minion = copy.deepcopy(source)
        copy_minion.entity_id = self._entity_id()
        copy_minion.attacks_this_turn = 0
        copy_minion.summoned_turn = self.state.turn
        player.board.append(copy_minion)
        self._refresh_dynamic_attack_bonuses()
        definition = self.cards.get(copy_minion.card_id)
        self._resolve_board_triggers(
            "friendly_summon",
            owner=actor,
            exclude_entity=copy_minion.entity_id,
            played_races=definition.races if definition is not None else copy_minion.races,
        )
        return copy_minion

    def _spell_damage(self, actor: int) -> int:
        return sum(
            definition.spell_damage
            for minion in self.state.players[actor].board
            if minion.health > 0
            for definition in (self.cards.get(minion.card_id),)
            if definition is not None
        )

    def _transform_dynamic_hand_cards(self, actor: int, spell_card_id: str) -> None:
        player = self.state.players[actor]
        for hand_card in player.hand:
            current_definition = self.cards.get(hand_card.card_id)
            origin_definition = self.cards.get(hand_card.origin_card_id)
            if not (
                current_definition is not None
                and current_definition.transforms_in_hand_to_last_spell
            ) and not (
                origin_definition is not None and origin_definition.transforms_in_hand_to_last_spell
            ):
                continue
            if not hand_card.origin_card_id:
                hand_card.origin_card_id = hand_card.card_id
            hand_card.card_id = spell_card_id
            hand_card.attack_bonus = 0
            hand_card.health_bonus = 0
            hand_card.cost_modifier = 0

    def _summon_multiplier(self, actor: int) -> int:
        multiplier = 1
        for minion in self.state.players[actor].board:
            if minion.health <= 0:
                continue
            definition = self.cards.get(minion.card_id)
            if definition is not None:
                multiplier *= definition.summon_multiplier
        return multiplier

    def _corpse_gain_multiplier(self, actor: int) -> int:
        multiplier = 1
        for minion in self.state.players[actor].board:
            if minion.health <= 0:
                continue
            definition = self.cards.get(minion.card_id)
            if definition is not None:
                multiplier *= definition.corpse_gain_multiplier
        return multiplier

    def _gain_corpses(self, actor: int, amount: int) -> None:
        self.state.players[actor].corpses += amount * self._corpse_gain_multiplier(actor)

    def _start_discover(
        self,
        actor: int,
        candidate_ids: Tuple[str, ...],
        *,
        from_deck: bool = False,
        attack_bonus: int = 0,
        health_bonus: int = 0,
        heal_by_cost: bool = False,
        cost_modifier: int = 0,
        summon_choice: bool = False,
        freeze_choice: bool = False,
        special_tags: Tuple[str, ...] = (),
    ) -> None:
        if self.state.pending_discover_player is not None:
            self.state.pending_discover_queue.append(candidate_ids)
            return
        candidates = list(
            dict.fromkeys(card_id for card_id in candidate_ids if card_id in self.cards)
        )
        if not candidates:
            return
        option_count = min(3, len(candidates))
        self.state.pending_discover_player = actor
        self.state.pending_discover_options = tuple(self.rng.sample(candidates, option_count))
        self.state.pending_discover_from_deck = from_deck
        self.state.pending_discover_attack_bonus = attack_bonus
        self.state.pending_discover_health_bonus = health_bonus
        self.state.pending_discover_heal_by_cost = heal_by_cost
        self.state.pending_discover_cost_modifier = cost_modifier
        self.state.pending_discover_summon = summon_choice
        self.state.pending_discover_freeze = freeze_choice
        self.state.pending_discover_special_tags = special_tags

    def _summon_random_collectible_minion(self, actor: int, cost: int) -> Optional[Minion]:
        candidates = [
            card.card_id
            for card in self.cards.values()
            if card.collectible and card.card_type == CardType.MINION and card.cost == cost
        ]
        if not candidates:
            return None
        return self._summon(actor, self.rng.choice(candidates))

    def _freeze(self, target: Optional[TargetRef]) -> None:
        if target is None:
            raise IllegalAction("freeze requires a target")
        if target.kind == "hero":
            self.state.players[target.player].hero_frozen = True
            return
        if target.kind == "minion":
            self._find_minion(target.player, target.entity_id).frozen = True
            return
        raise IllegalAction("unknown target kind")

    def _temporary_attack_buff(self, target: Optional[TargetRef], attack: int) -> None:
        if target is None or target.kind != "minion":
            raise IllegalAction("temporary buff requires a minion target")
        minion = self._find_minion(target.player, target.entity_id)
        minion.attack += attack
        minion.temporary_attack += attack
        minion.temporary_attack_expires_turn = self.state.turn

    def _swap_minion_attack_and_health(self, target: Optional[TargetRef]) -> None:
        if target is None or target.kind != "minion":
            raise IllegalAction("stat swap requires a minion target")
        minion = self._find_minion(target.player, target.entity_id)
        previous_attack = minion.attack
        previous_health = minion.health
        minion.attack = previous_health
        minion.health = previous_attack
        minion.max_health = previous_attack
        minion.temporary_attack = 0
        minion.temporary_attack_expires_turn = None

    def _cleanup_deaths(self) -> None:
        pending_deathrattles: List[Tuple[int, Tuple[Effect, ...], TargetRef, Minion]] = []
        death_events: List[Tuple[int, Tuple[str, ...]]] = []
        for player_index, player in enumerate(self.state.players):
            survivors: List[Minion] = []
            for minion in player.board:
                if minion.health > 0:
                    survivors.append(minion)
                    continue
                card = self.cards.get(minion.card_id)
                death_events.append(
                    (player_index, card.races if card is not None else minion.races)
                )
                player.graveyard.append(minion.card_id)
                if card is not None and card.leaves_corpse:
                    self._gain_corpses(player_index, 1)
                if card is not None and "UNDEAD" in card.races:
                    player.friendly_undead_died_since_last_turn = True
                deathrattle_effects = (
                    card.deathrattle_effects if card is not None else ()
                ) + minion.attached_deathrattle_effects
                if deathrattle_effects:
                    pending_deathrattles.append(
                        (
                            player_index,
                            deathrattle_effects,
                            TargetRef.minion(player_index, minion.entity_id),
                            minion,
                        )
                    )
                if minion.reborn:
                    if card is None:
                        raise RuntimeError(
                            "reborn minion is missing its card definition: {}".format(
                                minion.card_id
                            )
                        )
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
        self._refresh_dynamic_attack_bonuses()
        for owner, races in death_events:
            self._resolve_board_triggers(
                "friendly_death",
                owner=owner,
                played_races=races,
            )
        for actor, effects, source, source_snapshot in pending_deathrattles:
            self._resolve_effect_sequence(
                actor,
                effects,
                None,
                source,
                source_snapshot=source_snapshot,
            )
        if any(minion.health <= 0 for player in self.state.players for minion in player.board):
            self._cleanup_deaths()

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

    def _find_location(self, player: int, entity_id: Optional[int]) -> Location:
        for location in self.state.players[player].locations:
            if location.entity_id == entity_id:
                return location
        raise IllegalAction("location entity not found")

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
            "pending_discover": {
                "player": self.state.pending_discover_player,
                "options": list(self.state.pending_discover_options)
                if self.state.pending_discover_player == player
                else [],
                "option_count": len(self.state.pending_discover_options),
            },
        }

    def public_snapshot(self) -> Dict[str, Any]:
        return {
            "turn": self.state.turn,
            "active_player": self.state.active_player,
            "players": [self._player_public(p, include_hand=False) for p in self.state.players],
            "terminal": self.state.terminal,
            "winner": self.state.winner,
            "terminal_reason": self.state.terminal_reason,
            "pending_discover_player": self.state.pending_discover_player,
            "pending_discover_option_count": len(self.state.pending_discover_options),
        }

    @staticmethod
    def _player_public(player: PlayerState, include_hand: bool) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "hero_health": player.hero_health,
            "hero_armor": player.hero_armor,
            "hero_attack": player.hero_attack,
            "hero_frozen": player.hero_frozen,
            "max_mana": player.max_mana,
            "mana": player.mana,
            "temporary_mana": player.temporary_mana,
            "overload_pending": player.overload_pending,
            "overloaded_mana": player.overloaded_mana,
            "corpses": player.corpses,
            "graveyard": list(player.graveyard),
            "friendly_undead_died_since_last_turn": (player.friendly_undead_died_since_last_turn),
            "spells_played_this_turn": list(player.spells_played_this_turn),
            "spells_played_previous_turn": list(player.spells_played_previous_turn),
            "fatigue": player.fatigue,
            "hero_power_used": player.hero_power_used,
            "deck_count": len(player.deck),
            "hand_count": len(player.hand),
            "board": [asdict(minion) for minion in player.board],
            "weapon": asdict(player.weapon) if player.weapon is not None else None,
            "locations": [asdict(location) for location in player.locations],
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
