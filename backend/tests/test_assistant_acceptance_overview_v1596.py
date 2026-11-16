"""Read-only coverage is a bounded preview, never proof of formal approval."""
import pytest
from fastapi import Response
from sqlalchemy import event as sqla_event
from app import assistant_acceptance_submissions as sub
from app.models import User,AssistantAcceptanceEvidence,AssistantAcceptanceEvidenceEvent
from test_management_briefings_v1468 import dataset
from test_assistant_acceptance_submissions_v1592 import patch_profile

def test_empty_coverage_is_explicitly_not_accepted(monkeypatch):
    db=dataset()
    try:
        patch_profile(monkeypatch)
        r=sub.list_evidence(Response(),db.get(User,1),db)
        assert r["counts_scope"]=="MOST_RECENT_100_SUBMISSIONS_ONLY"
        assert r["historical_records_may_be_excluded"] is False
        assert len(r["track_progress"])==6
        assert r["external_acceptance_tracks_pending"] is True
        assert not r["formal_client_acceptance_verified"]
        assert all(not x["has_formal_approval"] for x in r["track_progress"].values())
    finally:db.close()

def test_batched_listing_preserves_review_history_and_bounds_queries(monkeypatch):
    db=dataset()
    try:
        patch_profile(monkeypatch)
        for i in range(30):
            a=sub.submit_evidence(sub.EvidenceSubmit(
                track="SOURCE_LINKED_AI_REVIEW",reference=f"qa:sample-{i:04d}"),
                Response(),db.get(User,1),db)
            if i%3==0:
                sub.review_evidence(a["id"],sub.EvidenceReview(action="EVIDENCE_REVIEWED"),
                                   Response(),db.get(User,2),db)
            if i%3==1:
                sub.review_evidence(a["id"],sub.EvidenceReview(action="REVISION_REQUESTED"),
                                   Response(),db.get(User,2),db)
        counts=[]
        def before(conn,cursor,statement,parameters,context,executemany):
            if statement.strip().lower().startswith("select"):counts.append(statement)
        sqla_event.listen(db.bind,"before_cursor_execute",before)
        try:
            data=sub.list_evidence(Response(),db.get(User,1),db)
        finally:sqla_event.remove(db.bind,"before_cursor_execute",before)
        assert len(data["entries"])==30
        assert data["status_counts"]=={
            "SUBMITTED_UNVERIFIED":10,"REVIEWED":10,"REVISION_REQUESTED":10}
        assert len(counts)<=4,counts
        assert all(row["history"][0]["action"]=="SUBMITTED" for row in data["entries"])
        assert data["track_progress"]["SOURCE_LINKED_AI_REVIEW"]["evidence_reviewed_not_formally_approved"]==10
        assert not data["formal_legal_signoff_verified"]
    finally:db.close()

def test_101st_submission_triggers_sample_limit_disclosure(monkeypatch):
    db=dataset()
    try:
        patch_profile(monkeypatch)
        for i in range(101):
            db.add(AssistantAcceptanceEvidence(
                track="FORMAL_CLIENT_ACCEPTANCE",reference=f"client:sample-{i:04d}",submitted_by=1))
        db.commit()
        rows=db.query(AssistantAcceptanceEvidence).all()
        db.add_all([AssistantAcceptanceEvidenceEvent(evidence_id=e.id,actor_id=1,action="SUBMITTED")
                    for e in rows]);db.commit()
        result=sub.list_evidence(Response(),db.get(User,1),db)
        assert result["historical_records_may_be_excluded"] is True
        assert len(result["entries"])==100
        assert result["track_progress"]["FORMAL_CLIENT_ACCEPTANCE"]["visible_submissions"]==100
        assert result["formal_client_acceptance_verified"] is False
    finally:db.close()
