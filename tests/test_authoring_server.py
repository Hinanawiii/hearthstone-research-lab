import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.request import Request, urlopen

from cardlab.authoring.server import ReviewRequestHandler
from cardlab.authoring.store import ReviewStore
from cardlab.research.governance import ResearchGovernanceStore


class AuthoringServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self.temp_dir.name) / "review.db"
        store = ReviewStore(db_path)
        store.upsert_card("MODERN_001", "现代研究牌", "一个需要核验的现代效果。")
        store.set_interview_complete("MODERN_001", True)
        self.store = store
        governance = ResearchGovernanceStore(db_path)
        handler = type(
            "TestReviewRequestHandler",
            (ReviewRequestHandler,),
            {"store": store, "governance": governance},
        )
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = "http://127.0.0.1:{}".format(self.server.server_port)

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp_dir.cleanup()

    def request(
        self, path: str, payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = Request(
            self.base_url + path,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST" if payload is not None else "GET",
        )
        with urlopen(request, timeout=2) as response:
            return json.loads(response.read().decode("utf-8"))

    def test_card_and_research_governance_routes(self) -> None:
        approved = self.request(
            "/api/cards/MODERN_001/generation-approval",
            {"approved": True, "reviewer": "human-reviewer"},
        )
        self.assertTrue(approved["card"]["ready_to_generate"])

        for status in ("generated", "under_review"):
            self.request(
                "/api/cards/MODERN_001/implementation",
                {"status": status, "reviewer": "reviewer"},
            )
        implemented = self.request(
            "/api/cards/MODERN_001/implementation",
            {
                "status": "implementation_ready",
                "reviewer": "reviewer",
                "evidence": {
                    "code_review": "approved",
                    "automated_tests": "passed",
                    "human_scenario_review": "approved",
                },
            },
        )
        self.assertTrue(implemented["card"]["ready_for_research"])
        self.assertEqual(
            implemented["card"]["implementation_reviewed_by"], "reviewer"
        )
        self.assertEqual(
            implemented["card"]["implementation_evidence"]["human_scenario_review"],
            "approved",
        )
        ai_test = self.request(
            "/api/cards/MODERN_001/implementation-tests",
            {"prompt": "请补测隐藏目标。", "requested_by": "internal-tester"},
        )
        self.assertEqual(ai_test["question"]["category"], "implementation_test")
        self.assertEqual(ai_test["card"]["implementation_status"], "under_review")
        self.assertTrue(ai_test["card"]["generation_approved"])

        proposal = self.request(
            "/api/research/proposals",
            {
                "proposal_id": "modern-window-v1",
                "title": "现代资源窗口",
                "question": "何时应该保留翻盘资源？",
                "rationale": "比较即时收益与条件收益。",
                "proposed_by": "research-llm",
            },
        )
        self.assertEqual(proposal["proposal"]["status"], "draft")
        reviewed = self.request(
            "/api/research/proposals/modern-window-v1/transitions",
            {
                "to_status": "critic_reviewed",
                "actor": "critic-llm",
                "note": "问题可证伪，但需要固定对手策略。",
            },
        )
        self.assertEqual(reviewed["proposal"]["status"], "critic_reviewed")
        proposals = self.request("/api/research/proposals")
        self.assertEqual(len(proposals["proposals"]), 1)

    def test_bulk_generation_approval_route_is_idempotent(self) -> None:
        approved = self.request(
            "/api/cards/bulk-generation-approval",
            {"reviewer": "human-reviewer", "note": "zero-question review"},
        )
        self.assertEqual(
            approved["bulk_approval"],
            {"approved_count": 1, "card_ids": ["MODERN_001"]},
        )
        self.assertTrue(self.store.get_card("MODERN_001")["ready_to_generate"])

        repeated = self.request(
            "/api/cards/bulk-generation-approval",
            {"reviewer": "human-reviewer"},
        )
        self.assertEqual(
            repeated["bulk_approval"], {"approved_count": 0, "card_ids": []}
        )

    def test_static_review_page_exposes_implementation_approval_controls(self) -> None:
        with urlopen(self.base_url + "/", timeout=2) as response:
            html = response.read().decode("utf-8")
        with urlopen(self.base_url + "/app.js", timeout=2) as response:
            javascript = response.read().decode("utf-8")

        self.assertIn('id="implementation-approval-button"', html)
        self.assertIn('id="implementation-ai-test-button"', html)
        self.assertIn('id="implementation-ai-test-dialog"', html)
        self.assertIn('name="prompt"', html)
        self.assertIn('/implementation-tests', javascript)
        self.assertIn('cancel ? "under_review" : "implementation_ready"', javascript)


if __name__ == "__main__":
    unittest.main()
