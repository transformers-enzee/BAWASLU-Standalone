"""v155.9: Unsigned pilot worksheet never creates/approves real cases."""
from app.casework import pilot_intake, CaseAssignment, CaseTransition
from app.models import User, CampaignEvidence, EvidenceAssessment
from test_casework_workflow import dataset
from test_officer_pilot_intake_v1544 import finding, post, _patch
from test_officer_pilot_active_case_lookup_v1547 import _case
from app.officer_pilot_readiness import _STAGES

def _run(monkeypatch,db):
    _patch(monkeypatch,[finding(posts=[post()])])
    return pilot_intake(db.get(User,1),db)

def test_unsigned_five_stage_checklist_uses_existing_casework_taxonomy(monkeypatch):
    db=dataset()
    try:
        result=_run(monkeypatch,db)
        item=result["items"][0]
        checklist=item["acceptance_workflow_checklist"]
        assert tuple(stage["key"] for stage in checklist)==_STAGES
        assert len(checklist)==result["acceptance_checklist_stage_count"]==5
        assert all(stage["completed"] is False for stage in checklist)
        assert all(stage["status"]=="REQUIRES_AUTHORIZED_CASEWORK_VERIFICATION" for stage in checklist)
        assert item["acceptance_saved_source_reference"]=={
            "source_type":"SOCIAL","source_id":"11","campaign_id":"90","visible_case_id":None}
        assert result["acceptance_checklist_is_unsigned"] is True
        assert result["acceptance_checklist_is_preparatory"] is True
        assert db.query(CaseAssignment).count()==0
        assert db.query(CaseTransition).count()==0
    finally: db.close()

def test_visible_case_id_is_reference_not_certification(monkeypatch):
    db=dataset()
    try:
        db.add(_case(11));db.commit()
        result=_run(monkeypatch,db)
        item=result["items"][0]
        assert item["acceptance_saved_source_reference"]["visible_case_id"]==1
        assert item["pilot_next_action"]=="CONTINUE_EXISTING_CASE"
        assert item["acceptance_workflow_stages_not_observed_here"] is True
        assert item["acceptance_requires_real_officer_review"] is True
        assert item["acceptance_source_authenticity_unverified"] is True
        assert item["acceptance_legal_approval_not_granted"] is True
        assert not any(x["completed"] for x in item["acceptance_workflow_checklist"])
        assert db.query(CaseTransition).count()==0
    finally: db.close()

def test_unavailable_source_reference_never_reveals_case_id(monkeypatch):
    db=dataset()
    try:
        db.add(_case(11));db.commit()
        db.query(CampaignEvidence).filter_by(campaign_id=90,result_id=11).delete()
        db.commit()
        result=_run(monkeypatch,db)
        item=result["items"][0]
        assert item["pilot_next_action"]=="SOURCE_UNAVAILABLE"
        assert item["acceptance_saved_source_reference"]["visible_case_id"] is None
        assert item["casework_link"] is None
        assert item["source_link"] is None
        assert db.query(CaseAssignment).count()==1
    finally: db.close()

def test_relevance_changed_does_not_fabricate_acceptance(monkeypatch):
    db=dataset()
    try:
        db.add(EvidenceAssessment(campaign_id=90,result_id=11,
            assessment_version=2,relevance_label="IRRELEVANT"))
        db.commit()
        item=_run(monkeypatch,db)["items"][0]
        assert item["pilot_next_action"]=="RECHECK_LATEST_ASSESSMENT"
        assert item["acceptance_legal_approval_not_granted"] is True
        assert all(not step["completed"] for step in item["acceptance_workflow_checklist"])
    finally: db.close()
