from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List

from ..cards import CARD_POOL_VERSION, CARDS
from ..engine import Game, play_game
from ..model import ActionType
from ..policy import GreedyPolicy, RandomPolicy
from .schema import FEATURE_CATALOG, PRIOR_CATALOG, SCENARIO_CATALOG


def build_research_packet(games: int = 12, seed: int = 100) -> Dict[str, Any]:
    records: List[Dict[str, Any]] = []
    greedy_wins = random_wins = draws = 0
    stranded_mana: List[float] = []
    for index in range(games):
        game_seed = seed + index
        if index % 2 == 0:
            game = play_game(GreedyPolicy(game_seed), RandomPolicy(game_seed + 1), seed=game_seed)
            greedy_seat = 0
        else:
            game = play_game(RandomPolicy(game_seed + 1), GreedyPolicy(game_seed), seed=game_seed)
            greedy_seat = 1
        if game.state.winner is None:
            draws += 1
        elif game.state.winner == greedy_seat:
            greedy_wins += 1
        else:
            random_wins += 1
        endings = [
            event
            for event in game.history
            if event["action"]["action_type"] == ActionType.END_TURN.value
        ]
        for event in endings:
            actor = event["actor"]
            player = event["before"]["players"][actor]
            stranded_mana.append(float(player["mana"] + player["temporary_mana"]))
        records.append(_compact_game(game, greedy_seat))

    return {
        "packet_schema_version": 1,
        "environment": {
            "name": "CardLab limited-pool Hearthstone environment",
            "card_pool_version": CARD_POOL_VERSION,
            "information_model": "players see own hand and public state; deck order and opponent hand are hidden",
            "implemented_mechanics": [
                "mana and temporary mana",
                "draw, hand limit, fatigue",
                "minions, summoning sickness, charge and taunt",
                "targeted damage, random damage and simultaneous combat damage",
                "Fireblast hero power",
            ],
            "omitted_mechanics": [
                "mulligan",
                "weapons, armor, secrets, overload and freeze",
                "discover and card generation",
                "auras, silence, deathrattles and triggered-effect queues",
            ],
            "cards": [
                {
                    "card_id": card.card_id,
                    "name": card.name,
                    "type": card.card_type.value,
                    "cost": card.cost,
                    "attack": card.attack,
                    "health": card.health,
                    "taunt": card.taunt,
                    "charge": card.charge,
                    "target_mode": card.target_mode.value,
                    "effects": [asdict(effect) for effect in card.effects],
                }
                for card in CARDS.values()
            ],
        },
        "research_contract": {
            "role": "Study the game as a scientist, not merely tune a neural network.",
            "valid_interventions": [
                "curriculum: change which strategically meaningful positions are sampled",
                "feature: expose a computable game concept to the specialist",
                "policy_prior: encode a defeasible strategic prior",
                "evaluation_probe: add a controlled decision experiment",
                "trainer: allowed only alongside a game-level intervention",
            ],
            "executable_catalog": {
                "feature_flags": sorted(FEATURE_CATALOG),
                "curriculum_scenarios": sorted(SCENARIO_CATALOG),
                "policy_priors": sorted(PRIOR_CATALOG),
                "note": "The experiment field may only select these audited controls.",
            },
            "protected_components": [
                "rules engine",
                "hidden-information boundary",
                "seeded evaluator",
                "proposal validator",
            ],
            "acceptance_gate": [
                "state a falsifiable game hypothesis",
                "predict a directional effect before running the experiment",
                "include a probe comparing at least two in-game choices",
                "pass deterministic engine tests and fixed-seed evaluation",
            ],
        },
        "baseline": {
            "games": games,
            "seed_start": seed,
            "greedy_wins": greedy_wins,
            "random_wins": random_wins,
            "draws": draws,
            "greedy_win_rate_excluding_draws": greedy_wins
            / max(1, greedy_wins + random_wins),
            "mean_stranded_mana_at_end_turn": mean(stranded_mana) if stranded_mana else 0.0,
        },
        "representative_games": records[: min(6, len(records))],
        "questions_for_researcher": [
            "When is face damage preferable to board control in this closed card pool?",
            "How should tempo be valued against card draw when fatigue is reachable?",
            "When does holding a cheap card improve the next turn more than spending all mana now?",
            "How should random-damage uncertainty alter target choice and sequencing?",
        ],
    }


def _compact_game(game: Game, greedy_seat: int) -> Dict[str, Any]:
    swings = []
    for event in game.history:
        before = event["before"]["players"]
        after = event["after"]["players"]
        before_gap = _board_value(before[0]) - _board_value(before[1])
        after_gap = _board_value(after[0]) - _board_value(after[1])
        swings.append((abs(after_gap - before_gap), event))
    critical = [
        {
            "actor": event["actor"],
            "action": event["action"],
            "before": event["before"],
            "after": event["after"],
        }
        for _, event in sorted(swings, key=lambda item: item[0], reverse=True)[:3]
    ]
    return {
        "seed": game.seed,
        "greedy_seat": greedy_seat,
        "winner": game.state.winner,
        "terminal_reason": game.state.terminal_reason,
        "action_count": len(game.history),
        "largest_board_swing_transitions": critical,
    }


def _board_value(player: Dict[str, Any]) -> float:
    return float(
        sum(
            minion["attack"] + minion["health"] + (1.0 if minion["taunt"] else 0.0)
            for minion in player["board"]
        )
    )


def write_packet(packet: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(packet, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
