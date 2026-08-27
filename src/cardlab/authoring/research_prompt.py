from __future__ import annotations

import json
from typing import Any, Mapping

AUTHORING_RESEARCH_SYSTEM_PROMPT = """You are CardLab's card-rules research agent. Your output is
an evidence-backed candidate answer for a human reviewer, not a final ruling and never permission
to generate implementation code.

You may search the internet. Open the underlying pages rather than relying on search snippets.
Use sources in this order: (1) official card text and patch notes, (2) maintained advanced
rulebooks or wikis that cite client observations, (3) simulator source code or reproducible client
tests, and (4) forums, videos, and social posts as leads only. Record retrieval dates and state
which claim each source supports. If sources conflict or may be patch-sensitive, say so and choose
needs_verification.

Working Hearthstone rules knowledge, to be checked against the relevant version:
- A Damage Event is different from paying Health or directly losing Health.
- Predamage triggers run before Health and Armor are reduced. They may redirect, modify, or prevent
  a Damage Event. A prevented event normally does not produce after-damage triggers.
- Multi-hit and many area effects create separate Damage Events. State can change between events,
  including an enchantment, minion, Secret, or weapon leaving play.
- Do not infer event granularity, trigger order, ownership, zone memory, or snapshot behavior from
  natural-language card text alone.

Answer the exact implementation question. Give a concise conclusion, an auditable evidence
summary, and confidence of low, medium, or high. Do not reveal private chain-of-thought. Use high
confidence only when current primary evidence or multiple independent reproducible sources agree.
Return exactly one JSON object matching the supplied schema."""


ASSESSMENT_SCHEMA = {
    "assessment_key": "stable-card-question-research-version",
    "disposition": "candidate_answer or needs_verification",
    "answer": "candidate implementation ruling",
    "reasoning": "concise evidence summary and unresolved caveats",
    "confidence": "low, medium, or high",
    "researched_by": "model or workflow identifier",
    "sources": [
        {
            "url": "https://example.test/source",
            "title": "source title",
            "source_type": (
                "official, maintained_rules, source_code, client_test, community, or other"
            ),
            "claim": "the exact claim supported by this source",
            "retrieved_at": "YYYY-MM-DD",
        }
    ],
}


def make_question_research_prompt(
    card: Mapping[str, Any],
    question: Mapping[str, Any],
) -> str:
    evidence_input = {
        "card": {
            "card_id": card.get("card_id"),
            "name": card.get("name"),
            "source_text": card.get("source_text"),
            "card_set": card.get("card_set"),
            "source_version": card.get("source_version"),
            "source_data": card.get("source_data", {}),
        },
        "question": {
            "question_id": question.get("question_id"),
            "category": question.get("category"),
            "prompt": question.get("prompt"),
            "rationale": question.get("rationale"),
            "human_answers": question.get("answers", []),
            "prior_ai_assessments": question.get("ai_assessments", []),
        },
    }
    return "{}\n\nEVIDENCE INPUT\n{}\n\nREQUIRED JSON SCHEMA\n{}".format(
        AUTHORING_RESEARCH_SYSTEM_PROMPT,
        json.dumps(evidence_input, ensure_ascii=False, sort_keys=True),
        json.dumps(ASSESSMENT_SCHEMA, ensure_ascii=False, sort_keys=True),
    )
