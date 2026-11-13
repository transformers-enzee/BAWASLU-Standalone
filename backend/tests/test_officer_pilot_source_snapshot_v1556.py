"""v155.6: refresh saved text/URL and assessment versions on officer pilot previews.

All fixtures are in-memory and never create live Supabase cases.
"""
from app.casework import pilot_intake, CaseAssignment
from app.models import User, SocialListeningResult, EvidenceAssessment
from test_casework_workflow import dataset
from test_officer_pilot_intake_v1544 import finding, post, _patch

def _run(monkeypatch, db, source):
    _patch(monkeypatch,[finding(posts=[source])])
    return pilot_intake(db.get(User,1),db)

def test_cleared_url_revokes_stale_casework_link_and_updates_recovery(monkeypatch):
    db=dataset()
    try:
        db.get(SocialListeningResult,11).canonical_url=""
        db.commit()
        data=_run(monkeypatch,db,post(url="https://example.invalid/old"))
        row=data["items"][0]
        assert row["latest_saved_eligibility"]=="LATEST_SAVED_ELIGIBLE"
        assert row["original_source_url_available"] is False
        assert row["source_recovery_reason"]=="MISSING_ORIGINAL_URL"
        assert row["casework_link"] is None
        assert row["source_link"].startswith("/inbox?")
        assert row["source_availability_changed_since_inbox"] is True
        assert data["preview_source_availability_changed_count"]==1
        assert data["preview_source_recovery_count"]==1
        assert db.query(CaseAssignment).count()==0
    finally: db.close()

def test_newly_restored_url_allows_human_intake_without_creating_case(monkeypatch):
    db=dataset()
    try:
        data=_run(monkeypatch,db,post(url=""))
        row=data["items"][0]
        assert row["latest_saved_eligibility"]=="LATEST_SAVED_ELIGIBLE"
        assert row["original_source_url_available"] is True
        assert row["source_recovery_reason"]=="NO_RECOVERY_NEEDED"
        assert row["casework_link"].endswith("&tab=assignments")
        assert row["source_availability_changed_since_inbox"] is True
        assert data["preview_new_source_review_count"]==1
        assert db.query(CaseAssignment).count()==0
    finally: db.close()

def test_retracted_saved_text_requires_recovery_even_with_old_cached_text(monkeypatch):
    db=dataset()
    try:
        db.get(SocialListeningResult,11).text_content=" "
        db.commit()
        data=_run(monkeypatch,db,post(text="Old saved text"))
        row=data["items"][0]
        assert row["source_text_available"] is False
        assert row["source_recovery_reason"]=="MISSING_ORIGINAL_TEXT"
        assert row["casework_link"] is None
        assert data["preview_current_saved_text_available_count"]==0
        assert data["preview_source_availability_changed_count"]==1
    finally: db.close()

def test_latest_assessment_version_informs_without_disclosing_post_content(monkeypatch):
    db=dataset()
    try:
        db.add(EvidenceAssessment(campaign_id=90,result_id=11,
            assessment_version=5,relevance_label="RELEVANT"))
        db.commit()
        old=post();old["assessment_version"]=1
        data=_run(monkeypatch,db,old)
        row=data["items"][0]
        assert row["latest_saved_assessment_version"]==5
        assert row["assessment_version_changed_since_inbox"] is True
        assert data["preview_assessment_version_changed_count"]==1
        assert "Dugaan pelanggaran" not in str(data)
        assert "example.test/post/11" not in str(data)
        assert row["source_truth_verified"] is False
    finally: db.close()

def test_unknown_snapshot_version_is_not_falsely_reported_changed(monkeypatch):
    db=dataset()
    try:
        data=_run(monkeypatch,db,post())
        row=data["items"][0]
        assert row["latest_saved_assessment_version"]==1
        assert row["assessment_version_changed_since_inbox"] is None
        assert data["preview_assessment_version_changed_count"]==0
    finally: db.close()
