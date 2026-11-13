"""v155.4: latest saved-source access and relevance checks for officer pilot.

Every fixture uses isolated SQLite; no live cases or Supabase writes.
"""
from app.casework import pilot_intake, CaseAssignment
from app.models import User, CampaignEvidence, EvidenceAssessment
from test_casework_workflow import dataset
from test_officer_pilot_intake_v1544 import finding, post, _patch
from test_officer_pilot_active_case_lookup_v1547 import _case

def test_new_irrelevant_assessment_disables_stale_casework_link(monkeypatch):
    db=dataset()
    try:
        _patch(monkeypatch,[finding(posts=[post()])])
        db.add(_case(11))
        db.add(EvidenceAssessment(campaign_id=90,result_id=11,
            assessment_version=2,relevance_label="IRRELEVANT"))
        db.commit()
        response=pilot_intake(db.get(User,1),db)
        row=response["items"][0]
        assert row["latest_saved_eligibility"]=="LATEST_ASSESSMENT_NOT_RELEVANT"
        assert row["casework_link"] is None
        assert row["source_link"] is not None
        assert row["review_step"]=="RECHECK_SAVED_SOURCE"
        assert response["preview_latest_irrelevant_count"]==1
        assert response["preview_existing_case_count"]==1
        assert db.query(CaseAssignment).count()==1
    finally: db.close()

def test_removed_campaign_source_link_hides_case_id_and_both_links(monkeypatch):
    db=dataset()
    try:
        _patch(monkeypatch,[finding(posts=[post()])])
        db.add(_case(11));db.commit()
        db.query(CampaignEvidence).filter_by(campaign_id=90,result_id=11).delete()
        db.commit()
        response=pilot_intake(db.get(User,1),db)
        row=response["items"][0]
        assert row["latest_saved_eligibility"]=="SOURCE_NOT_IN_AUTHORIZED_SCOPE"
        assert row["casework_link"] is None
        assert row["source_link"] is None
        assert row["visible_open_case_id"] is None
        assert row["case_already_exists_in_visible_scope"] is False
        assert response["preview_now_unavailable_count"]==1
        assert response["preview_existing_case_count"]==0
        assert db.query(CaseAssignment).count()==1
    finally: db.close()

def test_valid_saved_source_can_still_enter_officer_casework(monkeypatch):
    db=dataset()
    try:
        _patch(monkeypatch,[finding(posts=[post()])])
        response=pilot_intake(db.get(User,1),db)
        row=response["items"][0]
        assert row["latest_saved_eligibility"]=="LATEST_SAVED_ELIGIBLE"
        assert row["casework_link"].endswith("&tab=assignments")
        assert response["preview_latest_saved_eligible_count"]==1
        assert response["preview_latest_saved_recheck_count"]==len(response["items"])
        assert response["preview_latest_recheck_is_not_full_cohort"] is True
        assert response["latest_saved_eligibility_is_not_source_authenticity"] is True
        assert row["source_truth_verified"] is False
        assert db.query(CaseAssignment).count()==0
    finally: db.close()
