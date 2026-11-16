"""Authorized fresh-detail checks for the reviewer preflight workflow."""
import pytest
from fastapi import HTTPException,Response
from app import assistant_acceptance_submissions as sub
from app.models import User
from test_management_briefings_v1468 import dataset
from test_assistant_acceptance_submissions_v1592 import patch_profile

def test_targeted_detail_reports_stored_review_and_no_approval(monkeypatch):
    db=dataset()
    try:
        patch_profile(monkeypatch)
        record=sub.submit_evidence(sub.EvidenceSubmit(
            track="LEGAL_REFERENCE_SIGNOFF",reference="doc:legal-2026-0001"),
            Response(),db.get(User,1),db)
        response=Response()
        detail=sub.get_evidence(record["id"],response,db.get(User,2),db)
        assert detail["status"]=="SUBMITTED_UNVERIFIED"
        assert detail["submitted_by_user_id"]==1
        assert response.headers["Cache-Control"]=="private, no-store"
        reviewed=sub.review_evidence(record["id"],sub.EvidenceReview(
            action="REVISION_REQUESTED"),Response(),db.get(User,2),db)
        assert reviewed["status"]=="REVISION_REQUESTED"
        refreshed=sub.get_evidence(record["id"],Response(),db.get(User,2),db)
        assert refreshed["status"]=="REVISION_REQUESTED"
        assert len(refreshed["history"])==2
        assert refreshed["legal_signoff"] is False
        assert refreshed["client_acceptance"] is False
    finally:db.close()

@pytest.mark.parametrize("bad_id",[0,-1,999999])
def test_missing_or_invalid_detail_is_rejected(monkeypatch,bad_id):
    db=dataset()
    try:
        patch_profile(monkeypatch)
        with pytest.raises(HTTPException) as ex:
            sub.get_evidence(bad_id,Response(),db.get(User,1),db)
        assert ex.value.status_code==(422 if bad_id<=0 else 404)
    finally:db.close()

@pytest.mark.parametrize("role,scope",[
    ("Viewer","Nationwide"),
    ("National Administrator","Province"),
])
def test_detail_never_bypasses_national_admin_access(monkeypatch,role,scope):
    db=dataset()
    try:
        patch_profile(monkeypatch,role=role,scope=scope)
        with pytest.raises(HTTPException) as ex:
            sub.get_evidence(1,Response(),db.get(User,2),db)
        assert ex.value.status_code==403
    finally:db.close()
