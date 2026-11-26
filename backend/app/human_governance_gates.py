"""SmartRadar three human-control gates (v184.3).

Pure decision functions. They never mutate original data, authorize paid AI
calls, or grant permissions. API callers MUST enforce RBAC and jurisdiction,
persist append-only decisions, and call these guards at the write boundary.
"""
from __future__ import annotations
from collections.abc import Mapping
from typing import Any

SCHEMA = "BAWASLU_HUMAN_GOVERNANCE_V1"
HIGH_IMPACT = frozenset(("consequential_allegation", "legal_conclusion", "urgent_escalation"))
VALID_REVIEW = frozenset(("ai_assessed", "needs_review", "officer_verified", "held", "excluded"))
VALID_INSIGHT = frozenset(("draft", "pending_approval", "approved", "rejected", "superseded"))


def _present(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def information_gate(record: Mapping[str, Any]) -> dict[str, Any]:
    """Inbox visibility is distinct from officer verification and use in insight synthesis."""
    blockers = []
    if not _present(record.get("source_id")):
        blockers.append("SOURCE_ID_REQUIRED")
    if not (_present(record.get("original_text")) or _present(record.get("source_url"))):
        blockers.append("ORIGINAL_SOURCE_REQUIRED")
    status = record.get("review_status", "ai_assessed")
    if status not in VALID_REVIEW:
        blockers.append("INVALID_REVIEW_STATUS")
    if status in ("held", "excluded"):
        blockers.append("SOURCE_HELD_OR_EXCLUDED")
    high_impact = record.get("impact_category") in HIGH_IMPACT
    officer_verified = status == "officer_verified" and _present(record.get("reviewer_id"))
    if status == "officer_verified" and not officer_verified:
        blockers.append("REVIEWER_ID_REQUIRED")
    if high_impact and not officer_verified:
        blockers.append("HIGH_IMPACT_REQUIRES_OFFICER")
    if record.get("relevance") == "irrelevant" and not officer_verified:
        blockers.append("IRRELEVANCE_REQUIRES_EXCLUSION_QA")
    return {
        "schema": SCHEMA, "gate": 1,
        "inbox_visible": bool(_present(record.get("source_id"))) and status not in ("held", "excluded"),
        "human_verified": officer_verified,
        "eligible_for_approved_claims": officer_verified and not blockers,
        "requires_review": bool(blockers) or status in ("needs_review", "ai_assessed"),
        "review_blockers": blockers,
        "raw_record_must_be_preserved": True,
        "automatic_legal_violation_confirmed": False,
    }


def insight_publication_gate(insight: Mapping[str, Any]) -> dict[str, Any]:
    """Fail closed for publishing an official Command Centre insight."""
    blockers = []
    state = insight.get("state")
    if state != "approved":
        blockers.append("INSIGHT_NOT_APPROVED")
    if not _present(insight.get("approver_id")):
        blockers.append("APPROVER_REQUIRED")
    if not _present(insight.get("approved_revision")):
        blockers.append("APPROVED_REVISION_REQUIRED")
    if not _present(insight.get("finding_id")):
        blockers.append("FINDING_ID_REQUIRED")
    evidence = insight.get("evidence_refs")
    if not isinstance(evidence, (list, tuple)) or not evidence or any(not _present(x) for x in evidence):
        blockers.append("TRACEABLE_EVIDENCE_REQUIRED")
    if not _present(insight.get("analysis_scope")):
        blockers.append("ANALYSIS_SCOPE_REQUIRED")
    if insight.get("source_revision_current") is not True:
        blockers.append("SOURCE_REVISION_STALE_OR_UNKNOWN")
    if insight.get("claim_status") == "verified" and insight.get("evidence_verified") is not True:
        blockers.append("VERIFIED_CLAIM_WITHOUT_VERIFICATION")
    if insight.get("contains_high_impact_claims") is True and insight.get("high_impact_reviewed") is not True:
        blockers.append("HIGH_IMPACT_REVIEW_REQUIRED")
    if state == "superseded":
        blockers.append("SUPERSEDED")
    return {
        "schema": SCHEMA, "gate": 2, "publish_allowed": not blockers,
        "review_blockers": blockers, "publication_requires_server_side_enforcement": True,
        "unreviewed_inputs_may_only_support_labelled_preliminary_analysis": True,
    }


def learning_release_gate(release: Mapping[str, Any]) -> dict[str, Any]:
    """Model improvement must not automatically learn from unapproved overrides."""
    blockers = []
    if not _present(release.get("release_id")):
        blockers.append("RELEASE_ID_REQUIRED")
    if not _present(release.get("administrator_id")):
        blockers.append("ADMINISTRATOR_APPROVAL_REQUIRED")
    if release.get("dataset_reviewed") is not True:
        blockers.append("DATASET_REVIEW_REQUIRED")
    if release.get("held_out_evaluation_passed") is not True:
        blockers.append("EVALUATION_NOT_PASSED")
    if release.get("regression_passed") is not True:
        blockers.append("REGRESSION_NOT_PASSED")
    if release.get("security_review_passed") is not True:
        blockers.append("SECURITY_REVIEW_NOT_PASSED")
    if release.get("version_pinned") is not True:
        blockers.append("VERSION_NOT_PINNED")
    return {
        "schema": SCHEMA, "gate": 3, "release_allowed": not blockers,
        "review_blockers": blockers, "training_only_from_approved_examples": True,
        "does_not_trigger_training_or_deployment": True,
    }


def resolve_reviewed_field(ai_value: Any, officer_value: Any, review_state: str) -> Any:
    """Approved officer value wins; null is never a correction."""
    return officer_value if review_state == "approved" and officer_value is not None else ai_value
