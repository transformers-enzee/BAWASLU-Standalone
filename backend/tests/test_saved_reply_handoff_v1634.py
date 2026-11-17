"""Owner-only, bounded, sanitized pilot handoff with no inferred verdict."""
from types import SimpleNamespace
import pytest
from fastapi import HTTPException,Response
from app import saved_reply_reviews as review
from test_saved_reply_persistent_v1630 import db,request

def test_handoff_unsaved_and_owner_boundary(db):
 u=SimpleNamespace(id=3)
 result=review.pilot_handoff(Response(),u,db)
 assert result["schema"]=="BAWASLU_OWNED_PILOT_HANDOFF_V1634"
 assert result["handoff_bucket_counts"]=={"AWAITING_REVIEW":1}
 assert result["inventory_count"]==1
 assert result["rows"][0]["review_version"]==0
 assert result["rows"][0]["reviewer_id"] is None
 assert result["bounded_inventory_not_all_historical_replies"] is True
 assert result["source_authorization_at_export"] is False
 assert result["answer_text_included"] is False
 assert result["source_excerpts_included"] is False
 assert result["human_accuracy"] is None
 assert result["database_writes"]==0
 assert review.pilot_handoff(Response(),SimpleNamespace(id=4),db)["rows"]==[]

def test_followup_and_stale_never_count_as_no_action(db,monkeypatch):
 u=SimpleNamespace(id=3)
 monkeypatch.setattr(review,"resolve_mixed_audit_sources",lambda *args:[
  {"record_id":"SOCIAL-7","record_type":"SOCIAL_LISTENING","source_excerpt":"Test"}])
 review.save_review(request("EVIDENCE_CHECKED_FOLLOWUP_NEEDED",True,0),Response(),u,db)
 result=review.pilot_handoff(Response(),u,db)
 assert result["followup_required_count"]==1
 assert result["evidence_checked_no_action_count"]==0
 assert result["rows"][0]["reviewer_id"]==3
 thread=db.query(review.AssistantThread).first()
 thread.messages_json=thread.messages_json.replace("One post","Updated post")
 db.commit()
 stale=review.pilot_handoff(Response(),u,db)
 assert stale["followup_required_count"]==0
 assert stale["blocked_or_recheck_count"]==1
 assert stale["rows"][0]["handoff_bucket"]=="STALE_RECHECK_REQUIRED"
 assert stale["rows"][0]["evidence_checked_current"] is False

def test_ineligible_handoff_and_access_control(db,monkeypatch):
 u=SimpleNamespace(id=3)
 thread=db.query(review.AssistantThread).first()
 thread.messages_json=thread.messages_json.replace("One post [SOCIAL-7]","hi")
 db.commit()
 result=review.pilot_handoff(Response(),u,db)
 assert result["handoff_bucket_counts"]=={"INELIGIBLE":1}
 assert result["rows"][0]["eligible"] is False
 monkeypatch.setattr(review,"profile",lambda *args:{"status":"Active","permissions":{
  "view_intelligence":True,"review_ai_suggestions":False}})
 with pytest.raises(HTTPException) as exc:
  review.pilot_handoff(Response(),u,db)
 assert exc.value.status_code==403

def test_handoff_does_not_mutate_review_events(db):
 u=SimpleNamespace(id=3)
 review.save_review(request(),Response(),u,db)
 before=db.query(review.SavedReplyReviewEvent).count()
 result=review.pilot_handoff(Response(),u,db)
 assert result["database_writes"]==0
 assert db.query(review.SavedReplyReviewEvent).count()==before
