# Architecture

## Design goal

CardLab separates game research from policy optimization without isolating them. The LLM receives
enough evidence to reason about game mechanisms, then controls selected inputs to a specialist
learning system. The specialist supplies empirical pressure that language reasoning alone cannot.

## Components

### Protected environment

`cardlab.engine` owns legal actions, resolution, randomness, terminal states, and information-safe
observations. The evaluator uses fixed seeds and fixed baseline policies. Candidate experiments may
not import or patch either component during a run.

### Research packet

`cardlab.research.packet` combines the finite rule contract, card definitions, baseline statistics,
representative board swings, questions, and the current executable-control catalog. It is evidence
for the research director, not a training corpus of human game records.

### LLM research director

The backend receives a strict role prompt and must return a structured `ResearchProposal`. The
proposal describes a game mechanism, predictions, falsifiers, probes, and an `experiment` block.
In a campaign, the next packet includes compact evidence from every completed cycle. The validator
rejects malformed output, unknown controls, unknown probe executors, and trainer-only work.

### Audited control surface

The current control surface has three executable families:

- concept features add named, computable game quantities to fixed feature slots;
- curricula mix ordinary games with audited strategic starting positions;
- policy priors add small, defeasible logit offsets tied to named game ideas.

These controls are intentionally narrower than arbitrary code generation. A new control requires
code review and tests before an LLM may select it. This makes the first release safe enough to
inspect while still allowing the LLM to change what the specialist perceives, practices, and
initially prefers.

Decision probes use the same catalog boundary. A proposal selects an audited executor that builds
one position and two legal choices. The runner clones the position, forces each choice, and rolls
both branches forward with matched seeds. It records two-turn damage, board-value gap, terminal
score, and the baseline/candidate policy preference. Free-form probe prose is never executed as
code.

### Specialist and gate

The specialist scores each currently legal action from an information-safe observation. Self-play
uses a policy/value objective. Every campaign cycle trains a fresh control-free baseline and a
candidate under the same episode count and seed, evaluates both against random and greedy
opponents, runs the proposal's decision probes, and records the result as accepted, rejected, or
inconclusive. Cycle seeds do not overlap. The specialist checkpoint is not carried forward; the
research evidence is.

The win-rate gate measures the intervention. Probe outcomes are separate evidence about the stated
mechanism; neither result automatically proves the hypothesis.

## Trust boundaries

Protected in a research run:

- `src/cardlab/engine.py`
- `src/cardlab/cards.py`
- the observation boundary in `Game.observation`
- evaluator opponent definitions and evaluation seeds
- proposal schemas and acceptance rule
- tests

Mutable research surfaces:

- specialist feature implementations after review
- curriculum scenario implementations after review
- policy-prior implementations after review
- model and training code
- prompts, hypotheses, and probes

Generated files belong under `runs/` and are not source code.

## Reproducibility limits

A game is determined by its seed and action sequence. PyTorch training is seeded on CPU, but exact
floating-point reproduction can still vary across PyTorch versions and hardware. Reports therefore
record configuration and should be compared statistically, not by checkpoint bytes.
