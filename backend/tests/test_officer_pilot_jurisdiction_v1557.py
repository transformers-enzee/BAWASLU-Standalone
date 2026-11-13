"""v155.7: officer pilot jurisdiction and flag-review snapshot safety.

Run only with in-memory SQLite test fixtures.
"""
from app.casework import pilot_intake, CaseAssignment
from app.models import User, SocialListeningResult, EvidenceAssessment
from test_casework_workflow import dataset, confirmed
from test_officer_pilot_intake_v1544 import finding, post, _patch

def _run(monkeypatch,db,source):
    _patch(monkeypatch,[finding(posts=[source])])
    return pilot_intake(db.get(User,1),db)

def test_stale_verified_province_removed_after_source_text_changes(monkeypatch):
    db=dataset()
    try:
        confirmed(db)
        db.get(SocialListeningResult,11).text_content="Source text has changed after jurisdiction review."
        db.commit()
        data=_run(monkeypatch,db,post(province="Riau"))
        row=data["items"][0]
        assert row["latest_saved_eligibility"]=="LATEST_SAVED_ELIGIBLE"
        assert row["incident_jurisdiction_verified"] is False
        assert row["verified_incident_province"]==""
        assert row["latest_jurisdiction_review_state"]=="STALE_SOURCE_CHANGED"
        assert row["jurisdiction_verification_changed_since_inbox"] is True
        assert data["preview_jurisdiction_verification_changed_count"]==1
        assert db.query(CaseAssignment).count()==0
    finally: db.close()

def test_matching_human_jurisdiction_review_is_preserved(monkeypatch):
    db=dataset()
    try:
        confirmed(db)
        data=_run(monkeypatch,db,post(province="Riau"))
        row=data["items"][0]
        assert row["incident_jurisdiction_verified"] is True
        assert row["verified_incident_province"]=="Riau"
        assert row["latest_jurisdiction_review_state"]=="CONFIRMED"
        assert data["preview_jurisdiction_verification_changed_count"]==0
        assert row["source_truth_verified"] is False
    finally: db.close()

def test_cached_province_claim_without_human_review_is_not_verified(monkeypatch):
    db=dataset()
    try:
        data=_run(monkeypatch,db,post(province="Riau"))
        row=data["items"][0]
        assert row["incident_jurisdiction_verified"] is False
        assert row["verified_incident_province"]==""
        assert row["latest_jurisdiction_review_state"]=="UNREVIEWED"
        assert data["preview_jurisdiction_verification_changed_count"]==1
    finally: db.close()

def test_new_assessment_version_flags_stale_flag_signal_for_recheck(monkeypatch):
    db=dataset()
    try:
        db.add(EvidenceAssessment(campaign_id=90,result_id=11,assessment_version=7,
            relevance_label="RELEVANT"))
        db.commit()
        source=post();source["assessment_version"]=1
        data=_run(monkeypatch,db,source)
        row=data["items"][0]
        assert row["assessment_version_changed_since_inbox"] is True
        assert row["flag_review_recheck_required"] is True
        assert data["preview_flag_signal_recheck_count"]==1
        assert row["latest_saved_assessment_version"]==7
        assert db.query(CaseAssignment).count()==0
    finally: db.close()

def test_no_snapshot_version_does_not_falsely_stale_flag(monkeypatch):
    db=dataset()
    try:
        data=_run(monkeypatch,db,post())
        assert data["items"][0]["flag_review_recheck_required"] is False
        assert data["preview_flag_signal_recheck_count"]==0
    finally: db.close()
