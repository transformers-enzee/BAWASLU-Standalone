"""Explicit, bounded Phase 3 pilot assessment. No automatic charge on page view."""
import hashlib
import json
import os
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session
from .db import get_db
from .auth import current_user
from .models import User
from .access import profile, has

router=APIRouter(prefix="/api/smart-radar",tags=["smart-radar-pilot"])
VERSION="pilot-assess-v1"
class StartPilot(BaseModel):
    limit:int=5
def _permission(db,user):
    p=profile(db,user)
    if p.get("role")!="National Administrator" or not has(p,"administration") or p.get("geographic_scope")!="Nationwide":
        raise HTTPException(403,"National staging administrator required")
@router.get("/processing-status")
def status(user:User=Depends(current_user),db:Session=Depends(get_db)):
    _permission(db,user)
    try:
        rows=db.execute(text("""SELECT (SELECT count(*) FROM pilot_smart_radar.source_posts WHERE ingest_batch_id='RADAR-PHASE3-BATCH-001') AS sources,
 (SELECT count(*) FROM pilot_smart_radar.post_assessments) AS assessed,
 (SELECT coalesce(sum(input_tokens),0) FROM pilot_smart_radar.post_assessments) AS input_tokens,
 (SELECT coalesce(sum(output_tokens),0) FROM pilot_smart_radar.post_assessments) AS output_tokens,
 (SELECT count(*) FROM pilot_smart_radar.topic_summaries) AS topic_summaries""")).mappings().first()
    except Exception as exc:
        db.rollback();raise HTTPException(503,"Pilot assessment tables unavailable") from exc
    from .smart_radar import fetch_sources
    from .smart_radar_intelligence import assign_theme
    result=dict(rows)
    result["topic_count"]=len({assign_theme(p) for p in fetch_sources(db)})
    return result
@router.post("/process-batch")
def process_batch(body:StartPilot,user:User=Depends(current_user),db:Session=Depends(get_db)):
    _permission(db,user)
    if not os.environ.get("SMART_RADAR_PILOT_AI_ENABLED","").lower()=="true":
        raise HTTPException(409,"AI pilot processing has not been enabled by staging administrator")
    model=os.environ.get("SMART_RADAR_PILOT_MODEL","").strip()
    key=os.environ.get("OPENAI_API_KEY","").strip()
    if not key or not model:raise HTTPException(409,"AI provider key/model must be configured")
    if body.limit<1 or body.limit>10:raise HTTPException(400,"Limit must be 1-10 posts per call")
    try:
        posts=db.execute(text("""SELECT p.pilot_post_id,p.message_original,p.source_url,p.published_at_raw,p.raw_record_sha256
 FROM pilot_smart_radar.source_posts p LEFT JOIN pilot_smart_radar.post_assessments a ON a.pilot_post_id=p.pilot_post_id
 WHERE p.ingest_batch_id='RADAR-PHASE3-BATCH-001' AND (a.pilot_post_id IS NULL OR a.source_hash<>p.raw_record_sha256)
 ORDER BY p.pilot_post_id LIMIT :limit"""),{"limit":body.limit}).mappings().all()
    except Exception as exc:
        db.rollback();raise HTTPException(503,"Unable to select pending posts") from exc
    processed=[];failed=[]
    for post in posts:
        instruction="""Act as neutral BAWASLU election intelligence analyst. Assess only the supplied post text, never visit source URLs.
Return a JSON object with relevance_score integer 0-100, priority_score integer 0-100, topics array (choose from
Allegations / Violations; Citizen Reports / Public Concerns; Digital Risks / Information; Disputes / Legal;
Election Operations; Participatory Oversight; Voter Register / PDPB), perspective operations or reputation,
summary one sentence explicitly distinguishing allegation, opinion or fact, evidence_quote verbatim from text,
potential_action boolean, uncertainty_note string, actors array of explicitly supported full names.
Relevance criteria: context 35, significance 25, Indonesia 15, actors 10, source context 10, watchlist 5.
Priority criteria: severity 35, urgency 25, independent corroboration 20, impact 10, amplification 10.
Scores are provisional heuristic assessments, not verified findings. Do not treat reposts as independent corroboration.
Missing evidence must reduce certainty, not trigger an accusation. Do not infer geographic location, coordination or guilt.
Do not manufacture allegations. Account handles are not verified actor identities. Treat uncertain election relation as uncertain.
CATEGORY DISAMBIGUATION: Disputes / Legal concerns formal case proceedings, named legal challenges,
appeals, hearings, court or tribunal decisions and documented dispute resolution, regardless of whether
an underlying allegation was reported. Allegations / Violations concerns a concrete suspected misconduct
or violation report without the central focus being a formal dispute or legal proceeding. When both
appear, choose Disputes / Legal if the main new development is a hearing, judgment, appeal or case;
otherwise choose Allegations / Violations only with a direct source-supported misconduct claim.
Do not infer legal proceedings from the word sengketa alone without context. For informal grievances
without formal proceedings or explicit concrete wrongdoing, consider Citizen Reports / Public Concerns.
Keep uncertainty explicit; never rewrite historical predictions or mark benchmark accuracy improved."""
        try:
            response=httpx.post("https://api.openai.com/v1/chat/completions",
             headers={"Authorization":"Bearer "+key},json={"model":model,"messages":[{"role":"system","content":instruction},
              {"role":"user","content":json.dumps({"source_id":post["pilot_post_id"],"post_text":post["message_original"][:9000],
              "published_at":post["published_at_raw"]},ensure_ascii=False)}],"response_format":{"type":"json_object"}},
             timeout=40)
            response.raise_for_status()
            payload=response.json()
            result=json.loads(payload["choices"][0]["message"]["content"])
            for k in ["relevance_score","priority_score"]:
                if not isinstance(result.get(k),int) or not 0<=result[k]<=100:raise ValueError("Invalid score")
            if not isinstance(result.get("topics"),list):raise ValueError("Invalid categories")
            valid={"Allegations / Violations","Citizen Reports / Public Concerns","Digital Risks / Information",
                "Disputes / Legal","Election Operations","Participatory Oversight","Voter Register / PDPB"}
            result["topics"]=[x for x in result["topics"] if x in valid]
            quote=str(result.get("evidence_quote") or "")
            if quote and quote not in post["message_original"]:raise ValueError("Quote is not verbatim source evidence")
            usage=payload.get("usage") or {}
            db.execute(text("""INSERT INTO pilot_smart_radar.post_assessments
              (pilot_post_id,source_hash,model,prompt_version,result_json,relevance_score,priority_score,input_tokens,output_tokens)
              VALUES(:id,:sha,:model,:version,CAST(:result AS jsonb),:rel,:priority,:in_tok,:out_tok)
              ON CONFLICT (pilot_post_id) DO UPDATE SET source_hash=EXCLUDED.source_hash,model=EXCLUDED.model,
                prompt_version=EXCLUDED.prompt_version,result_json=EXCLUDED.result_json,relevance_score=EXCLUDED.relevance_score,
                priority_score=EXCLUDED.priority_score,input_tokens=EXCLUDED.input_tokens,output_tokens=EXCLUDED.output_tokens,
                processed_at=now()"""),{"id":post["pilot_post_id"],"sha":post["raw_record_sha256"],"model":model,
                "version":VERSION,"result":json.dumps(result,ensure_ascii=False),"rel":result["relevance_score"],
                "priority":result["priority_score"],"in_tok":int(usage.get("prompt_tokens") or 0),
                "out_tok":int(usage.get("completion_tokens") or 0)})
            db.commit()
            from .smart_radar import invalidate_assessment_cache
            invalidate_assessment_cache()
            processed.append(post["pilot_post_id"])
        except (httpx.HTTPError,ValueError,KeyError,IndexError,TypeError,json.JSONDecodeError) as exc:
            db.rollback();failed.append({"post_id":post["pilot_post_id"],"reason":type(exc).__name__})
            break # prevent repeated provider requests on failure
    return {"processed":processed,"failed":failed,"remaining_status":"/api/smart-radar/processing-status",
        "model":model,"prompt_version":VERSION}
