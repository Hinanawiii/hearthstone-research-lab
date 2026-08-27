from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List

from .probe_catalog import PROBE_CATALOG

GAME_INTERVENTIONS = {"curriculum", "feature", "policy_prior", "evaluation_probe"}
ALL_INTERVENTIONS = GAME_INTERVENTIONS | {"trainer"}
FEATURE_CATALOG = {
    "board_attack_gap",
    "board_health_gap",
    "card_advantage",
    "fatigue_risk",
    "lethal_pressure",
    "playable_minion_mana",
}
SCENARIO_CATALOG = {"normal", "tempo_deficit_draw"}
PRIOR_CATALOG = {"face_damage", "hold_draw_when_behind", "spend_mana", "trade_up"}


class ProposalError(ValueError):
    pass


@dataclass(frozen=True)
class Hypothesis:
    title: str
    claim: str
    mechanism: str
    scope: str
    evidence_needed: List[str]
    predictions: List[str]
    falsifiers: List[str]


@dataclass(frozen=True)
class Intervention:
    kind: str
    target: str
    change: str
    rationale: str


@dataclass(frozen=True)
class Probe:
    name: str
    executor: str
    question: str
    position_filter: str
    compared_choices: List[str]
    metric: str
    expected_relation: str


@dataclass(frozen=True)
class CurriculumItem:
    scenario: str
    weight: float


@dataclass(frozen=True)
class PolicyPrior:
    name: str
    weight: float


@dataclass(frozen=True)
class ExperimentSpec:
    feature_flags: List[str]
    curriculum: List[CurriculumItem]
    policy_priors: List[PolicyPrior]


@dataclass(frozen=True)
class ResearchProposal:
    proposal_id: str
    hypothesis: Hypothesis
    interventions: List[Intervention]
    probes: List[Probe]
    experiment: ExperimentSpec
    expected_outcomes: List[str]
    risks: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def proposal_from_dict(data: Dict[str, Any]) -> ResearchProposal:
    try:
        hypothesis = Hypothesis(**data["hypothesis"])
        interventions = [Intervention(**item) for item in data["interventions"]]
        probes = [Probe(**item) for item in data["probes"]]
        experiment_data = data["experiment"]
        experiment = ExperimentSpec(
            feature_flags=experiment_data["feature_flags"],
            curriculum=[CurriculumItem(**item) for item in experiment_data["curriculum"]],
            policy_priors=[PolicyPrior(**item) for item in experiment_data["policy_priors"]],
        )
        proposal = ResearchProposal(
            proposal_id=data["proposal_id"],
            hypothesis=hypothesis,
            interventions=interventions,
            probes=probes,
            experiment=experiment,
            expected_outcomes=data["expected_outcomes"],
            risks=data["risks"],
        )
    except (KeyError, TypeError) as exc:
        raise ProposalError("proposal does not match the required schema: {}".format(exc)) from exc
    validate_proposal(proposal)
    return proposal


def validate_proposal(proposal: ResearchProposal) -> None:
    text_fields = [
        proposal.proposal_id,
        proposal.hypothesis.title,
        proposal.hypothesis.claim,
        proposal.hypothesis.mechanism,
        proposal.hypothesis.scope,
    ]
    if any(not value.strip() for value in text_fields):
        raise ProposalError("proposal identifiers and hypothesis fields must be non-empty")
    if not proposal.hypothesis.predictions or not proposal.hypothesis.falsifiers:
        raise ProposalError("a game hypothesis needs predictions and falsifiers")
    if not proposal.probes:
        raise ProposalError("at least one game-level decision probe is required")
    kinds = {intervention.kind for intervention in proposal.interventions}
    unknown = kinds - ALL_INTERVENTIONS
    if unknown:
        raise ProposalError("unknown intervention kinds: {}".format(sorted(unknown)))
    if not kinds & GAME_INTERVENTIONS:
        raise ProposalError(
            "trainer-only proposals are invalid; change a curriculum, feature, policy prior, "
            "or evaluation probe derived from a game hypothesis"
        )
    for probe in proposal.probes:
        if probe.executor not in PROBE_CATALOG:
            raise ProposalError("unknown probe executor: {}".format(probe.executor))
        if len(probe.compared_choices) < 2:
            raise ProposalError("each probe must compare at least two game choices")
        catalog = PROBE_CATALOG[probe.executor]
        executable_choices = [
            str(catalog["choice_a"]["description"]),
            str(catalog["choice_b"]["description"]),
        ]
        if probe.compared_choices != executable_choices:
            raise ProposalError(
                "probe choices do not match executor {}: {}".format(
                    probe.executor, executable_choices
                )
            )
    unknown_features = set(proposal.experiment.feature_flags) - FEATURE_CATALOG
    if unknown_features:
        raise ProposalError("unknown feature flags: {}".format(sorted(unknown_features)))
    unknown_scenarios = {
        item.scenario for item in proposal.experiment.curriculum
    } - SCENARIO_CATALOG
    if unknown_scenarios:
        raise ProposalError("unknown curriculum scenarios: {}".format(sorted(unknown_scenarios)))
    if any(item.weight <= 0 for item in proposal.experiment.curriculum):
        raise ProposalError("curriculum weights must be positive")
    unknown_priors = {item.name for item in proposal.experiment.policy_priors} - PRIOR_CATALOG
    if unknown_priors:
        raise ProposalError("unknown policy priors: {}".format(sorted(unknown_priors)))


def proposal_schema_example() -> Dict[str, Any]:
    return {
        "proposal_id": "short-kebab-case-id",
        "hypothesis": {
            "title": "Game concept under study",
            "claim": "A falsifiable claim about play in this finite environment",
            "mechanism": "Why the rules and resources should produce the claim",
            "scope": "The positions and matchups where it should hold",
            "evidence_needed": ["measurement or trace evidence"],
            "predictions": ["observable outcome if true"],
            "falsifiers": ["observable outcome that would reject it"],
        },
        "interventions": [
            {
                "kind": "evaluation_probe",
                "target": "named probe suite",
                "change": "specific experiment change",
                "rationale": "connection to the mechanism",
            }
        ],
        "probes": [
            {
                "name": "probe-name",
                "executor": "tempo_vs_draw_v1",
                "question": "decision question",
                "position_filter": "machine-checkable or precisely stated position filter",
                "compared_choices": ["play Arcane Intellect", "play Chillwind Yeti"],
                "metric": "outcome metric",
                "expected_relation": "directional prediction",
            }
        ],
        "experiment": {
            "feature_flags": ["one or more names from the packet catalog"],
            "curriculum": [{"scenario": "normal", "weight": 1.0}],
            "policy_priors": [{"name": "spend_mana", "weight": 0.1}],
        },
        "expected_outcomes": ["benchmark change with direction and scope"],
        "risks": ["confound or likely failure mode"],
    }
