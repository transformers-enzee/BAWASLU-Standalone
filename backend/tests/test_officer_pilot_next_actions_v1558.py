"""Deterministic officer pilot next actions; isolated SQLite, read-only endpoint."""
from app.casework import pilot_intake, CaseAssignment, CaseTransition
from app.models import User, SocialListeningResult, EvidenceAssessment, CampaignEvidence
from test_casework_workflow import dataset, confirmed
from test_officer_pilot_intake_v1544 import finding, post, _patch
from test_officer_pilot_active_case_lookup_v1547 import _case

def _run(monkeypatch,db,source=None):
    _patch(monkeypatch,[finding(posts=[source or post()])])
    return pilot_intake(db.get(User,1),db)

def _assert_counts(result, expected):
    assert result["items"][0]["pilot_next_action"]==expected
    assert result["pilot_next_action_counts"]=={expected:1}
    assert result["pilot_next_action_counts_preview_only"] is True
    assert result["pilot_next_action_not_legal_determination"] is True
    assert result["items"][0]["pilot_action_is_preliminary"] is True
    assert result["no_assignment_created"] is True

def test_ready_for_officer_review(monkeypatch):
    db=dataset()
    try:
        _assert_counts(_run(monkeypatch,db),"REVIEW_SOURCE_IN_INBOX")
        assert db.query(CaseAssignment).count()==0
    finally:db.close()

def test_missing_evidence_overrides_other_review_and_does_not_allow_creation(monkeypatch):
    db=dataset()
    try:
        db.get(SocialListeningResult,11).canonical_url=""
        db.commit()
        result=_run(monkeypatch,db)
        _assert_counts(result,"RECOVER_SAVED_EVIDENCE")
        assert result["items"][0]["casework_link"] is None
    finally:db.close()

def test_changed_jurisdiction_requires_reconfirmation(monkeypatch):
    db=dataset()
    try:
        confirmed(db)
        db.get(SocialListeningResult,11).text_content="Updated source after review"
        db.commit()
        result=_run(monkeypatch,db,post(province="Riau"))
        _assert_counts(result,"RECONFIRM_INCIDENT_JURISDICTION")
        assert result["items"][0]["incident_jurisdiction_verified"] is False
    finally:db.close()

def test_new_assessment_version_prioritizes_flag_review(monkeypatch):
    db=dataset()
    try:
        db.add(EvidenceAssessment(campaign_id=90,result_id=11,
                                  assessment_version=9,relevance_label="RELEVANT"))
        db.commit()
        source=post();source["assessment_version"]=1
        _assert_counts(_run(monkeypatch,db,source),"REVIEW_UPDATED_FLAG_ASSESSMENT")
    finally:db.close()

def test_existing_visible_case_only_when_no_higher_priority_issue(monkeypatch):
    db=dataset()
    try:
        db.add(_case(11));db.commit()
        result=_run(monkeypatch,db)
        _assert_counts(result,"CONTINUE_EXISTING_CASE")
        assert result["items"][0]["casework_link"].endswith("&tab=reports")
        assert db.query(CaseTransition).count()==0
    finally:db.close()

def test_latest_irrelevant_assessment_takes_priority_over_recovery(monkeypatch):
    db=dataset()
    try:
        db.add(EvidenceAssessment(campaign_id=90,result_id=11,
                                  assessment_version=2,relevance_label="IRRELEVANT"))
        db.get(SocialListeningResult,11).canonical_url=""
        db.commit()
        result=_run(monkeypatch,db)
        _assert_counts(result,"RECHECK_LATEST_ASSESSMENT")
        assert result["items"][0]["casework_link"] is None
    finally:db.close()

def test_removed_campaign_source_link_is_inaccessible(monkeypatch):
    db=dataset()
    try:
        db.query(CampaignEvidence).filter_by(campaign_id=90,result_id=11).delete()
        db.commit()
        result=_run(monkeypatch,db)
        _assert_counts(result,"SOURCE_UNAVAILABLE")
        assert result["items"][0]["source_link"] is None
        assert result["items"][0]["casework_link"] is None
    finally:db.close()
