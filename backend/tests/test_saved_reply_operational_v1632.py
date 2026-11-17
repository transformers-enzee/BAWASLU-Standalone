"""Bounded operational review attention, stale history and last-50 activity."""
from types import SimpleNamespace
from fastapi import Response,HTTPException
from app import saved_reply_reviews as review
from test_saved_reply_persistent_v1630 import db,request
import pytest

def test_attention_summary_and_owner_scope(db):
 user=SimpleNamespace(id=3)
 saved=review.save_review(request(),Response(),user,db)
 listing=review.list_reviews(Response(),user,db)
 assert listing["review_action_counts"]=={"CONTINUE_REVIEW":1}
 assert listing["needs_attention_count"]==1
 assert listing["last_owner_review_activity_at"] is not None
 assert review.list_reviews(Response(),SimpleNamespace(id=4),db)["review_action_counts"]=={}
 assert saved["record"]["review_action_required"]=="CONTINUE_REVIEW"

def test_stale_record_history_still_accessible(db):
 user=SimpleNamespace(id=3)
 review.save_review(request(),Response(),user,db)
 thread=db.query(review.AssistantThread).first()
 thread.messages_json="[]"
 db.commit()
 listing=review.list_reviews(Response(),user,db)
 assert listing["stale_review_count"]==1
 assert listing["review_action_counts"]=={"RECHECK_CHANGED_ANSWER":1}
 history=review.history(request().thread_id,1,Response(),user,db)
 assert history["record"]["saved_reply_changed"] is True
 assert history["events"][0]["to_state"]=="PENDING_REVIEW"
 with pytest.raises(HTTPException) as e:
  review.history(request().thread_id,1,Response(),SimpleNamespace(id=4),db)
 assert e.value.status_code==404

def test_latest_50_events_and_explicit_truncation(db):
 user=SimpleNamespace(id=3)
 review.save_review(request(),Response(),user,db)
 row=db.query(review.SavedReplyReview).one()
 for v in range(2,57):
  db.add(review.SavedReplyReviewEvent(review_id=row.id,actor_id=user.id,
    from_state="PENDING_REVIEW",to_state="PENDING_REVIEW",version=v))
 row.version=56
 db.commit()
 h=review.history(request().thread_id,1,Response(),user,db)
 assert h["events_returned"]==50
 assert h["history_window"]=="MOST_RECENT_50"
 assert h["history_truncated"] is True
 assert h["total_recorded_versions"]==56
 assert h["events"][0]["version"]==7
 assert h["events"][-1]["version"]==56
