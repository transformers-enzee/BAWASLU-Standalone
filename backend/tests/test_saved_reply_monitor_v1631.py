"""Owner-scoped review monitoring, transition integrity, stale completion."""
from types import SimpleNamespace
import pytest
from fastapi import HTTPException,Response
from app import saved_reply_reviews as review
from test_saved_reply_persistent_v1630 import db,request

def test_three_transitions_keep_exact_prior_state(db):
 user=SimpleNamespace(id=3)
 for version,state in [(0,"PENDING_REVIEW"),(1,"EVIDENCE_CHECK_IN_PROGRESS"),(2,"REVIEW_BLOCKED")]:
  saved=review.save_review(request(state,False,version),Response(),user,db)
  assert saved["record"]["version"]==version+1
 timeline=review.history(request().thread_id,1,Response(),user,db)
 assert [(e["from_state"],e["to_state"],e["version"]) for e in timeline["events"]]==[
  ("NOT_RECORDED","PENDING_REVIEW",1),
  ("PENDING_REVIEW","EVIDENCE_CHECK_IN_PROGRESS",2),
  ("EVIDENCE_CHECK_IN_PROGRESS","REVIEW_BLOCKED",3)]
 overview=review.list_reviews(Response(),user,db)
 assert overview["review_progress_counts"]=={"REVIEW_BLOCKED":1}
 assert overview["completed_current_count"]==0 and overview["stale_review_count"]==0
 with pytest.raises(HTTPException) as e:review.save_review(request(version=2),Response(),user,db)
 assert e.value.status_code==409
 assert db.query(review.SavedReplyReviewEvent).count()==3

def test_changed_reply_invalidates_effective_completion(db,monkeypatch):
 user=SimpleNamespace(id=3)
 monkeypatch.setattr(review,"resolve_mixed_audit_sources",lambda *args:[
  {"record_id":"SOCIAL-7","record_type":"SOCIAL_LISTENING","source_excerpt":"Test source"}])
 review.save_review(request("EVIDENCE_CHECKED_NO_FURTHER_ACTION",True,0),Response(),user,db)
 before=review.list_reviews(Response(),user,db)
 assert before["completed_current_count"]==1
 original=db.query(review.AssistantThread).first()
 original.messages_json=original.messages_json.replace("One post","Changed post")
 db.commit()
 after=review.list_reviews(Response(),user,db)
 assert after["review_progress_counts"]=={"RECHECK_SAVED_REPLY":1}
 assert after["stale_review_count"]==1 and after["completed_current_count"]==0
 assert after["records"][0]["evidence_check_current"] is False
 recorded=review.history(request().thread_id,1,Response(),user,db)
 assert recorded["record"]["effective_review_state"]=="RECHECK_SAVED_REPLY"

def test_owner_and_permissions_hold_for_summary(db,monkeypatch):
 user=SimpleNamespace(id=3)
 review.save_review(request(),Response(),user,db)
 assert review.list_reviews(Response(),SimpleNamespace(id=4),db)["review_count"]==0
 monkeypatch.setattr(review,"profile",lambda *args:{"status":"Active","permissions":{"view_intelligence":True,"review_ai_suggestions":False}})
 with pytest.raises(HTTPException) as e:review.list_reviews(Response(),user,db)
 assert e.value.status_code==403
