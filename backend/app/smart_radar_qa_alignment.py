"""Analyst adjudication queue for ambiguous Shahrin reference labels.

Original Excel values never change. An authenticated QA reviewer must give a
written rationale for confirmation, correction, or deferral. Decisions and
revisions are audit logged, separate from BAWASLU officer Action Desk.
"""
from collections import Counter
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from sqlalchemy import text
from sqlalchemy.orm import Session
from .auth import current_user
from .db import get_db
from .models import User
from .smart_radar_qa import reviewer,CAT_SET

router=APIRouter(prefix="/api/smart-radar/qa",tags=["smart-radar-analyst-alignment"])
PRIORITY_CASES={"QA-10649":"AI-human disagreement: criticism classified as routine operations",
                "QA-11375":"AI-human disagreement: proceedings versus allegation",
                "QA-22450":"Voter-list label lacks clear voter-list subject",
                "QA-73905":"Digital-risk label lacks clear digital subject"}
SOURCE_RELATIONS={"not_applicable","distinct_comments","same_underlying_content","unresolved"}
DECISIONS={"confirmed","corrected","needs_context"}

def queue_data(db):
    rows=db.execute(text("""
      WITH duplicate_urls AS (
        SELECT h.source_url,count(*)::int AS source_rows,
               count(DISTINCT h.category)::int AS category_count
        FROM pilot_smart_radar.qa_imported_human_categories h
        GROUP BY h.source_url HAVING count(*)>1
      )
      SELECT p.qa_id,p.message_original,p.source_url,p.platform,
             p.original_excel_row,p.curated_category,
             h.category AS uploaded_category,h.review_status,
             d.source_rows,d.category_count,
             latest.predicted_category AS latest_ai_category,
             r.decision,r.approved_category,r.reasoning,r.source_relation,
             r.reviewer_name,r.reviewed_at
      FROM pilot_smart_radar.qa_source_posts p
      JOIN pilot_smart_radar.qa_imported_human_categories h
        ON h.original_excel_row=p.original_excel_row AND h.source_url=p.source_url
      LEFT JOIN duplicate_urls d ON d.source_url=h.source_url
      LEFT JOIN pilot_smart_radar.qa_alignment_decisions r ON r.qa_id=p.qa_id
      LEFT JOIN LATERAL (
         SELECT a.result_json->>'primary_category' AS predicted_category
         FROM pilot_smart_radar.qa_ai_assessments a
         WHERE a.qa_id=p.qa_id AND a.prompt_version LIKE 'qa-prompt-tune-v%'
         ORDER BY a.processed_at DESC LIMIT 1
      ) latest ON TRUE
      WHERE p.qa_id IN ('QA-10649','QA-11375','QA-22450','QA-73905')
         OR d.source_rows>1
         OR (latest.predicted_category IS NOT NULL AND
             latest.predicted_category<>COALESCE(r.approved_category,h.category))
      ORDER BY CASE WHEN p.qa_id IN ('QA-10649','QA-11375') THEN 0 ELSE 1 END,p.qa_id
    """)).mappings().all()
    return [dict(r) for r in rows]

def blocked_references(db):
    """Exclude ambiguous references from NEW tuning tests without deleting them."""
    return blocked_references_from_rows(queue_data(db))

class AnalystDecision(BaseModel):
    qa_id:str=Field(min_length=3,max_length=50)
    decision:str
    approved_category:str|None=None
    rationale:str=Field(min_length=30,max_length=3000)
    source_relation:str="not_applicable"

@router.get("/alignment")
def alignment_queue(user:User=Depends(current_user),db:Session=Depends(get_db)):
    reviewer(db,user)
    rows=queue_data(db)
    blocked=blocked_references_from_rows(rows)
    items=[]
    for row in rows:
        item={k:v for k,v in row.items()}
        item["reviewed_at"]=row["reviewed_at"].isoformat() if row["reviewed_at"] else None
        item["source_conflict"]=bool(row["source_rows"])
        item["reason_for_queue"]=PRIORITY_CASES.get(row["qa_id"],
               "Repeated source URL; confirm distinct comments and primary category" if row["source_rows"]
               else "AI disagrees with provisional human category; analyst explanation needed")
        item["training_blocked_reason"]=blocked.get(row["qa_id"])
        items.append(item)
    return {"items":items,"pending":len(blocked),"total":len(items),
            "note":"The uploaded Excel labels are preserved. Only a logged-in reviewer can confirm or correct them with written reasoning."}

def blocked_references_from_rows(rows):
    blocked={}
    urls={}
    for row in rows:
        if row["source_rows"]:
            urls.setdefault(row["source_url"],[]).append(row)
        if row["decision"] not in ("confirmed","corrected"):
            blocked[row["qa_id"]]="Human category requires analyst sign-off"
        elif row["source_rows"] and row["source_relation"]!="distinct_comments":
            blocked[row["qa_id"]]="Repeated URL not resolved as distinct comments"
    # A shared URL becomes eligible only once every associated record has
    # a confirmed category and is separately identified as distinct content.
    for url,items in urls.items():
        if any(x["decision"] not in ("confirmed","corrected") or
               x["source_relation"]!="distinct_comments" for x in items):
            for row in items:
                blocked[row["qa_id"]]="Shared URL group needs full analyst reconciliation"
    return blocked

@router.post("/alignment/decision")
def save_alignment_decision(body:AnalystDecision,user:User=Depends(current_user),
                            db:Session=Depends(get_db)):
    actor=reviewer(db,user)
    if body.decision not in DECISIONS:raise HTTPException(422,"Invalid decision")
    if body.source_relation not in SOURCE_RELATIONS:raise HTTPException(422,"Invalid source relation")
    source=db.execute(text("""
      SELECT p.qa_id,p.source_url,h.category,
        (SELECT count(*) FROM pilot_smart_radar.qa_imported_human_categories
           h2 WHERE h2.source_url=p.source_url) AS source_rows
      FROM pilot_smart_radar.qa_source_posts p
      JOIN pilot_smart_radar.qa_imported_human_categories h
        ON h.original_excel_row=p.original_excel_row AND h.source_url=p.source_url
      WHERE p.qa_id=:id
    """),{"id":body.qa_id}).mappings().first()
    if not source:raise HTTPException(404,"QA source record not found")
    eligible={r["qa_id"] for r in queue_data(db)}
    if body.qa_id not in eligible:raise HTTPException(422,"Record is not in the analyst-review queue")
    original=source["category"]
    category=body.approved_category
    if body.decision=="confirmed" and category!=original:
        raise HTTPException(422,"Confirm must preserve the uploaded category")
    if body.decision=="corrected" and (category not in CAT_SET or category==original):
        raise HTTPException(422,"Corrected category must be a different approved category")
    if body.decision=="needs_context" and category is not None:
        raise HTTPException(422,"Leave approved category empty when requesting context")
    if source["source_rows"]>1 and body.source_relation=="not_applicable":
        raise HTTPException(422,"For shared-source records, specify distinct comments, same underlying content, or unresolved")
    if source["source_rows"]<=1 and body.source_relation!="not_applicable":
        raise HTTPException(422,"Source relation should be not_applicable for unique URLs")
    if body.decision=="needs_context" and body.source_relation=="distinct_comments":
        raise HTTPException(422,"Cannot confirm distinct comments while deferring source identity")
    params={"id":body.qa_id,"original":original,"approved":category,
      "decision":body.decision,"reason":body.rationale.strip(),
      "relation":body.source_relation,"actor":str(user.id),"name":actor["name"]}
    db.execute(text("""
      INSERT INTO pilot_smart_radar.qa_alignment_decisions
      (qa_id,original_human_category,approved_category,decision,reasoning,
       source_relation,reviewed_by,reviewer_name)
      VALUES(:id,:original,:approved,:decision,:reason,:relation,:actor,:name)
      ON CONFLICT(qa_id) DO UPDATE SET
        approved_category=EXCLUDED.approved_category,
        decision=EXCLUDED.decision,reasoning=EXCLUDED.reasoning,
        source_relation=EXCLUDED.source_relation,
        reviewed_by=EXCLUDED.reviewed_by,reviewer_name=EXCLUDED.reviewer_name,
        reviewed_at=now()
    """),params)
    db.execute(text("""
      INSERT INTO pilot_smart_radar.qa_alignment_history
      (qa_id,original_human_category,approved_category,decision,reasoning,
       source_relation,reviewed_by,reviewer_name)
      VALUES(:id,:original,:approved,:decision,:reason,:relation,:actor,:name)
    """),params)
    db.commit()
    return {"saved":True,"qa_id":body.qa_id,
      "message":"Analyst QA decision saved with audit history; original Excel label unchanged; no Smart Radar officer task created"}
