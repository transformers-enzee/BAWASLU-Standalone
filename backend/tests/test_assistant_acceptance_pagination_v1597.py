"""Read-only keyset browsing of historical acceptance events without changing approvals."""
import pytest
from fastapi import HTTPException,Response
from sqlalchemy import event as sqla_event
from app import assistant_acceptance_submissions as sub
from app.models import User,AssistantAcceptanceEvidence,AssistantAcceptanceEvidenceEvent
from test_management_briefings_v1468 import dataset
from test_assistant_acceptance_submissions_v1592 import patch_profile

def make_records(db,n=215):
    rows=[AssistantAcceptanceEvidence(track="SOURCE_LINKED_AI_REVIEW",
        reference=f"qa:history-{i:04d}",submitted_by=1) for i in range(n)]
    db.add_all(rows);db.flush()
    db.add_all([AssistantAcceptanceEvidenceEvent(
        evidence_id=e.id,actor_id=1,action="SUBMITTED") for e in rows])
    db.commit()

def test_multiple_pages_cover_every_record_without_duplicates(monkeypatch):
    db=dataset()
    try:
        patch_profile(monkeypatch)
        make_records(db)
        all_ids=[]
        cursor=None
        for number,expected in enumerate((100,100,15)):
            response=Response()
            page=sub.list_evidence(response,db.get(User,1),db,before_id=cursor)
            ids=[e["id"] for e in page["entries"]]
            assert len(ids)==expected
            assert ids==sorted(ids,reverse=True)
            assert not set(ids).intersection(all_ids)
            all_ids.extend(ids)
            assert page["requested_before_id"]==cursor
            assert response.headers["Cache-Control"]=="private, no-store"
            assert all(e["history"][0]["action"]=="SUBMITTED" for e in page["entries"])
            assert not page["formal_client_acceptance_verified"]
            if number<2:
                assert page["more_older_records"] is True
                cursor=page["next_before_id"]
                assert cursor==ids[-1]
            else:
                assert page["more_older_records"] is False
                assert page["next_before_id"] is None
                assert page["counts_scope"]=="PAGE_OF_UP_TO_100_SUBMISSIONS_ONLY"
        assert len(set(all_ids))==215
        assert db.query(AssistantAcceptanceEvidence).count()==215
        assert db.query(AssistantAcceptanceEvidenceEvent).count()==215
    finally:db.close()

def test_pagination_keeps_query_count_bounded(monkeypatch):
    db=dataset()
    try:
        patch_profile(monkeypatch)
        make_records(db,140)
        before=[]
        def count(conn,cursor,statement,params,context,many):
            if statement.strip().lower().startswith("select"):before.append(statement)
        sqla_event.listen(db.bind,"before_cursor_execute",count)
        try:
            first=sub.list_evidence(Response(),db.get(User,1),db)
            second=sub.list_evidence(Response(),db.get(User,1),db,
                                     before_id=first["next_before_id"])
        finally:sqla_event.remove(db.bind,"before_cursor_execute",count)
        assert len(before)<=7,before
        assert len(second["entries"])==40
        assert second["track_progress"]["SOURCE_LINKED_AI_REVIEW"]["visible_submissions"]==40
    finally:db.close()

@pytest.mark.parametrize("cursor",[0,-1,"bad"])
def test_invalid_cursor_rejected(monkeypatch,cursor):
    db=dataset()
    try:
        patch_profile(monkeypatch)
        with pytest.raises(HTTPException) as e:
            sub.list_evidence(Response(),db.get(User,1),db,before_id=cursor)
        assert e.value.status_code==422
    finally:db.close()

def test_unknown_positive_cursor_returns_safe_empty_page(monkeypatch):
    db=dataset()
    try:
        patch_profile(monkeypatch)
        make_records(db,4)
        res=sub.list_evidence(Response(),db.get(User,1),db,before_id=1)
        assert res["entries"]==[]
        assert res["next_before_id"] is None
        assert not res["formal_legal_signoff_verified"]
    finally:db.close()
