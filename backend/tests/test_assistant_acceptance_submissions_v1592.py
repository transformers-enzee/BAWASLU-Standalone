"""v159.2 permission, isolation, append-only review and no false approval."""
import pytest
from fastapi import HTTPException,Response
from app import assistant_acceptance_submissions as sub
from app.models import User,AssistantAcceptanceEvidence,AssistantAcceptanceEvidenceEvent
from test_management_briefings_v1468 import dataset

def patch_profile(monkeypatch,role="National Administrator",scope="Nationwide",
                  active=True,administration=True):
    monkeypatch.setattr(sub,"profile",lambda db,user:{
        "role":role,"geographic_scope":scope,"status":"Active" if active else "Inactive",
        "permissions":{"administration":administration,"view_intelligence":True}})

def test_submission_and_independent_review_are_audited(monkeypatch):
    db=dataset()
    try:
        patch_profile(monkeypatch)
        a=sub.submit_evidence(sub.EvidenceSubmit(
            track="LEGAL_REFERENCE_SIGNOFF",reference="document:legal-2026-v1"),
            Response(),db.get(User,1),db)
        assert a["status"]=="SUBMITTED_UNVERIFIED"
        assert a["legal_signoff"] is False and a["client_acceptance"] is False
        assert [x["action"] for x in a["history"]]==["SUBMITTED"]
        with pytest.raises(HTTPException) as e:
            sub.review_evidence(a["id"],sub.EvidenceReview(action="EVIDENCE_REVIEWED"),
                                Response(),db.get(User,1),db)
        assert e.value.status_code==409
        b=sub.review_evidence(a["id"],sub.EvidenceReview(action="EVIDENCE_REVIEWED"),
                               Response(),db.get(User,2),db)
        assert b["status"]=="REVIEWED"
        assert [x["action"] for x in b["history"]]==["SUBMITTED","EVIDENCE_REVIEWED"]
        assert b["legal_signoff"] is False
        with pytest.raises(HTTPException) as e:
            sub.review_evidence(a["id"],sub.EvidenceReview(action="REVISION_REQUESTED"),
                                Response(),db.get(User,3),db)
        assert e.value.status_code==409
        listing=sub.list_evidence(Response(),db.get(User,1),db)
        assert listing["status_counts"]["REVIEWED"]==1
        assert not listing["formal_client_acceptance_verified"]
        assert db.query(AssistantAcceptanceEvidenceEvent).count()==2
    finally:db.close()

def test_negative_review_and_new_revision_is_separate_submission(monkeypatch):
    db=dataset()
    try:
        patch_profile(monkeypatch)
        a=sub.submit_evidence(sub.EvidenceSubmit(
            track="SOURCE_LINKED_AI_REVIEW",reference="qa:batch-review-001"),Response(),
            db.get(User,1),db)
        b=sub.review_evidence(a["id"],sub.EvidenceReview(
            action="REVISION_REQUESTED"),Response(),db.get(User,2),db)
        assert b["status"]=="REVISION_REQUESTED"
        c=sub.submit_evidence(sub.EvidenceSubmit(
            track="SOURCE_LINKED_AI_REVIEW",reference="qa:batch-review-002"),Response(),
            db.get(User,1),db)
        assert c["id"]!=a["id"]
        assert db.query(AssistantAcceptanceEvidence).count()==2
    finally:db.close()

@pytest.mark.parametrize("role,scope,active,administration",[
    ("Viewer","Nationwide",True,False),
    ("Provincial Administrator","Province",True,True),
    ("National Administrator","Province",True,True),
    ("National Administrator","Nationwide",False,True),
    ("National Administrator","Nationwide",True,False),
])
def test_non_admin_or_inactive_denied(monkeypatch,role,scope,active,administration):
    db=dataset()
    try:
        patch_profile(monkeypatch,role,scope,active,administration)
        with pytest.raises(HTTPException) as e:
            sub.submit_evidence(sub.EvidenceSubmit(
                track="FORMAL_CLIENT_ACCEPTANCE",reference="client:external-001"),
                Response(),db.get(User,1),db)
        assert e.value.status_code==403
        assert db.query(AssistantAcceptanceEvidence).count()==0
    finally:db.close()

@pytest.mark.parametrize("track,ref",[
    ("UNKNOWN","review:identifier-001"),
    ("FORMAL_CLIENT_ACCEPTANCE","https://example.invalid/file"),
    ("FORMAL_CLIENT_ACCEPTANCE","../file-name"),
    ("FORMAL_CLIENT_ACCEPTANCE","=HYPERLINK(1)"),
])
def test_untrusted_evidence_reference_rejected(monkeypatch,track,ref):
    db=dataset()
    try:
        patch_profile(monkeypatch)
        with pytest.raises((HTTPException,ValueError)):
            sub.submit_evidence(sub.EvidenceSubmit(track=track,reference=ref),
                                Response(),db.get(User,1),db)
        assert db.query(AssistantAcceptanceEvidence).count()==0
    finally:db.close()
