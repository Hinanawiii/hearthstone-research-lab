import tempfile
import unittest
from pathlib import Path

from cardlab.authoring.store import ReviewStore
from cardlab.research.governance import ResearchGovernanceStore


class ResearchGovernanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "governance.db"
        self.cards = ReviewStore(self.db_path)
        self.cards.upsert_card("MODERN_001", "现代研究牌", "一个需要核验的现代效果。")
        self.governance = ResearchGovernanceStore(self.db_path)
        self.governance.create_proposal(
            "swing-window-v1",
            "翻盘资源窗口",
            "何时应保留高翻盘价值资源？",
            "比较即时场面收益和下一回合的条件收益。",
            proposed_by="research-llm",
            evidence=[{"kind": "catalog", "claim": "该牌具有条件式翻盘效果"}],
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _approve_proposal(self) -> None:
        self.governance.transition_proposal(
            "swing-window-v1",
            "critic_reviewed",
            actor="critic-llm",
            note="问题可证伪，但必须隔离资源差。",
        )
        self.governance.transition_proposal(
            "swing-window-v1",
            "awaiting_human",
            actor="research-coordinator",
            note="反方审查完成，提交人工审核。",
        )
        self.governance.transition_proposal(
            "swing-window-v1",
            "approved",
            actor="human-reviewer",
            note="批准搭建有限牌池；不得提前运行探针。",
        )

    def _make_card_research_ready(self) -> None:
        self.cards.set_interview_complete("MODERN_001", True)
        self.cards.approve_generation("MODERN_001", "human-reviewer")
        self.cards.set_implementation_status("MODERN_001", "generated", "generator")
        self.cards.set_implementation_status("MODERN_001", "under_review", "reviewer")
        self.cards.set_implementation_status(
            "MODERN_001",
            "implementation_ready",
            "reviewer",
            evidence={
                "code_review": "approved",
                "automated_tests": "passed",
                "human_scenario_review": "approved",
            },
        )

    def test_capsule_cannot_freeze_before_card_implementation_is_ready(self) -> None:
        self._approve_proposal()
        capsule = self.governance.create_capsule(
            "modern-capsule-v1",
            "swing-window-v1",
            "现代翻盘研究胶囊",
            [{"card_id": "MODERN_001", "dependency_kind": "primary"}],
        )
        self.assertFalse(capsule["readiness"]["ready_to_freeze"])
        with self.assertRaisesRegex(ValueError, "not implementation_ready"):
            self.governance.freeze_capsule(
                "modern-capsule-v1", reviewer="human-reviewer"
            )

        self._make_card_research_ready()
        frozen = self.governance.freeze_capsule(
            "modern-capsule-v1", reviewer="human-reviewer"
        )
        self.assertEqual(frozen["status"], "frozen")
        self.assertTrue(frozen["dependency_hash"])

    def test_human_gates_proposal_experiment_and_champion_promotion(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid proposal transition"):
            self.governance.transition_proposal(
                "swing-window-v1",
                "approved",
                actor="research-llm",
                note="模型不得跳过人工审核。",
            )
        self._approve_proposal()
        self._make_card_research_ready()
        self.governance.create_capsule(
            "modern-capsule-v1",
            "swing-window-v1",
            "现代翻盘研究胶囊",
            [{"card_id": "MODERN_001", "dependency_kind": "primary"}],
        )
        self.governance.freeze_capsule(
            "modern-capsule-v1", reviewer="human-reviewer"
        )

        self.governance.register_champion(
            "champion-v0", "runs/champion-v0.pt", {"controls": []}, status="current"
        )
        self.governance.register_champion(
            "champion-v1",
            "runs/champion-v1.pt",
            {"controls": ["resource_window"]},
            parent_champion_id="champion-v0",
        )
        experiment = self.governance.register_experiment(
            "experiment-v1",
            "swing-window-v1",
            "modern-capsule-v1",
            "champion-v0",
            {
                "executor": "not-yet-implemented",
                "required_card_ids": ["MODERN_001"],
                "seed_manifest": {"train": [1, 2], "evaluation": [101, 102]},
            },
            candidate_champion_id="champion-v1",
        )
        self.assertEqual(experiment["status"], "registered")
        with self.assertRaisesRegex(ValueError, "human approval"):
            self.governance.promote_champion(
                "champion-v1", "experiment-v1", reviewer="human-reviewer"
            )

        self.governance.transition_experiment(
            "experiment-v1",
            "frozen",
            actor="human-reviewer",
            note="配置与种子已经冻结，但未在此框架中自动执行。",
        )
        self.governance.transition_experiment(
            "experiment-v1",
            "awaiting_human",
            actor="external-runner",
            note="外部执行器提交结果，等待解释审核。",
            result={"status": "completed", "paired_delta": 0.08},
        )
        self.governance.transition_experiment(
            "experiment-v1",
            "approved",
            actor="human-reviewer",
            note="结果和替代解释已审核，可以晋升。",
        )
        champion = self.governance.promote_champion(
            "champion-v1", "experiment-v1", reviewer="human-reviewer"
        )
        self.assertEqual(champion["status"], "current")
        self.assertEqual(self.governance.get_champion("champion-v0")["status"], "retired")

    def test_frozen_capsule_becomes_stale_after_card_review_changes(self) -> None:
        self._approve_proposal()
        self._make_card_research_ready()
        self.governance.create_capsule(
            "modern-capsule-v1",
            "swing-window-v1",
            "现代翻盘研究胶囊",
            [{"card_id": "MODERN_001", "dependency_kind": "primary"}],
        )
        frozen = self.governance.freeze_capsule(
            "modern-capsule-v1", reviewer="human-reviewer"
        )
        self.assertTrue(frozen["snapshot_matches_current"])

        self.cards.approve_generation(
            "MODERN_001",
            "human-reviewer",
            approved=False,
            note="new interaction requires review",
        )
        stale = self.governance.get_capsule("modern-capsule-v1")
        self.assertFalse(stale["snapshot_matches_current"])

        self.governance.register_champion(
            "champion-v0", "runs/champion-v0.pt", {"controls": []}, status="current"
        )
        with self.assertRaisesRegex(ValueError, "stale"):
            self.governance.register_experiment(
                "experiment-v1",
                "swing-window-v1",
                "modern-capsule-v1",
                "champion-v0",
                {"required_card_ids": ["MODERN_001"]},
            )


if __name__ == "__main__":
    unittest.main()
