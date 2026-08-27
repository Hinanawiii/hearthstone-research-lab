from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from ..specialist.network import NeuralPolicy, load_checkpoint
from ..specialist.train import TrainingConfig, evaluate_policy, train_self_play
from .ledger import append_ledger
from .llm import ResearchBackend, run_research
from .packet import build_research_packet, write_packet
from .probes import run_decision_probes, summarize_probe_results

CYCLE_SEED_STRIDE = 1_000_000


def run_autoresearch(
    backend: ResearchBackend,
    run_dir: Path,
    episodes: int = 100,
    evaluation_games: int = 40,
    seed: int = 100,
    acceptance_delta: float = 0.02,
    probe_samples: int = 8,
    prior_research: Optional[Sequence[Dict[str, Any]]] = None,
    ledger_path: Optional[Path] = None,
    cycle_number: int = 1,
) -> Dict[str, Any]:
    """Run one bounded research cycle over audited game-level controls."""
    run_dir.mkdir(parents=True, exist_ok=True)
    history = list(prior_research or [])
    packet = build_research_packet(
        games=max(4, min(24, evaluation_games)),
        seed=seed,
        prior_research=history,
    )
    write_packet(packet, run_dir / "research-packet.json")
    proposal = run_research(backend, packet)
    _write_json(run_dir / "proposal.json", proposal.to_dict())

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

    probe_seed = seed + 200_000
    probe_results = run_decision_probes(
        proposal.probes,
        {
            "baseline": lambda policy_seed: NeuralPolicy(
                baseline_model, seed=policy_seed
            ),
            "candidate": lambda policy_seed: NeuralPolicy(
                candidate_model,
                seed=policy_seed,
                controls=controls,
            ),
        },
        samples=probe_samples,
        seed=probe_seed,
    )
    _write_json(run_dir / "probe-results.json", probe_results)
    probe_summary = summarize_probe_results(probe_results)

    evidence = {
        "metric": "mean win rate excluding draws across random and greedy opponents",
        "acceptance_delta": acceptance_delta,
        "baseline_score": baseline_score,
        "candidate_score": candidate_score,
        "delta": delta,
        "decision_probes": probe_summary,
        "note": (
            "The intervention gate and decision probes are separate evidence. Passing the gate "
            "does not by itself prove the proposed mechanism."
        ),
    }
    append_ledger(
        ledger_path or run_dir / "theory-ledger.jsonl",
        proposal,
        result,
        json.dumps(evidence, ensure_ascii=False, sort_keys=True),
    )
    report = {
        "run_schema_version": 2,
        "cycle_number": cycle_number,
        "seed": seed,
        "evaluation_seed": evaluation_seed,
        "probe_seed": probe_seed,
        "prior_research_count": len(history),
        "proposal_id": proposal.proposal_id,
        "proposal": proposal.to_dict(),
        "result": result,
        "evidence": evidence,
        "baseline": baseline,
        "candidate": candidate,
        "baseline_training": baseline_metadata,
        "candidate_training": candidate_metadata,
        "research_controls": controls,
        "decision_probes": probe_results,
    }
    _write_json(run_dir / "report.json", report)
    return report


def run_research_campaign(
    backend: ResearchBackend,
    run_dir: Path,
    *,
    cycles: int = 1,
    episodes: int = 100,
    evaluation_games: int = 40,
    seed: int = 100,
    acceptance_delta: float = 0.02,
    probe_samples: int = 8,
) -> Dict[str, Any]:
    """Run fresh paired experiments while carrying research evidence between cycles."""
    if cycles < 1:
        raise ValueError("cycles must be positive")
    if probe_samples < 1:
        raise ValueError("probe samples must be positive")
    _assert_new_campaign(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = run_dir / "theory-ledger.jsonl"
    history: List[Dict[str, Any]] = []
    cycle_reports: List[Dict[str, Any]] = []

    for index in range(cycles):
        cycle_number = index + 1
        cycle_seed = seed + index * CYCLE_SEED_STRIDE
        cycle_dir = run_dir / "cycles" / "cycle-{:03d}".format(cycle_number)
        report = run_autoresearch(
            backend=backend,
            run_dir=cycle_dir,
            episodes=episodes,
            evaluation_games=evaluation_games,
            seed=cycle_seed,
            acceptance_delta=acceptance_delta,
            probe_samples=probe_samples,
            prior_research=list(history),
            ledger_path=ledger_path,
            cycle_number=cycle_number,
        )
        history_record = _history_record(report)
        history.append(history_record)
        cycle_reports.append(
            {
                **history_record,
                "artifact_dir": str(cycle_dir),
                "report": str(cycle_dir / "report.json"),
                "probe_results": str(cycle_dir / "probe-results.json"),
            }
        )
        _write_json(
            run_dir / "campaign-report.json",
            _campaign_report(
                cycles=cycles,
                completed=cycle_reports,
                episodes=episodes,
                evaluation_games=evaluation_games,
                seed=seed,
                acceptance_delta=acceptance_delta,
                probe_samples=probe_samples,
            ),
        )

    return _campaign_report(
        cycles=cycles,
        completed=cycle_reports,
        episodes=episodes,
        evaluation_games=evaluation_games,
        seed=seed,
        acceptance_delta=acceptance_delta,
        probe_samples=probe_samples,
    )


def _history_record(report: Dict[str, Any]) -> Dict[str, Any]:
    proposal = report["proposal"]
    return {
        "cycle_number": report["cycle_number"],
        "seed": report["seed"],
        "proposal_id": report["proposal_id"],
        "hypothesis": proposal["hypothesis"],
        "result": report["result"],
        "evidence": report["evidence"],
        "research_controls": report["research_controls"],
    }


def _campaign_report(
    *,
    cycles: int,
    completed: Sequence[Dict[str, Any]],
    episodes: int,
    evaluation_games: int,
    seed: int,
    acceptance_delta: float,
    probe_samples: int,
) -> Dict[str, Any]:
    final_result = completed[-1]["result"] if completed else None
    return {
        "campaign_schema_version": 1,
        "cycles_requested": cycles,
        "cycles_completed": len(completed),
        "result": final_result,
        "final_result": final_result,
        "config": {
            "episodes_per_cycle": episodes,
            "evaluation_games_per_opponent": evaluation_games,
            "probe_samples_per_probe": probe_samples,
            "seed_start": seed,
            "cycle_seed_stride": CYCLE_SEED_STRIDE,
            "acceptance_delta": acceptance_delta,
            "training_mode": "fresh paired baseline and candidate in every cycle",
        },
        "cycles": list(completed),
    }


def _assert_new_campaign(run_dir: Path) -> None:
    protected_outputs = (
        run_dir / "campaign-report.json",
        run_dir / "theory-ledger.jsonl",
        run_dir / "cycles",
    )
    if any(path.exists() for path in protected_outputs):
        raise FileExistsError(
            "campaign directory already contains research evidence; choose a new --run-dir"
        )


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _mean_opponent_win_rate(report: Dict[str, Any]) -> float:
    rates = [
        float(item["win_rate_excluding_draws"]) for item in report["opponents"].values()
    ]
    return sum(rates) / max(1, len(rates))
