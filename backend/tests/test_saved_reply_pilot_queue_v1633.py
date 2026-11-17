"""Owned pilot inventory is bounded, status-aware, and non-verdict."""
from types import SimpleNamespace
import pytest
from fastapi import HTTPException,Response
from app import saved_reply_reviews as review
from test_saved_reply_persistent_v1630 import db,request

def test_eligible_unsaved_queue_and_owner_boundary(db):
 u=SimpleNamespace(id=3)
 result=review.pilot_queue(Response(),u,db)
 assert result["candidate_count"]==1
 assert result["eligible_count"]==1
 assert result["pilot_state_counts"]=={"NOT_STARTED":1}
 assert result["recommended_next_batch_count"]==1
 assert result["source_permission_rechecked_at_listing"] is False
 assert result["human_accuracy"] is None and result["database_writes"]==0
 other=review.pilot_queue(Response(),SimpleNamespace(id=4),db)
 assert other["candidate_count"]==0

def test_recorded_and_stale_queue_classification(db):
 u=SimpleNamespace(id=3)
 review.save_review(request(),Response(),u,db)
 recorded=review.pilot_queue(Response(),u,db)
 assert recorded["pilot_state_counts"]=={"PENDING_REVIEW":1}
 original=db.query(review.AssistantThread).first()
 original.messages_json=original.messages_json.replace("One post","Changed post")
 db.commit()
 stale=review.pilot_queue(Response(),u,db)
 assert stale["pilot_state_counts"]=={"RECHECK_SAVED_REPLY":1}
 assert stale["candidates"][0]["evidence_checked_current"] is False

def test_ineligible_candidate_and_permission_denial(db,monkeypatch):
 u=SimpleNamespace(id=3)
 original=db.query(review.AssistantThread).first()
 original.messages_json=original.messages_json.replace("One post [SOCIAL-7]","hi")
 db.commit()
 result=review.pilot_queue(Response(),u,db)
 assert result["pilot_state_counts"]=={"INELIGIBLE_FOR_AUDIT":1}
 assert result["recommended_next_batch_count"]==0
 monkeypatch.setattr(review,"profile",lambda *args:{"status":"Active","permissions":{
  "view_intelligence":True,"review_ai_suggestions":False}})
 with pytest.raises(HTTPException) as exc:
  review.pilot_queue(Response(),u,db)
 assert exc.value.status_code==403

def test_queue_never_changes_review_records(db):
 u=SimpleNamespace(id=3)
 review.save_review(request(),Response(),u,db)
 before=db.query(review.SavedReplyReviewEvent).count()
 response=review.pilot_queue(Response(),u,db)
 assert response["database_writes"]==0
 assert db.query(review.SavedReplyReviewEvent).count()==before
