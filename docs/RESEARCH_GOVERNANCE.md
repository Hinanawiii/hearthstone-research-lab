# Research governance

This layer separates an LLM's game-research proposal from permission to run training or probes. The
current implementation records proposals, human decisions, card-pool dependencies, model lineage,
and experiment results. It never starts training, self-play, or a probe.

After starting the local service, review proposals at
<http://127.0.0.1:8765/research.html>.

## Proposal states

Research proposals follow this state machine:

```text
draft -> critic_reviewed -> awaiting_human -> approved
                |                 |
                +-> revision_requested -> draft
                                  |
                                  +-> rejected
```

Every transition records an actor and a review note. One LLM may draft a proposal and another may
perform the adversarial review, but only a human decision makes it approved. The schema does not try
to authenticate a human role yet; the review UI and append-only events preserve accountability.

A proposal should identify an in-game mechanism, a testable prediction, and an observation that
could falsify it. Network depth, learning rate, or training-duration tuning alone is not a game
research question.

## Finite research capsules

An approved proposal may define a research capsule: the bounded dependency set needed for that
study, rather than the entire Standard catalog. Each card has one dependency kind:

- `primary`: the direct subject of the study;
- `token`: a generated card or summoned entity;
- `random_pool`: a card reachable through Discover, generation, or another random pool;
- `interaction`: a card required to construct a critical interaction.

A human may freeze the capsule only after every dependency is `ready_for_research`. The frozen
record contains source fingerprints, generation-approval times, implementation-review times, and a
digest of the review evidence. A later source, approval, or implementation change makes the capsule
stale. A stale capsule cannot register an experiment and must be reviewed and frozen again.

## Experiments and champions

Experiment registration requires all of the following:

1. a human-approved proposal;
2. a frozen, current capsule;
3. the current champion as baseline;
4. a non-empty `required_card_ids` subset of the capsule;
5. seeds, controls, metrics, and executor configuration in the experiment record.

Registration creates an immutable experiment hash; it does not execute the experiment. Results from
an external runner still require human review. Only a human-approved experiment may promote a
candidate champion. The candidate must name that experiment's baseline champion as its parent. On
promotion, the previous champion becomes `retired` and its lineage remains recorded.

## Local API

The proposal UI uses:

```http
POST /api/research/proposals
POST /api/research/proposals/{proposal_id}/transitions
GET  /api/research/proposals
GET  /api/research/proposals/{proposal_id}
```

Capsule, champion, and experiment records are available through:

```http
POST /api/research/capsules
POST /api/research/capsules/{capsule_id}/freeze
GET  /api/research/capsules/{capsule_id}

POST /api/research/champions
POST /api/research/champions/{champion_id}/promote
GET  /api/research/champions/{champion_id}

POST /api/research/experiments
POST /api/research/experiments/{experiment_id}/transitions
GET  /api/research/experiments/{experiment_id}
```

These endpoints share the authoring-review SQLite database, so capsule gates read the same human
decisions and implementation states. The current UI covers proposal review. Capsule, experiment,
and champion screens will be added before the first real research batch runs.

## Current boundary

The framework blocks unclarified, unapproved, or unreviewed cards from a frozen pool, and prevents an
LLM from bypassing human proposal and result review. It does not yet:

- choose the first modern-card batch automatically;
- call an authoring model to write rule implementations;
- run training, self-play, or probes;
- modify algorithms or promote a model from results automatically.

It is therefore safe to accumulate proposals and authoring questions now. Real research begins only
after the relevant cards reach `ready_for_research`, a human approves a specific proposal, and its
capsule is frozen.
