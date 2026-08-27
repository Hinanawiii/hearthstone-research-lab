from __future__ import annotations

from dataclasses import asdict, dataclass
from statistics import mean
from typing import Any, Callable, Dict, List, Mapping, Sequence

from ..engine import Game
from ..model import Action, ActionType, HandCard, Minion
from ..policy import GreedyPolicy
from .probe_catalog import PROBE_CATALOG
from .schema import Probe

PolicyFactory = Callable[[int], Any]


@dataclass(frozen=True)
class ProbeCase:
    game: Game
    actor: int
    choices: Mapping[str, Action]


def run_decision_probes(
    probes: Sequence[Probe],
    policy_factories: Mapping[str, PolicyFactory],
    *,
    samples: int = 8,
    seed: int = 200_000,
) -> Dict[str, Any]:
    if samples < 1:
        raise ValueError("probe samples must be positive")
    results = []
    for probe_index, probe in enumerate(probes):
        probe_seed = seed + probe_index * 10_000
        variants = {
            name: _run_variant(probe.executor, factory, samples, probe_seed)
            for name, factory in policy_factories.items()
        }
        results.append(
            {
                "probe": asdict(probe),
                "catalog": PROBE_CATALOG[probe.executor],
                "seed_start": probe_seed,
                "samples": samples,
                "opponent": "greedy",
                "variants": variants,
            }
        )
    return {
        "probe_schema_version": 1,
        "samples_per_probe": samples,
        "results": results,
    }


def summarize_probe_results(report: Mapping[str, Any]) -> List[Dict[str, Any]]:
    summaries = []
    for result in report.get("results", []):
        summaries.append(
            {
                "name": result["probe"]["name"],
                "executor": result["probe"]["executor"],
                "expected_relation": result["probe"]["expected_relation"],
                "variants": {
                    name: {
                        "policy_preference_counts": variant["policy_preference_counts"],
                        "choice_means": variant["choice_means"],
                        "paired_effects": variant["paired_effects"],
                    }
                    for name, variant in result["variants"].items()
                },
            }
        )
    return summaries


def _run_variant(
    executor: str,
    policy_factory: PolicyFactory,
    samples: int,
    seed: int,
) -> Dict[str, Any]:
    sample_results: List[Dict[str, Any]] = []
    preference_counts: Dict[str, int] = {}
    for index in range(samples):
        sample_seed = seed + index
        case = _build_case(executor, sample_seed)
        choice_keys = list(case.choices)
        choices = [case.choices[key] for key in choice_keys]
        preference_policy = policy_factory(sample_seed + 100_000)
        preferred_action = preference_policy.choose(
            case.game.observation(case.actor), choices
        )
        preferred_key = choice_keys[choices.index(preferred_action)]
        preference_counts[preferred_key] = preference_counts.get(preferred_key, 0) + 1

        outcomes = {}
        for choice_key, action in case.choices.items():
            outcomes[choice_key] = _run_branch(
                case,
                action,
                policy_factory,
                sample_seed + 400_000,
            )
        sample_results.append(
            {
                "seed": sample_seed,
                "policy_preference": preferred_key,
                "outcomes": outcomes,
            }
        )

    catalog = PROBE_CATALOG[executor]
    choice_a = str(catalog["choice_a"]["key"])
    choice_b = str(catalog["choice_b"]["key"])
    metrics = list(catalog["metrics"])
    choice_means = {
        choice_key: {
            metric: mean(
                float(sample["outcomes"][choice_key][metric]) for sample in sample_results
            )
            for metric in metrics
        }
        for choice_key in (choice_a, choice_b)
    }
    paired_effects = {
        "comparison": str(catalog["comparison"]),
        **{
            metric: mean(
                float(sample["outcomes"][choice_b][metric])
                - float(sample["outcomes"][choice_a][metric])
                for sample in sample_results
            )
            for metric in metrics
        },
    }
    return {
        "policy_preference_counts": preference_counts,
        "choice_means": choice_means,
        "paired_effects": paired_effects,
        "sample_results": sample_results,
    }


def _build_case(executor: str, seed: int) -> ProbeCase:
    if executor == "tempo_vs_draw_v1":
        return _tempo_vs_draw_case(seed)
    raise ValueError("unsupported probe executor: {}".format(executor))


def _tempo_vs_draw_case(seed: int) -> ProbeCase:
    game = Game(seed=seed, starting_player=0)
    actor = game.state.active_player
    enemy = 1 - actor
    own = game.state.players[actor]
    opposing = game.state.players[enemy]
    game.state.turn = 7
    own.hero_health = opposing.hero_health = 24
    own.max_mana = own.mana = 4
    own.temporary_mana = 0
    opposing.max_mana = 3
    opposing.mana = opposing.temporary_mana = 0
    own.hand = [
        HandCard(8_000_001, "CS2_023"),
        HandCard(8_000_002, "CS2_182"),
        HandCard(8_000_003, "CS2_120"),
    ]
    own.board = [Minion(8_000_004, "CS2_120", 2, 3, 3, summoned_turn=5)]
    opposing.board = [Minion(8_000_005, "CS2_182", 4, 5, 5, summoned_turn=5)]
    game.history.clear()
    choices = {
        "draw_now": Action(ActionType.PLAY, 8_000_001),
        "develop_minion": Action(ActionType.PLAY, 8_000_002),
    }
    legal = game.legal_actions()
    if any(action not in legal for action in choices.values()):
        raise RuntimeError("probe case produced an illegal compared choice")
    return ProbeCase(game=game, actor=actor, choices=choices)


def _run_branch(
    case: ProbeCase,
    initial_action: Action,
    policy_factory: PolicyFactory,
    seed: int,
    max_actions: int = 400,
) -> Dict[str, Any]:
    game = case.game.clone()
    actor = case.actor
    initial_health = game.state.players[actor].hero_health
    game.apply(initial_action)
    policies = {
        actor: policy_factory(seed),
        1 - actor: GreedyPolicy(seed + 1),
    }
    actor_reentries = 0
    horizon_snapshot = None
    for _ in range(max_actions):
        if game.state.terminal:
            break
        active_before = game.state.active_player
        legal = game.legal_actions()
        action = policies[active_before].choose(game.observation(active_before), legal)
        game.apply(action)
        if active_before != actor and game.state.active_player == actor:
            actor_reentries += 1
            if actor_reentries == 2:
                horizon_snapshot = _strategic_snapshot(game, actor, initial_health)
        if horizon_snapshot is not None:
            break
    if horizon_snapshot is None:
        horizon_snapshot = _strategic_snapshot(game, actor, initial_health)

    for _ in range(max_actions - len(game.history)):
        if game.state.terminal:
            break
        active = game.state.active_player
        action = policies[active].choose(game.observation(active), game.legal_actions())
        game.apply(action)
    if not game.state.terminal:
        game.state.terminal_reason = "draw"
    terminal_score = 0.0
    if game.state.winner is not None:
        terminal_score = 1.0 if game.state.winner == actor else -1.0
    return {
        **horizon_snapshot,
        "terminal_score": terminal_score,
        "winner": game.state.winner,
        "terminal_reason": game.state.terminal_reason,
        "action_count": len(game.history),
    }


def _strategic_snapshot(game: Game, actor: int, initial_health: int) -> Dict[str, float]:
    own = game.state.players[actor]
    enemy = game.state.players[1 - actor]
    return {
        "two_turn_damage_taken": float(max(0, initial_health - own.hero_health)),
        "two_turn_board_value_gap": float(_board_value(own.board) - _board_value(enemy.board)),
    }


def _board_value(board: Sequence[Minion]) -> int:
    return sum(minion.attack + minion.health + int(minion.taunt) for minion in board)
