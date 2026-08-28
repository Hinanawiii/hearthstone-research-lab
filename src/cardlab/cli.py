from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional, Sequence

from .authoring.importer import import_current_standard
from .authoring.review_format import render_review_document_zh
from .authoring.server import serve_review_queue
from .authoring.store import ReviewStore
from .engine import play_game
from .policy import GreedyPolicy, RandomPolicy
from .research.ledger import append_ledger
from .research.llm import MockResearchBackend, OpenAICompatibleBackend, run_research
from .research.loop import run_research_campaign
from .research.packet import build_research_packet, write_packet
from .specialist.network import NeuralPolicy, load_checkpoint
from .specialist.train import TrainingConfig, evaluate_policy, train_self_play, write_report
from .trace import game_record, write_jsonl


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cardlab", description="CardLab research harness")
    sub = parser.add_subparsers(dest="command", required=True)

    simulate = sub.add_parser("simulate", help="play reproducible baseline games")
    simulate.add_argument("--games", type=int, default=4)
    simulate.add_argument("--seed", type=int, default=1)
    simulate.add_argument("--output", type=Path)

    packet = sub.add_parser("packet", help="build an LLM game-research packet")
    packet.add_argument("--games", type=int, default=12)
    packet.add_argument("--seed", type=int, default=100)
    packet.add_argument("--output", type=Path, default=Path("runs/research-packet.json"))

    propose = sub.add_parser("propose", help="ask a research backend for a validated hypothesis")
    propose.add_argument("--backend", choices=("mock", "openai-compatible"), default="mock")
    propose.add_argument("--games", type=int, default=12)
    propose.add_argument("--seed", type=int, default=100)
    propose.add_argument("--output", type=Path, default=Path("runs/proposal.json"))
    propose.add_argument("--ledger", type=Path, default=Path("research/theory-ledger.jsonl"))

    train = sub.add_parser("train", help="run specialist neural self-play")
    train.add_argument("--episodes", type=int, default=100)
    train.add_argument("--seed", type=int, default=7)
    train.add_argument("--output", type=Path, default=Path("runs/specialist.pt"))

    evaluate = sub.add_parser("evaluate", help="evaluate a specialist checkpoint")
    evaluate.add_argument("--checkpoint", type=Path, required=True)
    evaluate.add_argument("--games", type=int, default=40)
    evaluate.add_argument("--seed", type=int, default=1000)
    evaluate.add_argument("--output", type=Path, default=Path("runs/evaluation.json"))

    autoresearch = sub.add_parser(
        "autoresearch", help="run one or more LLM-guided research cycles"
    )
    autoresearch.add_argument(
        "--backend", choices=("mock", "openai-compatible"), default="mock"
    )
    autoresearch.add_argument("--episodes", type=int, default=100)
    autoresearch.add_argument("--eval-games", type=int, default=40)
    autoresearch.add_argument("--cycles", type=int, default=1)
    autoresearch.add_argument("--probe-samples", type=int, default=8)
    autoresearch.add_argument("--seed", type=int, default=100)
    autoresearch.add_argument("--acceptance-delta", type=float, default=0.02)
    autoresearch.add_argument("--run-dir", type=Path, default=Path("runs/autoresearch-001"))

    review = sub.add_parser("review", help="serve the local card-authoring question queue")
    review.add_argument(
        "--db", type=Path, default=Path("runs/authoring/review.db"), help="SQLite database path"
    )
    review.add_argument("--port", type=int, default=8765)

    import_standard = sub.add_parser(
        "import-standard", help="import the current Standard card catalog into the review queue"
    )
    import_standard.add_argument(
        "--db", type=Path, default=Path("runs/authoring/review.db"), help="SQLite database path"
    )
    import_standard.add_argument(
        "--build", default="latest", help="HearthstoneJSON build number or latest"
    )

    render_review = sub.add_parser(
        "render-authoring-review",
        help="render a fixed-format authoring review JSON file as Chinese text without an LLM",
    )
    render_review.add_argument("--input", type=Path, required=True)
    render_review.add_argument("--output", type=Path)
    render_review.add_argument(
        "--db",
        type=Path,
        default=Path("runs/authoring/review.db"),
        help="card-name catalog database used to render Chinese names",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "simulate":
        records = []
        wins = {"greedy": 0, "random": 0, "draw": 0}
        for index in range(args.games):
            seed = args.seed + index
            game = play_game(GreedyPolicy(seed), RandomPolicy(seed + 1), seed=seed)
            records.append(game_record(game))
            if game.state.winner == 0:
                wins["greedy"] += 1
            elif game.state.winner == 1:
                wins["random"] += 1
            else:
                wins["draw"] += 1
        if args.output:
            write_jsonl(args.output, records)
        print(json.dumps({"games": args.games, "wins": wins}, sort_keys=True))
        return 0

    if args.command == "packet":
        packet = build_research_packet(args.games, args.seed)
        write_packet(packet, args.output)
        print(json.dumps({"packet": str(args.output), "baseline": packet["baseline"]}))
        return 0

    if args.command == "propose":
        packet = build_research_packet(args.games, args.seed)
        backend = (
            MockResearchBackend()
            if args.backend == "mock"
            else OpenAICompatibleBackend.from_environment()
        )
        proposal = run_research(backend, packet)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(proposal.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        append_ledger(args.ledger, proposal)
        print(json.dumps({"proposal": str(args.output), "ledger": str(args.ledger)}))
        return 0

    if args.command == "train":
        metadata = train_self_play(
            TrainingConfig(episodes=args.episodes, seed=args.seed), args.output
        )
        print(json.dumps({"checkpoint": str(args.output), "metadata": metadata}, sort_keys=True))
        return 0

    if args.command == "evaluate":
        model, metadata = load_checkpoint(args.checkpoint)
        policy = NeuralPolicy(model)
        report = evaluate_policy(policy, args.games, args.seed)
        report["checkpoint_metadata"] = metadata
        write_report(report, args.output)
        print(json.dumps({"evaluation": str(args.output), "opponents": report["opponents"]}))
        return 0
    if args.command == "autoresearch":
        backend = (
            MockResearchBackend()
            if args.backend == "mock"
            else OpenAICompatibleBackend.from_environment()
        )
        report = run_research_campaign(
            backend=backend,
            run_dir=args.run_dir,
            cycles=args.cycles,
            episodes=args.episodes,
            evaluation_games=args.eval_games,
            seed=args.seed,
            acceptance_delta=args.acceptance_delta,
            probe_samples=args.probe_samples,
        )
        print(
            json.dumps(
                {
                    "run_dir": str(args.run_dir),
                    "cycles_completed": report["cycles_completed"],
                    "result": report["final_result"],
                    "final_cycle": report["cycles"][-1],
                },
                sort_keys=True,
            )
        )
        return 0
    if args.command == "review":
        serve_review_queue(args.db, port=args.port)
        return 0
    if args.command == "import-standard":
        report = import_current_standard(ReviewStore(args.db), build=args.build)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 0
    if args.command == "render-authoring-review":
        document = json.loads(args.input.read_text(encoding="utf-8"))
        rendered = render_review_document_zh(document, ReviewStore(args.db).card_names_zh())
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
