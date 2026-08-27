import unittest

from cardlab.research.llm import MockResearchBackend, run_research
from cardlab.research.packet import build_research_packet
from cardlab.research.schema import ProposalError, proposal_from_dict


class ResearchProtocolTests(unittest.TestCase):
    def test_packet_exposes_rules_contract_and_evidence(self) -> None:
        packet = build_research_packet(games=2, seed=20)
        self.assertEqual(packet["packet_schema_version"], 1)
        self.assertTrue(packet["environment"]["cards"])
        self.assertTrue(packet["representative_games"])
        self.assertIn("protected_components", packet["research_contract"])

    def test_mock_backend_produces_valid_game_hypothesis(self) -> None:
        proposal = run_research(MockResearchBackend(), build_research_packet(2, 30))
        self.assertTrue(proposal.hypothesis.falsifiers)
        self.assertIn("evaluation_probe", {item.kind for item in proposal.interventions})
        self.assertGreaterEqual(len(proposal.probes[0].compared_choices), 2)

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


if __name__ == "__main__":
    unittest.main()
