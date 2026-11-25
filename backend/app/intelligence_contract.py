"""SmartRadar intelligence contract v1: pure, side-effect-free validation helpers.

This module does not write to the database or authorize corrections. API endpoints
must authenticate officers, enforce jurisdiction ACL and persist append-only audits.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping


CONTRACT_VERSION = "1.0.0"

FIELD_GROUPS: dict[str, tuple[str, ...]] = {
    "source_provenance": ("source_id", "platform", "source_url", "author", "published_at", "collected_at", "content_fingerprint"),
    "content": ("original_text", "language", "normalized_text", "transcript", "summary", "context_completeness"),
    "actors": ("mentioned_people", "candidate_id", "candidate_role", "parties", "actor_match_confidence"),
    "geography_time": ("country", "province", "regency", "district", "village", "event_location", "event_date", "location_basis", "location_confidence"),
    "election_context": ("election_type", "election_year", "election_stage", "electoral_district", "jurisdiction_status", "competent_authority"),
    "violation_screening": ("primary_issue", "violation_type", "violation_subtype", "alleged_conduct", "possible_legal_reference", "allegation_status"),
    "narratives": ("sentiment", "sentiment_target", "public_concern", "narrative", "stance"),
    "evidence": ("source_authenticity", "corroborating_sources", "contradicting_sources", "evidence_strength", "verification_status", "missing_evidence"),
    "patterns": ("duplicate_cluster_id", "incident_cluster_id", "engagement", "post_velocity"),
    "triage": ("relevance", "severity", "urgency", "review_priority", "recommended_action", "responsible_office", "human_review_status"),
}

INSIGHT_VARIABLES: tuple[str, ...] = (
    "issue_frequency", "trend_velocity", "geographic_concentration",
    "geographic_spread", "actor_involvement", "violation_patterns",
    "narrative_evolution", "sentiment_movement", "public_concern_intensity",
    "evidence_strength", "jurisdiction_relevance", "risk_severity",
    "urgency_escalation", "historical_comparison", "actionability",
)

SOURCE_FIELDS = frozenset(("source_id", "source_url", "original_text", "published_at", "collected_at", "content_fingerprint"))
OVERRIDABLE_FIELDS = frozenset(field for values in FIELD_GROUPS.values() for field in values) - SOURCE_FIELDS
VALID_REVIEW_STATUSES = frozenset(("unreviewed", "in_review", "approved", "rejected", "inconclusive"))
VALID_JURISDICTION_STATUSES = frozenset(("in_scope", "out_of_scope", "uncertain"))
VALID_ALLEGATION_STATUSES = frozenset(("allegation", "under_review", "substantiated_by_authority", "not_substantiated", "inconclusive"))


class ContractError(ValueError):
    """A record or correction violates the intelligence data contract."""


class CorrectionState(str, Enum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(frozen=True)
class FieldAssessment:
    field: str
    ai_value: Any
    ai_confidence: float | None
    evidence_refs: tuple[str, ...]
    assessment_version: str

    def validate(self) -> None:
        known = {field for values in FIELD_GROUPS.values() for field in values}
        if self.field not in known:
            raise ContractError("Unknown assessment field")
        if self.ai_confidence is not None and not (0 <= self.ai_confidence <= 1):
            raise ContractError("Confidence must be within [0,1]")
        if not self.assessment_version:
            raise ContractError("Assessment version is required")


@dataclass(frozen=True)
class FieldCorrection:
    field: str
    human_value: Any
    reason: str
    evidence_refs: tuple[str, ...]
    reviewer_id: str
    state: CorrectionState
    revision: int

    def validate(self) -> None:
        if self.field not in OVERRIDABLE_FIELDS:
            raise ContractError("Field cannot be overridden")
        if not self.reason.strip():
            raise ContractError("Officer justification is required")
        if not self.reviewer_id.strip():
            raise ContractError("Officer identity is required")
        if self.revision < 1:
            raise ContractError("Revision must be positive")
        if self.human_value is None:
            raise ContractError("Use an explicit unknown value; null is not an override")


def effective_value(assessment: FieldAssessment, correction: FieldCorrection | None) -> Any:
    """Only an approved matching correction supersedes AI. Never mutate originals."""
    assessment.validate()
    if correction is None:
        return assessment.ai_value
    correction.validate()
    if correction.field != assessment.field:
        raise ContractError("Correction targets a different field")
    return correction.human_value if correction.state is CorrectionState.APPROVED else assessment.ai_value


def require_expected_revision(current_revision: int, expected_revision: int) -> None:
    """Optimistic concurrency guard; caller must enforce it transactionally."""
    if current_revision != expected_revision:
        raise ContractError("Stale correction; reload before editing")


def insight_ready(record: Mapping[str, Any]) -> bool:
    """Minimal traceability gate, NOT a determination of legal validity.

    Unverified items can still generate clearly labelled preliminary warnings;
    only approved review records pass the verified-insight gate.
    """
    return (
        record.get("human_review_status") == "approved"
        and bool(record.get("source_id"))
        and bool(record.get("evidence_refs"))
        and record.get("jurisdiction_status") in VALID_JURISDICTION_STATUSES
    )
