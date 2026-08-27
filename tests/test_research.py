import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cardlab.policy import GreedyPolicy
from cardlab.research.llm import MockResearchBackend, run_research
from cardlab.research.loop import CYCLE_SEED_STRIDE, run_research_campaign
from cardlab.research.packet import build_research_packet
from cardlab.research.probes import run_decision_probes
from cardlab.research.schema import ProposalError, proposal_from_dict


class ResearchProtocolTests(unittest.TestCase):
    def test_packet_exposes_rules_contract_and_evidence(self) -> None:
        packet = build_research_packet(games=2, seed=20)
        self.assertEqual(packet["packet_schema_version"], 1)
        self.assertTrue(packet["environment"]["cards"])
        self.assertTrue(packet["representative_games"])
        self.assertIn("protected_components", packet["research_contract"])
        self.assertIn(
            "tempo_vs_draw_v1",
            packet["research_contract"]["executable_catalog"]["decision_probes"],
        )

    def test_mock_backend_produces_valid_game_hypothesis(self) -> None:
        proposal = run_research(MockResearchBackend(), build_research_packet(2, 30))
        self.assertTrue(proposal.hypothesis.falsifiers)
        self.assertIn("evaluation_probe", {item.kind for item in proposal.interventions})
        self.assertGreaterEqual(len(proposal.probes[0].compared_choices), 2)

    def test_prior_research_is_exposed_to_the_next_proposal(self) -> None:
        history = [
            {
                "cycle_number": 1,
                "proposal_id": "earlier-result",
                "result": "inconclusive",
            }
        ]
        packet = build_research_packet(2, 30, prior_research=history)
        self.assertEqual(packet["prior_research"]["records"], history)
        self.assertEqual(packet["prior_research"]["cycle_count"], 1)

    def test_executable_probe_is_seeded_and_paired(self) -> None:
        proposal = run_research(MockResearchBackend(), build_research_packet(2, 32))
        factories = {"greedy": lambda seed: GreedyPolicy(seed)}
        first = run_decision_probes(proposal.probes, factories, samples=2, seed=500)
        second = run_decision_probes(proposal.probes, factories, samples=2, seed=500)
        self.assertEqual(first, second)
        variant = first["results"][0]["variants"]["greedy"]
        self.assertEqual(
            set(variant["choice_means"]), {"draw_now", "develop_minion"}
        )
        self.assertIn("terminal_score", variant["paired_effects"])

    def test_campaign_carries_history_and_uses_disjoint_cycle_seeds(self) -> None:
        calls = []

        def fake_cycle(**kwargs):
            calls.append(kwargs)
            cycle_number = kwargs["cycle_number"]
            return {
                "cycle_number": cycle_number,
                "seed": kwargs["seed"],
                "proposal_id": "proposal-{}".format(cycle_number),
                "proposal": {
                    "hypothesis": {
                        "title": "cycle {}".format(cycle_number),
                        "claim": "claim",
                        "mechanism": "mechanism",
                        "scope": "scope",
                        "evidence_needed": ["evidence"],
                        "predictions": ["prediction"],
                        "falsifiers": ["falsifier"],
                    }
                },
                "result": "inconclusive",
                "evidence": {"delta": 0.0, "decision_probes": []},
                "research_controls": {},
            }

        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory) / "campaign"
            with patch("cardlab.research.loop.run_autoresearch", side_effect=fake_cycle):
                report = run_research_campaign(
                    MockResearchBackend(),
                    run_dir,
                    cycles=2,
                    episodes=1,
                    evaluation_games=1,
                    seed=700,
                    probe_samples=1,
                )
            self.assertEqual(report["cycles_completed"], 2)
            self.assertEqual(calls[0]["prior_research"], [])
            self.assertEqual(len(calls[1]["prior_research"]), 1)
            self.assertEqual(calls[1]["seed"], 700 + CYCLE_SEED_STRIDE)
            self.assertTrue((run_dir / "campaign-report.json").exists())
            with self.assertRaisesRegex(FileExistsError, "already contains"):
                run_research_campaign(MockResearchBackend(), run_dir)

    def test_trainer_only_proposal_is_rejected(self) -> None:
        with self.assertRaisesRegex(ProposalError, "trainer-only"):
            proposal_from_dict(
                {
                    "proposal_id": "optimizer-only",
                    "hypothesis": {
                        "title": "Faster updates",
                        "claim": "A larger learning rate learns faster",
                        "mechanism": "larger gradient steps",
                        "scope": "all states",
                        "evidence_needed": ["loss"],
                        "predictions": ["loss falls faster"],
                        "falsifiers": ["loss does not fall"],
                    },
                    "interventions": [
                        {
                            "kind": "trainer",
                            "target": "learning rate",
                            "change": "double it",
                            "rationale": "faster optimization",
                        }
                    ],
                    "probes": [
                        {
                            "name": "placeholder",
                            "executor": "tempo_vs_draw_v1",
                            "question": "A or B?",
                            "position_filter": "all",
                            "compared_choices": ["A", "B"],
                            "metric": "loss",
                            "expected_relation": "A > B",
                        }
                    ],
                    "experiment": {
                        "feature_flags": [],
                        "curriculum": [{"scenario": "normal", "weight": 1.0}],
                        "policy_priors": [],
                    },
                    "expected_outcomes": ["faster"],
                    "risks": ["instability"],
                }
            )

    def test_unknown_executable_feature_is_rejected(self) -> None:
        proposal = run_research(MockResearchBackend(), build_research_packet(2, 31)).to_dict()
        proposal["experiment"]["feature_flags"] = ["opponent_future_draw"]
        with self.assertRaisesRegex(ProposalError, "unknown feature"):
            proposal_from_dict(proposal)

    def test_unknown_probe_executor_is_rejected(self) -> None:
        proposal = run_research(MockResearchBackend(), build_research_packet(2, 33)).to_dict()
        proposal["probes"][0]["executor"] = "invented_probe"
        with self.assertRaisesRegex(ProposalError, "unknown probe executor"):
            proposal_from_dict(proposal)

    def test_probe_choices_must_match_the_audited_executor(self) -> None:
        proposal = run_research(MockResearchBackend(), build_research_packet(2, 34)).to_dict()
        proposal["probes"][0]["compared_choices"] = ["draw", "do something else"]
        with self.assertRaisesRegex(ProposalError, "do not match executor"):
            proposal_from_dict(proposal)


if __name__ == "__main__":
    unittest.main()
