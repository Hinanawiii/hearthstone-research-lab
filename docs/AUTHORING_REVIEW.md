# Card-authoring review queue

The card-authoring review queue is a loopback-only development tool. An authoring agent can
register a card and accumulate rule questions over time. Human answers are appended to SQLite;
later decisions do not erase earlier evidence.

## Start the local page

First, synchronize the current Standard catalog. `latest` resolves to a fixed HearthstoneJSON build;
the resolved build and source URLs are stored with the imported records.

```bash
cardlab import-standard --db runs/authoring/review.db --build latest
```

As of 2026-08-27, the import covers `CORE`, `EMERALD_DREAM`, `THE_LOST_CITY`, `TIME_TRAVEL`,
`CATACLYSM`, and `ESCAPEFROM_VIOLET_HOLD`. The default database uses build `250339`: 1,166
collectible cards are in the authoring queue, while 995 non-collectible tokens and dependencies are
available in the source catalog without crowding the queue.

Imports are incremental. Unchanged cards keep their state; changed names, rules text, or structured
card data preserve prior questions and answers but reopen review. Cards that leave Standard are
removed from the active queue without deleting their history.

Then start the page:

```bash
cardlab review --db runs/authoring/review.db --port 8765
```

Open <http://127.0.0.1:8765>. The default database lives under `runs/`, is ignored by Git, and is
never uploaded by the tool. The server binds only to `127.0.0.1`; remote access and authentication
are intentionally outside the current scope.

The page lets a reviewer register source text, inspect accumulated questions, append an answer,
inspect AI research candidates and their sources, copy a candidate into the human answer form,
mark a question as requiring a client probe, inspect answer history, and close or reopen the LLM's
interview pass. It can also approve all completed, zero-question cards in one confirmed action.
Copying a candidate never saves it as a human answer.
For a generated implementation, the reviewer can approve or revoke readiness with one click, or
leave a focused test request for the authoring AI and confirm its result later.

## Generation gate

Authoring and research use three separate gates:

1. `authoring_ready`: the AI has closed its interview pass and the latest human record for every
   blocking question is `answered`;
2. `ready_to_generate`: the first gate passes and a human explicitly approves formal generation;
3. `ready_for_research`: the generated implementation has passed code review, automated tests, and
   human scenario review, and is marked `implementation_ready`.

Finishing the questions therefore does not start generation. A `needs_verification` record remains
unresolved, and even a zero-question card needs explicit approval. A new question, a semantic source
change, a reopened interview, or a new human answer revokes prior generation approval and
implementation readiness. An implementation test request is the exception: it preserves the
generation approval, implementation, and existing evidence, but sends a ready card back to
`under_review` until the new result is checked.

The bulk action only selects in-scope cards whose interview is complete, whose question count is
zero, and which are not already approved. Cards that ever raised a question remain subject to
individual review, even after all answers are resolved. Each approved card receives its own workflow
event.

An external authoring agent may only claim cards with `ready_to_generate`. This repository currently
provides the queue and enforceable gates, not an automatic authoring executor. The approval button
adds a card to the generation queue; it does not invoke a model or write rules code.

## AI research candidates

The authoring AI may research its own questions before asking a reviewer to decide. Its prompt
distinguishes Damage Events from Health payments and direct Health loss, and asks for official card
text and patch notes first. Maintained advanced rules, simulator source, reproducible client tests,
and community reports follow in that order. Every source must identify the claim it supports. The
AI should return `needs_verification` when a ruling is version-sensitive or the evidence is thin.

Research results are stored in `ai_assessments`, separately from human `answers`. A reviewer can
copy one into the answer field and edit it, but an assessment does not change `current_resolution`
or `ready_to_generate`. The reviewer still has to save a decision.

The repository currently supplies the prompt, storage contract, and review UI, but it does not run
a web-enabled model itself. An external workflow can call a model with search access and submit the
structured result through the local API. The prompt builder is
`cardlab.authoring.research_prompt`.

## Local API

Register or update a card:

```http
POST /api/cards
Content-Type: application/json

{
  "card_id": "JAIL_205",
  "name": "Rat Burglar",
  "source_text": "At the end of your turn, steal all cards that entered your opponent's hand during your turn."
}
```

Submit one or more questions:

```http
POST /api/cards/JAIL_205/questions
Content-Type: application/json

{
  "questions": [
    {
      "question_id": "rat-burglar-turn-history",
      "category": "timing",
      "prompt": "Does Rat Burglar steal cards that entered the opposing hand before Rat Burglar was played?",
      "rationale": "This decides whether the trigger queries turn history or observes only later events.",
      "blocking": true,
      "asked_by": "authoring-llm"
    }
  ]
}
```

Declare the interview pass complete:

```http
POST /api/cards/JAIL_205/interview
Content-Type: application/json

{"complete": true}
```

Approve formal generation:

```http
POST /api/cards/JAIL_205/generation-approval
Content-Type: application/json

{
  "approved": true,
  "reviewer": "human-reviewer",
  "note": "Blocking questions are reviewed; generate the first implementation."
}
```

Approve every eligible zero-question card:

```http
POST /api/cards/bulk-generation-approval
Content-Type: application/json

{
  "reviewer": "human-reviewer",
  "note": "Reviewed the zero-question queue."
}
```

The endpoint rechecks eligibility inside one transaction and returns the approved count and card
IDs. Repeated calls do not create duplicate events.

The generator and reviewers then record implementation transitions. `implementation_ready` requires
review evidence:

```http
POST /api/cards/JAIL_205/implementation
Content-Type: application/json

{
  "status": "implementation_ready",
  "reviewer": "human-reviewer",
  "note": "Code, tests, and critical scenarios were reviewed.",
  "evidence": {
    "code_review": "approved",
    "automated_tests": "passed",
    "human_scenario_review": "approved"
  }
}
```

The normal path is `not_started -> generated -> under_review -> implementation_ready`; a reviewer
may also send an implementation back to `generated` or mark it `rejected`.

An internal reviewer can leave a focused implementation test from the page or through the API:

```http
POST /api/cards/JAIL_205/implementation-tests
Content-Type: application/json

{
  "prompt": "Test the resolution when the opponent's hand is already full.",
  "requested_by": "internal-tester"
}
```

This question does not block the generation gate. If the card was `implementation_ready`, the
endpoint keeps its implementation and evidence but moves it back to `under_review`. The authoring
AI submits its result through the question's `ai-assessments` endpoint; a reviewer then decides
whether to approve the implementation again.

Read the gate, current decisions, and full answer history:

```http
GET /api/cards/JAIL_205
```

Fetch a collectible card, token, or other dependency from the source catalog by ID:

```http
GET /api/source-cards/CAP_805t
```

Reviewers normally answer through the page. The equivalent API call is:

```http
POST /api/questions/rat-burglar-turn-history/answers
Content-Type: application/json

{
  "resolution": "answered",
  "answer": "Yes. It queries the current turn's complete hand-entry history at end of turn.",
  "respondent": "human-reviewer"
}
```

`resolution` accepts `answered` or `needs_verification`. Repeated answers append history; they do
not overwrite earlier records. `current_resolution` is derived from the latest answer.

Archive an AI research candidate:

```http
POST /api/questions/rat-burglar-turn-history/ai-assessments
Content-Type: application/json

{
  "assessment_key": "rat-burglar-turn-history-web-v1",
  "disposition": "needs_verification",
  "answer": "Candidate ruling; a reviewer must still verify it.",
  "reasoning": "A short evidence summary and the unresolved boundary.",
  "confidence": "medium",
  "researched_by": "authoring-ai-web-v1",
  "sources": [
    {
      "url": "https://example.test/rules",
      "title": "Rule source title",
      "source_type": "maintained_rules",
      "claim": "The exact ruling supported by this source",
      "retrieved_at": "2026-08-27"
    }
  ]
}
```

`disposition` accepts `candidate_answer` or `needs_verification`; `confidence` accepts `low`,
`medium`, or `high`. `assessment_key` makes retries idempotent. Valid `source_type` values are
`official`, `maintained_rules`, `source_code`, `client_test`, `community`, and `other`.

## Scope

The queue records questions, decisions, generation approval, and implementation review. It cannot prove that the LLM
asked every necessary question. The authoring workflow should still apply a stable checklist for
targets, timing, zones, ownership, capacity, randomness, and snapshots, followed by an independent
counterexample pass. The queue makes unresolved ambiguity visible instead of silently encoding it
in the rules engine. See [research governance](RESEARCH_GOVERNANCE.md) for the downstream capsule
and experiment gates.
