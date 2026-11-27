"""v185.7: full read-only Gate 1 queue regression and isolation guards."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException
from app import inbox_human_gate as gate
from app import inbox_human_queue as queue


def test_validation_and_empty_page(monkeypatch):
    with pytest.raises(HTTPException) as error:
        queue.paginated_review_queue(None, None, 1, page_size=101)
    assert error.value.status_code == 422
    for category in ("bad", "UNKNOWN"):
        with pytest.raises(HTTPException):
            queue.paginated_review_queue(None, None, 1, category=category)
    with pytest.raises(HTTPException):
        queue.paginated_review_queue(None, None, 1, cursor=0)
    db=MagicMock()
    db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value=[]
    response=queue.paginated_review_queue(db, {"geographic_scope":"Nationwide"}, 12)
    assert response["items"] == []
    assert response["has_more"] is False
    assert response["not_population_totals"]
    db.commit.assert_not_called()


def test_api_enforces_read_flag_and_campaign_scope(monkeypatch):
    monkeypatch.delenv("BAWASLU_INBOX_GATE1_READ_ENABLED",raising=False)
    with pytest.raises(HTTPException) as err:
        gate.review_queue(10,user=SimpleNamespace(id=1),db=MagicMock())
    assert err.value.status_code==503
    monkeypatch.setenv("BAWASLU_INBOX_GATE1_READ_ENABLED","true")
    monkeypatch.setattr(gate,"_grant",lambda db,user,p:{"id":"officer"})
    def deny(db,officer,campaign):raise HTTPException(404,"Campaign unavailable")
    monkeypatch.setattr(gate,"_campaign",deny)
    with pytest.raises(HTTPException) as err:
        gate.review_queue(10,user=SimpleNamespace(id=1),db=MagicMock())
    assert err.value.status_code==404


def test_category_filter_keeps_cursor_after_scanned_links(monkeypatch):
    links=[SimpleNamespace(id=i,result_id=i) for i in range(6,0,-1)]
    class Query:
        def __init__(self,db):self.db=db;self.upper=None;self.quantity=200
        def filter(self,*filters):return self
        def order_by(self,*a):return self
        def limit(self,n):self.quantity=n;return self
        def all(self):
            # Deliberately exercise the pagination algorithm without relying
            # on SQLAlchemy mocks for SQL expression interpretation.
            return [row for row in links if self.db.maxid is None or row.id<self.db.maxid][:self.quantity]
        def first(self):return (1,) if self.db.more else None
    class DB:
        def __init__(self):self.maxid=None;self.more=True
        def query(self,*a):return Query(self)
    db=DB()
    def classify(db,officer,campaign,rows):
        return {row.result_id:{"result_id":str(row.result_id),"category":"relevant" if row.id%2 else "unassessed","action":"CHECK_RELEVANT_EVIDENCE" if row.id%2 else "VERIFY_UNASSESSED"} for row in rows}
    monkeypatch.setattr(queue,"_classified_batch",classify)
    # Capture the cursor predicate using a small deterministic fake query:
    from app.models import CampaignEvidence
    monkeypatch.setattr(queue,"FETCH_BATCH",3)
    # Validate result categories, cursor shape and duplicate-free pages using
    # a single mocked page (the next-page query is separately validated in SQL).
    page=queue.paginated_review_queue(db,{},10,page_size=2,category="unassessed")
    assert [r["result_id"] for r in page["items"]]==["6","4"]
    assert page["next_cursor"]=="4"
    assert page["has_more"]


def test_security_and_no_side_effects_contract():
    from inspect import getsource
    s=getsource(queue.paginated_review_queue)
    batch=getsource(queue._classified_batch)
    route=getsource(gate.review_queue)
    assert "CampaignEvidence.match_method != \"WATCHLIST_ACCOUNT\"" in s
    assert "_result_in_scope(db, officer, sources[sid])" in batch
    assert '_grant(db,user,"view_intelligence")' in route
    assert "_campaign(db,officer,campaign_id)" in route
    assert "db.commit(" not in s+batch+route
    assert "MAX_SCAN_PER_REQUEST" in s
    assert "paid_provider_called" in s


def test_frontend_has_pagination_filters_and_keeps_existing_audit_route():
    root=Path(__file__).resolve().parents[2]
    ui=(root/"frontend/src/components/intel/InboxHumanReview.jsx").read_text()
    client=(root/"frontend/src/api/base44Client.js").read_text()
    for fragment in ("gate1-load-more","gate1-category-filter","base44.inboxHumanReview.queue","campaignAssessmentCorrection","detail.can_correct_relevance","originalLink(detail.canonical_url)"):
        assert fragment in ui
    assert "/queue?" in client
    assert "new URLSearchParams" in client
