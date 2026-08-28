from __future__ import annotations

import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Tuple
from urllib.parse import unquote, urlparse

from ..research.governance import ResearchGovernanceStore
from .store import ReviewStore

STATIC_ROOT = Path(__file__).with_name("static")


class ReviewRequestHandler(BaseHTTPRequestHandler):
    store: ReviewStore
    governance: ResearchGovernanceStore

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            if path == "/api/cards":
                self._json(HTTPStatus.OK, {"cards": self.store.list_cards()})
                return
            if path == "/api/research/proposals":
                self._json(
                    HTTPStatus.OK, {"proposals": self.governance.list_proposals()}
                )
                return
            research_route = self._research_route(path)
            if research_route is not None:
                entity, entity_id, action = research_route
                if action is not None:
                    self._error(HTTPStatus.NOT_FOUND, "unknown endpoint")
                    return
                getters = {
                    "proposals": self.governance.get_proposal,
                    "capsules": self.governance.get_capsule,
                    "champions": self.governance.get_champion,
                    "experiments": self.governance.get_experiment,
                }
                getter = getters.get(entity)
                if getter is not None:
                    self._json(HTTPStatus.OK, {entity[:-1]: getter(entity_id)})
                    return
            card_id = self._card_detail_path(path)
            if card_id is not None:
                self._json(HTTPStatus.OK, {"card": self.store.get_card(card_id)})
                return
            source_card_id = self._source_card_path(path)
            if source_card_id is not None:
                self._json(
                    HTTPStatus.OK,
                    {"source_card": self.store.get_source_card(source_card_id)},
                )
                return
            self._static(path)
        except KeyError as error:
            self._error(HTTPStatus.NOT_FOUND, str(error))
        except ValueError as error:
            self._error(HTTPStatus.BAD_REQUEST, str(error))

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            payload = self._read_json()
            if path == "/api/research/proposals":
                evidence = payload.get("evidence", [])
                if not isinstance(evidence, list):
                    raise ValueError("evidence must be a list")
                proposal = self.governance.create_proposal(
                    str(payload.get("proposal_id", "")),
                    str(payload.get("title", "")),
                    str(payload.get("question", "")),
                    str(payload.get("rationale", "")),
                    proposed_by=str(payload.get("proposed_by", "research-llm")),
                    evidence=evidence,
                )
                self._json(HTTPStatus.CREATED, {"proposal": proposal})
                return
            if path == "/api/research/capsules":
                dependencies = payload.get("dependencies", [])
                if not isinstance(dependencies, list):
                    raise ValueError("dependencies must be a list")
                capsule = self.governance.create_capsule(
                    str(payload.get("capsule_id", "")),
                    str(payload.get("proposal_id", "")),
                    str(payload.get("name", "")),
                    dependencies,
                )
                self._json(HTTPStatus.CREATED, {"capsule": capsule})
                return
            if path == "/api/research/champions":
                config = payload.get("config", {})
                if not isinstance(config, dict):
                    raise ValueError("config must be an object")
                champion = self.governance.register_champion(
                    str(payload.get("champion_id", "")),
                    str(payload.get("checkpoint_path", "")),
                    config,
                    parent_champion_id=(
                        str(payload["parent_champion_id"])
                        if payload.get("parent_champion_id")
                        else None
                    ),
                    status=str(payload.get("status", "candidate")),
                )
                self._json(HTTPStatus.CREATED, {"champion": champion})
                return
            if path == "/api/research/experiments":
                probe_spec = payload.get("probe_spec", {})
                if not isinstance(probe_spec, dict):
                    raise ValueError("probe_spec must be an object")
                experiment = self.governance.register_experiment(
                    str(payload.get("experiment_id", "")),
                    str(payload.get("proposal_id", "")),
                    str(payload.get("capsule_id", "")),
                    str(payload.get("base_champion_id", "")),
                    probe_spec,
                    candidate_champion_id=(
                        str(payload["candidate_champion_id"])
                        if payload.get("candidate_champion_id")
                        else None
                    ),
                )
                self._json(HTTPStatus.CREATED, {"experiment": experiment})
                return
            research_route = self._research_route(path)
            if research_route is not None:
                entity, entity_id, action = research_route
                if entity == "proposals" and action == "transitions":
                    proposal = self.governance.transition_proposal(
                        entity_id,
                        str(payload.get("to_status", "")),
                        actor=str(payload.get("actor", "")),
                        note=str(payload.get("note", "")),
                    )
                    self._json(HTTPStatus.OK, {"proposal": proposal})
                    return
                if entity == "capsules" and action == "freeze":
                    capsule = self.governance.freeze_capsule(
                        entity_id, reviewer=str(payload.get("reviewer", ""))
                    )
                    self._json(HTTPStatus.OK, {"capsule": capsule})
                    return
                if entity == "experiments" and action == "transitions":
                    result = payload.get("result")
                    if result is not None and not isinstance(result, dict):
                        raise ValueError("result must be an object")
                    experiment = self.governance.transition_experiment(
                        entity_id,
                        str(payload.get("to_status", "")),
                        actor=str(payload.get("actor", "")),
                        note=str(payload.get("note", "")),
                        result=result,
                    )
                    self._json(HTTPStatus.OK, {"experiment": experiment})
                    return
                if entity == "champions" and action == "promote":
                    champion = self.governance.promote_champion(
                        entity_id,
                        str(payload.get("experiment_id", "")),
                        reviewer=str(payload.get("reviewer", "")),
                    )
                    self._json(HTTPStatus.OK, {"champion": champion})
                    return
            if path == "/api/cards":
                card = self.store.upsert_card(
                    str(payload.get("card_id", "")),
                    str(payload.get("name", "")),
                    str(payload.get("source_text", "")),
                )
                self._json(HTTPStatus.CREATED, {"card": card})
                return
            if path == "/api/cards/bulk-generation-approval":
                result = self.store.approve_zero_question_cards(
                    str(payload.get("reviewer", "human")),
                    note=str(payload.get("note", "")),
                )
                self._json(HTTPStatus.OK, {"bulk_approval": result})
                return
            route = self._card_action_path(path)
            if route is not None:
                card_id, action = route
                if action == "questions":
                    questions = payload.get("questions")
                    if not isinstance(questions, list):
                        questions = [payload]
                    result = self.store.add_questions(card_id, questions)
                    self._json(HTTPStatus.CREATED, {"questions": result})
                    return
                if action == "interview":
                    card = self.store.set_interview_complete(
                        card_id, bool(payload.get("complete"))
                    )
                    self._json(HTTPStatus.OK, {"card": card})
                    return
                if action == "generation-approval":
                    card = self.store.approve_generation(
                        card_id,
                        str(payload.get("reviewer", "human")),
                        approved=bool(payload.get("approved", True)),
                        note=str(payload.get("note", "")),
                    )
                    self._json(HTTPStatus.OK, {"card": card})
                    return
                if action == "implementation":
                    evidence = payload.get("evidence", {})
                    if not isinstance(evidence, dict):
                        raise ValueError("evidence must be an object")
                    card = self.store.set_implementation_status(
                        card_id,
                        str(payload.get("status", "")),
                        str(payload.get("reviewer", "")),
                        evidence=evidence,
                        note=str(payload.get("note", "")),
                    )
                    self._json(HTTPStatus.OK, {"card": card})
                    return
            question_id = self._question_answer_path(path)
            if question_id is not None:
                question = self.store.record_answer(
                    question_id,
                    str(payload.get("answer", "")),
                    str(payload.get("respondent", "human")),
                    str(payload.get("resolution", "answered")),
                )
                self._json(HTTPStatus.CREATED, {"question": question})
                return
            assessment_question_id = self._question_assessment_path(path)
            if assessment_question_id is not None:
                sources = payload.get("sources", [])
                if not isinstance(sources, list):
                    raise ValueError("sources must be a list")
                assessment_key = str(payload.get("assessment_key", "")).strip() or None
                question = self.store.record_ai_assessment(
                    assessment_question_id,
                    str(payload.get("answer", "")),
                    reasoning=str(payload.get("reasoning", "")),
                    confidence=str(payload.get("confidence", "")),
                    disposition=str(payload.get("disposition", "candidate_answer")),
                    researched_by=str(payload.get("researched_by", "authoring-ai")),
                    sources=sources,
                    assessment_key=assessment_key,
                )
                self._json(HTTPStatus.CREATED, {"question": question})
                return
            self._error(HTTPStatus.NOT_FOUND, "unknown endpoint")
        except json.JSONDecodeError:
            self._error(HTTPStatus.BAD_REQUEST, "request body must be valid JSON")
        except KeyError as error:
            self._error(HTTPStatus.NOT_FOUND, str(error))
        except (TypeError, ValueError) as error:
            self._error(HTTPStatus.BAD_REQUEST, str(error))

    @staticmethod
    def _card_detail_path(path: str) -> Optional[str]:
        parts = path.strip("/").split("/")
        if len(parts) == 3 and parts[:2] == ["api", "cards"]:
            return unquote(parts[2])
        return None

    @staticmethod
    def _card_action_path(path: str) -> Optional[Tuple[str, str]]:
        parts = path.strip("/").split("/")
        if len(parts) == 4 and parts[:2] == ["api", "cards"]:
            return unquote(parts[2]), parts[3]
        return None

    @staticmethod
    def _source_card_path(path: str) -> Optional[str]:
        parts = path.strip("/").split("/")
        if len(parts) == 3 and parts[:2] == ["api", "source-cards"]:
            return unquote(parts[2])
        return None

    @staticmethod
    def _question_answer_path(path: str) -> Optional[str]:
        parts = path.strip("/").split("/")
        if len(parts) == 4 and parts[:2] == ["api", "questions"] and parts[3] == "answers":
            return unquote(parts[2])
        return None

    @staticmethod
    def _question_assessment_path(path: str) -> Optional[str]:
        parts = path.strip("/").split("/")
        if (
            len(parts) == 4
            and parts[:2] == ["api", "questions"]
            and parts[3] == "ai-assessments"
        ):
            return unquote(parts[2])
        return None

    @staticmethod
    def _research_route(path: str) -> Optional[Tuple[str, str, Optional[str]]]:
        parts = path.strip("/").split("/")
        if len(parts) not in (4, 5) or parts[:2] != ["api", "research"]:
            return None
        entity = parts[2]
        if entity not in {"proposals", "capsules", "champions", "experiments"}:
            return None
        return entity, unquote(parts[3]), parts[4] if len(parts) == 5 else None

    def _read_json(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        value = json.loads(body or "{}")
        if not isinstance(value, dict):
            raise ValueError("request JSON must be an object")
        return value

    def _static(self, path: str) -> None:
        if path == "/favicon.ico":
            self.send_response(HTTPStatus.NO_CONTENT)
            self.end_headers()
            return
        relative = "index.html" if path in ("", "/") else path.lstrip("/")
        candidate = (STATIC_ROOT / relative).resolve()
        if STATIC_ROOT.resolve() not in candidate.parents or not candidate.is_file():
            self._error(HTTPStatus.NOT_FOUND, "page not found")
            return
        content_type = mimetypes.guess_type(str(candidate))[0] or "application/octet-stream"
        data = candidate.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "{}; charset=utf-8".format(content_type))
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _json(self, status: HTTPStatus, payload: Mapping[str, Any]) -> None:
        data = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _error(self, status: HTTPStatus, message: str) -> None:
        self._json(status, {"error": message})

    def log_message(self, format: str, *args: Any) -> None:
        # Keep the CLI readable while still reporting one concise access line.
        print("review-ui: {}".format(format % args))


def serve_review_queue(db_path: Path, port: int = 8765) -> None:
    store = ReviewStore(db_path)
    governance = ResearchGovernanceStore(db_path)
    handler = type(
        "BoundReviewRequestHandler",
        (ReviewRequestHandler,),
        {"store": store, "governance": governance},
    )
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    print("CardLab authoring review: http://127.0.0.1:{}".format(port))
    print("Review database: {}".format(db_path.resolve()))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
