from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..cards import CARDS
from ..model import Action, ActionType

CARD_IDS = tuple(sorted(CARDS))
CARD_INDEX = {card_id: index for index, card_id in enumerate(CARD_IDS)}
CONCEPT_FEATURES = (
    "board_attack_gap",
    "board_health_gap",
    "card_advantage",
    "fatigue_risk",
    "lethal_pressure",
    "playable_minion_mana",
)
STATE_SIZE = 20 + 3 * len(CARD_IDS) + len(CONCEPT_FEATURES)
ACTION_TYPE_SIZE = len(ActionType)
ACTION_SIZE = ACTION_TYPE_SIZE + 8 + len(CARD_IDS)


def _clip(value: float, scale: float) -> float:
    return max(-1.0, min(1.0, value / scale))


def encode_state(
    observation: Dict[str, Any], feature_flags: Optional[List[str]] = None
) -> List[float]:
    own = observation["own"]
    enemy = observation["enemy"]
    own_board = own["board"]
    enemy_board = enemy["board"]
    values = [
        _clip(float(observation["turn"]), 30),
        1.0 if observation["active_player"] == observation["viewer"] else -1.0,
        _clip(float(own["hero_health"]), 30),
        _clip(float(enemy["hero_health"]), 30),
        _clip(float(own["mana"] + own["temporary_mana"]), 10),
        _clip(float(enemy["mana"] + enemy["temporary_mana"]), 10),
        _clip(float(own["max_mana"]), 10),
        _clip(float(enemy["max_mana"]), 10),
        _clip(float(own["hand_count"]), 10),
        _clip(float(enemy["hand_count"]), 10),
        _clip(float(own["deck_count"]), 30),
        _clip(float(enemy["deck_count"]), 30),
        _clip(float(len(own_board)), 7),
        _clip(float(len(enemy_board)), 7),
        _clip(float(sum(m["attack"] for m in own_board)), 30),
        _clip(float(sum(m["attack"] for m in enemy_board)), 30),
        _clip(float(sum(m["health"] for m in own_board)), 35),
        _clip(float(sum(m["health"] for m in enemy_board)), 35),
        _clip(float(sum(bool(m["taunt"]) for m in own_board)), 7),
        _clip(float(sum(bool(m["taunt"]) for m in enemy_board)), 7),
    ]
    hand_counts = [0.0] * len(CARD_IDS)
    own_board_counts = [0.0] * len(CARD_IDS)
    enemy_board_counts = [0.0] * len(CARD_IDS)
    for card in own.get("hand", []):
        hand_counts[CARD_INDEX[card["card_id"]]] += 0.5
    for minion in own_board:
        own_board_counts[CARD_INDEX[minion["card_id"]]] += 0.5
    for minion in enemy_board:
        enemy_board_counts[CARD_INDEX[minion["card_id"]]] += 0.5
    enabled = set(feature_flags or [])
    own_attack = sum(m["attack"] for m in own_board)
    enemy_attack = sum(m["attack"] for m in enemy_board)
    own_health = sum(m["health"] for m in own_board)
    enemy_health = sum(m["health"] for m in enemy_board)
    playable_minion_cost = sum(
        CARDS[card["card_id"]].cost
        for card in own.get("hand", [])
        if CARDS[card["card_id"]].card_type.value == "minion"
        and CARDS[card["card_id"]].cost <= own["mana"] + own["temporary_mana"]
    )
    concepts = {
        "board_attack_gap": _clip(float(own_attack - enemy_attack), 20),
        "board_health_gap": _clip(float(own_health - enemy_health), 25),
        "card_advantage": _clip(float(own["hand_count"] - enemy["hand_count"]), 10),
        "fatigue_risk": _clip(float(enemy["deck_count"] - own["deck_count"]), 15),
        "lethal_pressure": _clip(float(own_attack - enemy["hero_health"]), 30),
        "playable_minion_mana": _clip(float(playable_minion_cost), 20),
    }
    derived = [concepts[name] if name in enabled else 0.0 for name in CONCEPT_FEATURES]
    return values + hand_counts + own_board_counts + enemy_board_counts + derived


def encode_action(observation: Dict[str, Any], action: Action) -> List[float]:
    values = [0.0] * ACTION_SIZE
    action_types = list(ActionType)
    values[action_types.index(action.action_type)] = 1.0
    card_id = _source_card_id(observation, action.source_id)
    if card_id is not None:
        values[ACTION_TYPE_SIZE + CARD_INDEX[card_id]] = 1.0
        card = CARDS[card_id]
        offset = ACTION_TYPE_SIZE + len(CARD_IDS)
        values[offset] = _clip(float(card.cost), 10)
        values[offset + 1] = _clip(float(card.attack), 10)
        values[offset + 2] = _clip(float(card.health), 10)
    else:
        offset = ACTION_TYPE_SIZE + len(CARD_IDS)
    if action.target:
        own_target = action.target.player == observation["viewer"]
        values[offset + 3] = 1.0 if own_target else -1.0
        values[offset + 4] = 1.0 if action.target.kind == "hero" else 0.0
        values[offset + 5] = 1.0 if action.target.kind == "minion" else 0.0
        target_minion = _target_minion(observation, action)
        if target_minion:
            values[offset + 6] = _clip(float(target_minion["attack"]), 10)
            values[offset + 7] = _clip(float(target_minion["health"]), 10)
    return values


def _source_card_id(observation: Dict[str, Any], source_id: Optional[int]) -> Optional[str]:
    if source_id is None:
        return None
    for card in observation["own"].get("hand", []):
        if card["entity_id"] == source_id:
            return str(card["card_id"])
    for minion in observation["own"]["board"]:
        if minion["entity_id"] == source_id:
            return str(minion["card_id"])
    return None


def _target_minion(observation: Dict[str, Any], action: Action) -> Optional[Dict[str, Any]]:
    if not action.target or action.target.kind != "minion":
        return None
    side = "own" if action.target.player == observation["viewer"] else "enemy"
    for minion in observation[side]["board"]:
        if minion["entity_id"] == action.target.entity_id:
            return dict(minion)
    return None
