from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict

from ..specialist.network import NeuralPolicy, load_checkpoint
from ..specialist.train import TrainingConfig, evaluate_policy, train_self_play
from .ledger import append_ledger
from .llm import ResearchBackend, run_research
from .packet import build_research_packet, write_packet


def run_autoresearch(
    backend: ResearchBackend,
    run_dir: Path,
    episodes: int = 100,
    evaluation_games: int = 40,
    seed: int = 100,
    acceptance_delta: float = 0.02,
) -> Dict[str, Any]:
    """Run one bounded research cycle over audited game-level controls."""
    run_dir.mkdir(parents=True, exist_ok=True)
    packet = build_research_packet(games=max(4, min(24, evaluation_games)), seed=seed)
    write_packet(packet, run_dir / "research-packet.json")
    proposal = run_research(backend, packet)
    (run_dir / "proposal.json").write_text(
        json.dumps(proposal.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    controls = asdict(proposal.experiment)
    baseline_path = run_dir / "baseline.pt"
    candidate_path = run_dir / "candidate.pt"
    train_self_play(TrainingConfig(episodes=episodes, seed=seed), baseline_path)
    train_self_play(
        TrainingConfig(episodes=episodes, seed=seed, research_controls=controls), candidate_path
    )

    baseline_model, baseline_metadata = load_checkpoint(baseline_path)
    candidate_model, candidate_metadata = load_checkpoint(candidate_path)
    evaluation_seed = seed + 100_000
    baseline = evaluate_policy(
        NeuralPolicy(baseline_model), games=evaluation_games, seed=evaluation_seed
    )
    candidate = evaluate_policy(
        NeuralPolicy(candidate_model, controls=controls),
        games=evaluation_games,
        seed=evaluation_seed,
    )
    baseline_score = _mean_opponent_win_rate(baseline)
    candidate_score = _mean_opponent_win_rate(candidate)
    delta = candidate_score - baseline_score
    if delta >= acceptance_delta:
        result = "accepted"
    elif delta <= -acceptance_delta:
        result = "rejected"
    else:
        result = "inconclusive"
    evidence = {
        "metric": "mean win rate excluding draws across random and greedy opponents",
        "acceptance_delta": acceptance_delta,
        "baseline_score": baseline_score,
        "candidate_score": candidate_score,
        "delta": delta,
        "note": "This gate evaluates the intervention; it does not by itself prove the mechanism.",
    }
    append_ledger(run_dir / "theory-ledger.jsonl", proposal, result, json.dumps(evidence))
    report = {
        "run_schema_version": 1,
        "proposal_id": proposal.proposal_id,
        "result": result,
        "evidence": evidence,
        "baseline": baseline,
        "candidate": candidate,
        "baseline_training": baseline_metadata,
        "candidate_training": candidate_metadata,
        "research_controls": controls,
    }
    (run_dir / "report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return report


def _mean_opponent_win_rate(report: Dict[str, Any]) -> float:
    rates = [
        float(item["win_rate_excluding_draws"]) for item in report["opponents"].values()
    ]
    return sum(rates) / max(1, len(rates))

