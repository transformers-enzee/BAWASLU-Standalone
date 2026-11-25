"""Contract regression tests: no provider calls or database writes."""
import pytest

from app.intelligence_contract import (
    CONTRACT_VERSION, FIELD_GROUPS, INSIGHT_VARIABLES, SOURCE_FIELDS,
    ContractError, CorrectionState, FieldAssessment, FieldCorrection,
    effective_value, insight_ready, require_expected_revision,
)


def _assessment(field="violation_type"):
    return FieldAssessment(field, "money_politics", 0.74, ("SOCIAL-1",), CONTRACT_VERSION)


def _correction(state=CorrectionState.APPROVED, field="violation_type"):
    return FieldCorrection(field, "other_regulatory_issue", "Reviewed original source", ("SOCIAL-1",), "officer-1", state, 1)


def test_contract_has_ten_groups_and_fifteen_insight_variables():
    assert len(FIELD_GROUPS) == 10
    assert len(INSIGHT_VARIABLES) == 15
    assert all(FIELD_GROUPS.values())


def test_approved_officer_override_wins():
    original = _assessment()
    assert effective_value(original, _correction()) == "other_regulatory_issue"
    assert original.ai_value == "money_politics"


@pytest.mark.parametrize("state", [CorrectionState.PROPOSED, CorrectionState.REJECTED])
def test_unapproved_corrections_do_not_replace_ai(state):
    assert effective_value(_assessment(), _correction(state)) == "money_politics"


def test_original_source_fields_are_immutable():
    assert "original_text" in SOURCE_FIELDS
    with pytest.raises(ContractError):
        effective_value(_assessment("original_text"), _correction(field="original_text"))


def test_justification_and_actor_required():
    with pytest.raises(ContractError):
        effective_value(_assessment(), FieldCorrection("violation_type", "other", " ", (), "officer-1", CorrectionState.APPROVED, 1))
    with pytest.raises(ContractError):
        effective_value(_assessment(), FieldCorrection("violation_type", "other", "reason", (), "", CorrectionState.APPROVED, 1))


def test_wrong_field_and_stale_revision_fail():
    with pytest.raises(ContractError):
        effective_value(_assessment(), _correction(field="candidate_id"))
    with pytest.raises(ContractError):
        require_expected_revision(2, 1)


def test_unverified_records_cannot_be_presented_as_verified_insights():
    record = {"source_id": "SOCIAL-1", "evidence_refs": ["SOCIAL-1"], "jurisdiction_status": "uncertain", "human_review_status": "unreviewed"}
    assert not insight_ready(record)
    assert insight_ready({**record, "human_review_status": "approved"})
