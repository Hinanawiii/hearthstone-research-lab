# Research protocol

## One cycle

1. Freeze a card-pool version, engine revision, opponent set, seed range, episode budget, and gate.
2. Generate the research packet from baseline games.
3. Ask the LLM for one falsifiable hypothesis and one bounded experiment.
4. Validate the proposal before training starts.
5. Train a baseline and candidate with the same seed and budget.
6. Evaluate both on the same held-out seeds with alternating seats.
7. Run the declared decision probes from cloned states with matched branch seeds.
8. Append the intervention result and probe evidence to the theory ledger.

Changing the gate after seeing results starts a new cycle and must not overwrite the old record.

## Multiple cycles

`cardlab autoresearch --cycles N` runs a campaign. Each cycle starts fresh baseline and candidate
training with a disjoint seed range. The next research packet contains compact hypotheses, controls,
results, and probe summaries from completed cycles, so the LLM can revise or replace its theory.
An inconclusive experiment should not be repeated unchanged.

Campaign artifacts are written under `cycles/cycle-NNN/`. Each cycle has its own packet, proposal,
checkpoints, report, and `probe-results.json`. `campaign-report.json` summarizes the run, while one
append-only `theory-ledger.jsonl` records every completed cycle. A directory containing campaign
evidence cannot be reused accidentally.

## What counts as game research

The proposal must connect a rule or observable position property to a choice. Examples include
tempo versus draw, face damage versus board control, resource use across turns, taunt timing, and
sequencing under random damage. It should say where the claim applies and where it should stop
applying.

Optimizer settings may be part of an experiment, but cannot be its entire intellectual content.
`validate_proposal` enforces this mechanically.

## Executable experiment contract

The `experiment` object contains only catalog entries supplied in the packet:

```json
{
  "feature_flags": ["board_attack_gap"],
  "curriculum": [
    {"scenario": "normal", "weight": 0.7},
    {"scenario": "tempo_deficit_draw", "weight": 0.3}
  ],
  "policy_priors": [
    {"name": "hold_draw_when_behind", "weight": 0.15}
  ]
}
```

Unknown features, scenarios, and priors are rejected. This is the first safety boundary, not the
end state. A later sandbox may let the LLM submit new candidate implementations, but protected
files and evaluation data must remain mounted read-only.

Each declared probe also selects an audited executor:

```json
{
  "name": "tempo-vs-draw-when-behind",
  "executor": "tempo_vs_draw_v1",
  "question": "Should the player draw or develop while behind on board?",
  "compared_choices": ["play Arcane Intellect", "play Chillwind Yeti"],
  "metric": "two-turn damage, board gap, and terminal score",
  "expected_relation": "develop-first takes less damage"
}
```

The executor, legal choices, and recorded metrics come from the packet's probe catalog. The LLM's
free-form position filter and explanation remain research claims, not executable code.

## Result labels

- `accepted`: candidate score improves by at least the declared delta;
- `rejected`: candidate score worsens by at least that delta;
- `inconclusive`: the observed difference falls inside the interval.

The default metric is the mean win rate, excluding draws, against random and greedy opponents. It
is a smoke gate, not a publication-quality benchmark. Probe results are reported alongside the gate
and are not folded into the accepted/rejected label. Serious claims need more seeds, confidence
intervals, stronger opponents, additional probe positions, and correction for repeated experiments.

## Leakage controls

At decision time a policy receives its own hand and public state. Opponent cards and both deck
orders stay hidden. Post-game research packets may use public transitions and aggregate outcomes;
they do not expose a future hidden draw as an input to the acting policy.

Human game records are not required by this protocol. Pretrained game knowledge may inform the
LLM's hypothesis, while simulation determines whether the proposal survives this environment.
