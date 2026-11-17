"""Owner-scoped persisted Assistant review, immutable event history, stale guard."""
import json
from datetime import datetime
from types import SimpleNamespace
import pytest
from fastapi import HTTPException,Response
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.assistant_history import AssistantThread
from app import saved_reply_reviews as reviews

@pytest.fixture
def db(monkeypatch):
 engine=create_engine("sqlite+pysqlite:///:memory:")
 Base.metadata.create_all(engine,tables=[AssistantThread.__table__,
   reviews.SavedReplyReview.__table__,reviews.SavedReplyReviewEvent.__table__])
 with Session(engine) as session:
  session.add(AssistantThread(id="11111111-1111-4111-8111-111111111111",user_id=3,title="Review",
   messages_json=json.dumps([{"role":"user","text":"Explain saved post"},
     {"role":"assistant","text":"One post [SOCIAL-7]","records":[{"id":"SOCIAL-7"}]}]),
   created_at=datetime.utcnow(),updated_at=datetime.utcnow()))
  session.commit()
  monkeypatch.setattr(reviews,"profile",lambda d,u:{"status":"Active","permissions":{
   "view_intelligence":True,"review_ai_suggestions":True}})
  yield session
 engine.dispose()

def request(state="PENDING_REVIEW",checked=False,version=0):
 return reviews.ReviewSave(thread_id="11111111-1111-4111-8111-111111111111",
  answer_message_index=1,review_state=state,evidence_checked=checked,expected_version=version)

def test_save_and_stale_version(db):
 user=SimpleNamespace(id=3)
 a=reviews.save_review(request(),Response(),user,db)
 assert a["record"]["version"]==1
 assert reviews.list_reviews(Response(),user,db)["records"][0]["review_state"]=="PENDING_REVIEW"
 with pytest.raises(HTTPException) as err:reviews.save_review(request(),Response(),user,db)
 assert err.value.status_code==409
 assert db.query(reviews.SavedReplyReviewEvent).count()==1

def test_owned_and_permission_gate(db,monkeypatch):
 with pytest.raises(HTTPException) as err:
  reviews.save_review(request(),Response(),SimpleNamespace(id=4),db)
 assert err.value.status_code==404
 monkeypatch.setattr(reviews,"profile",lambda d,u:{"status":"Active","permissions":{
  "view_intelligence":True,"review_ai_suggestions":False}})
 with pytest.raises(HTTPException) as err:
  reviews.list_reviews(Response(),SimpleNamespace(id=3),db)
 assert err.value.status_code==403

def test_changed_saved_answer_blocks_update(db):
 user=SimpleNamespace(id=3)
 reviews.save_review(request(),Response(),user,db)
 row=db.query(AssistantThread).first()
 row.messages_json=row.messages_json.replace("One post","Different post")
 db.commit()
 with pytest.raises(HTTPException) as err:
  reviews.save_review(request(version=1),Response(),user,db)
 assert err.value.status_code==409
 assert reviews.list_reviews(Response(),user,db)["records"][0]["saved_reply_changed"] is True

def test_terminal_requires_actual_source_reauthorization(db,monkeypatch):
 user=SimpleNamespace(id=3)
 with pytest.raises(HTTPException) as err:
  reviews.save_review(request("EVIDENCE_CHECKED_FOLLOWUP_NEEDED",False),Response(),user,db)
 assert err.value.status_code==422
 def unavailable(*args):raise HTTPException(404,"Evidence access missing")
 monkeypatch.setattr(reviews,"resolve_mixed_audit_sources",unavailable)
 with pytest.raises(HTTPException) as err:
  reviews.save_review(request("EVIDENCE_CHECKED_FOLLOWUP_NEEDED",True),Response(),user,db)
 assert err.value.status_code==404
 assert db.query(reviews.SavedReplyReview).count()==0
