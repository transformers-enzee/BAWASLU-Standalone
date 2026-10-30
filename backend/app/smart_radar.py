"""Smart Radar API: operational evidence comes only from saved Intelligence Inbox.

Historical pilot helpers stay for archival source lineage, not live findings.
"""
from collections import Counter, defaultdict
import json
import os
import time
import threading
from datetime import datetime, timezone
import re
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session
from .db import get_db
from .auth import current_user
from .models import User
from .access import profile, has
from .smart_radar_intelligence import build_topic_findings
from .smart_radar_geography import attach_geo_to_findings

"""AI-assisted summaries are used only after a dedicated, cached topic synthesis
    job; source-grounded editorial insight templates are used for the initial
    109-post pilot. No provider calls occur during dashboard reads."""
router = APIRouter(prefix="/api/smart-radar", tags=["smart-radar"])
BATCH = "RADAR-PHASE3-BATCH-001"
SOURCE_SQL = """SELECT pilot_post_id, platform, published_at_raw, account_raw, message_original,
source_url, original_category_hint, suggested_perspective_unverified,
suggested_topic_unverified, source_verification_status, imported_at
FROM pilot_smart_radar.source_posts WHERE ingest_batch_id=:batch
ORDER BY pilot_post_id"""

def authorised(db, user, decision=False):
    p = profile(db, user)
    if not has(p, "human_validation" if decision else "view_intelligence"):
        raise HTTPException(403, "BAWASLU permission required")
    # Inbox enforces campaign and source-level regional permissions.
    return p

# Per-instance bounded cache of static pilot data only, never officer decisions.
# Authorization and jurisdiction checks happen on every incoming API request.
_CACHE_LOCK=threading.RLock()
_SOURCE_CACHE={"rows":None,"expires":0.0}
_AI_CACHE={"rows":None,"expires":0.0}
_TOPIC_CACHE={"rows":None,"expires":0.0}
_GEO_CACHE={"rows":None,"expires":0.0}
def invalidate_source_cache():
    with _CACHE_LOCK:_SOURCE_CACHE.update(rows=None,expires=0.0)
def invalidate_assessment_cache():
    with _CACHE_LOCK:_AI_CACHE.update(rows=None,expires=0.0)
def invalidate_topic_cache():
    with _CACHE_LOCK:_TOPIC_CACHE.update(rows=None,expires=0.0)
def fetch_topic_summaries(db):
    ttl=max(5,min(120,int(os.getenv("SMART_RADAR_TOPIC_CACHE_SECONDS","30"))))
    with _CACHE_LOCK:
        if _TOPIC_CACHE["rows"] is not None and time.monotonic()<_TOPIC_CACHE["expires"]:
            return _TOPIC_CACHE["rows"]
        try:
            rows={x["finding_id"]:dict(x) for x in db.execute(text(
                "SELECT finding_id,source_signature,insight_json,model,prompt_version,sample_count,generated_at "
                "FROM pilot_smart_radar.topic_summaries")).mappings()}
        except Exception:
            db.rollback()
            return {}
        _TOPIC_CACHE.update(rows=rows,expires=time.monotonic()+ttl)
        return rows

def fetch_verified_incident_geography(db):
    """Only explicitly human-verified incident provinces are eligible for the heatmap.

    An account's address, a BAWASLU office, or a candidate's constituency must
    never be mistaken for the geographical location of an incident.
    """
    ttl=max(10,min(300,int(os.getenv("SMART_RADAR_GEO_CACHE_SECONDS","60"))))
    with _CACHE_LOCK:
        if _GEO_CACHE["rows"] is not None and time.monotonic()<_GEO_CACHE["expires"]:
            return _GEO_CACHE["rows"]
        try:
            pairs=list(db.execute(text("""
                SELECT pilot_post_id,province_code
                FROM pilot_smart_radar.post_geography
                WHERE location_role='incident' AND verification_status='verified'
            """)).mappings())
        except Exception:
            db.rollback()
            return {}
        result=defaultdict(set)
        for item in pairs:
            result[item["pilot_post_id"]].add(item["province_code"])
        _GEO_CACHE.update(rows=dict(result),expires=time.monotonic()+ttl)
        return _GEO_CACHE["rows"]

def fetch_sources(db):
    ttl=max(30,min(1800,int(os.getenv("SMART_RADAR_SOURCE_CACHE_SECONDS","600"))))
    with _CACHE_LOCK:
        if _SOURCE_CACHE["rows"] is not None and time.monotonic()<_SOURCE_CACHE["expires"]:
            return _SOURCE_CACHE["rows"]
        try:
            rows=[dict(x) for x in db.execute(text(SOURCE_SQL), {"batch": BATCH}).mappings()]
        except Exception as exc:
            db.rollback()
            raise HTTPException(503, "Pilot source table unavailable: check staging DATABASE_URL and import") from exc
        _SOURCE_CACHE.update(rows=rows,expires=time.monotonic()+ttl)
        return rows

def detect_topic(post):
    content = (post["message_original"] or "").lower()
    hint = (post["original_category_hint"] or "").lower()
    if re.search(r"pdpb|daftar pemilih|data pemilih|\bdpt\b|pemutakhiran", content): return "Voter Register / PDPB"
    if re.search(r"hoaks|disinformasi|misinformasi", content): return "Digital Risks / Information"
    if re.search(r"politik uang|serangan fajar|intimidasi|penggelembungan suara", content): return "Allegations / Violations"
    if re.search(r"sidang|mahkamah konstitusi|\bphpu\b|sengketa|gugatan", content): return "Disputes / Legal"
    if re.search(r"pengawasan partisipatif|partisipasi|relawan|sosialisasi", content): return "Participatory Oversight"
    if re.search(r"keluhan|aduan|pengaduan|kecewa|laporan warga", content): return "Citizen Reports / Public Concerns"
    if "election operations" in hint: return "Election Operations"
    return post.get("original_category_hint") or "Election Operations"

def perspective(post):
    c=(post["message_original"] or "").lower()
    # Institutional complaints require a stronger signal than merely mentioning BAWASLU.
    if re.search(r"bawaslu.{0,70}(pelayanan|lambat|tidak netral|netralitas|kecewa|keluhan|tak tanggap)|kecewa.{0,30}bawaslu", c):
        return "reputation"
    return "operations"

def actors(text_value):
    t = (text_value or "").lower()
    matches=[]
    for word,name in [("prabowo","Prabowo Subianto"),("gibran","Gibran Rakabuming Raka"),
                      ("anies","Anies Baswedan"),("ganjar","Ganjar Pranowo"),
                      ("mahfud","Mahfud MD"),("muhaimin","Muhaimin Iskandar")]:
        if re.search(r"\b"+word+r"\b", t): matches.append(name)
    # Account identity 'cindymonica.ig' must NOT be mapped to a person without verification.
    return matches

def grouping(post):
    t = (post["message_original"] or "").lower()
    if "gibran" in t and re.search(r"ijazah|pendidikan|pencalonan|\bphpu\b", t):
        return ("NARR-GIBRAN-COURT", "Gibran education eligibility and related court discussion", "narratives")
    if re.search(r"tunjangan kinerja|\btukin\b",t) and "bawaslu" in t:
        return ("NARR-BAWASLU-ALLOWANCE", "Discussion about BAWASLU staff allowance policy", "narratives")
    # Everything else stays a separate source-level preliminary finding.
    # Never combine distinct incidents merely because they share a topic or region.
    pid=post["pilot_post_id"]
    title=re.sub(r"\s+"," ",post["message_original"] or "").strip()[:105]
    return ("POST-"+pid,title or pid,"concerns" if detect_topic(post)=="Citizen Reports / Public Concerns" else "narratives")

def fetch_assessments(db):
    ttl=max(5,min(60,int(os.getenv("SMART_RADAR_ASSESSMENT_CACHE_SECONDS","15"))))
    with _CACHE_LOCK:
        if _AI_CACHE["rows"] is not None and time.monotonic()<_AI_CACHE["expires"]:
            return _AI_CACHE["rows"]
        try:
            rows={x["pilot_post_id"]: dict(x) for x in db.execute(text("SELECT pilot_post_id,result_json,relevance_score,priority_score,processed_at FROM pilot_smart_radar.post_assessments")).mappings()}
        except Exception:
            db.rollback()
            return {}
        _AI_CACHE.update(rows=rows,expires=time.monotonic()+ttl)
        return rows

def fetch_states(db):
    try:
        return {x["finding_id"]: dict(x) for x in db.execute(text(
            "SELECT finding_id,status,first_reviewed_at,next_followup,updated_at "
            "FROM pilot_smart_radar.finding_states")).mappings()}
    except Exception:
        db.rollback()
        return {}

def source_view(p):
    from .source_ids import canonical_source_id
    view={k:p.get(k) for k in ("pilot_post_id","platform","published_at_raw","account_raw",
            "message_original","source_url","source_verification_status","original_category_hint")}
    view["canonical_source_id"]=canonical_source_id("radar",p["pilot_post_id"])
    return view

def build_findings(posts, states, assessments=None):
    # Topic-centric findings with stable IDs and independently tracked officer
    # decisions. Original posts appear as linked evidence, never duplicated cases.
    return build_topic_findings(posts, states, assessments or {}, actors, source_view)

def access_findings(db,user):
    """Dashboard and finding details use the SAME saved Inbox source of truth."""
    from .inbox_radar import live_inbox_findings
    principal=authorised(db,user)
    findings,_=live_inbox_findings(db,principal,fetch_states(db))
    return findings

@router.get("/dashboard")
def dashboard(response:Response,user:User=Depends(current_user),db:Session=Depends(get_db)):
    response.headers["Cache-Control"]="private, no-store"
    from .inbox_radar import live_inbox_findings
    principal=authorised(db,user)
    findings,inbox=live_inbox_findings(db,principal,fetch_states(db))
    posts=[post for finding in findings for post in finding["posts"]]
    platforms=Counter(post["platform"] for post in posts)
    candidates=Counter()
    sentiments=Counter()
    geo_mentions=Counter()
    verified_locations=Counter()
    for finding in findings:
        candidates.update(finding.get("actor_mentions") or {})
        sentiments.update(finding.get("sentiment_counts") or {})
        geo_mentions.update(finding.get("geo_signal_counts") or {})
        verified_locations.update(finding.get("verified_incident_counts") or {})
    from .registry import registry_action
    watchlist=registry_action(db,principal,'watchlistSummary',{})
    return {"batch_id":None,"source_total":len(posts),
        "source_unique_urls":len({post["source_url"] for post in posts if post["source_url"]}),
        "findings":[{k:v for k,v in finding.items() if k!="posts"} for finding in findings],
        "platform_counts":dict(platforms),"candidate_mentions":candidates.most_common(10),
        "sentiment_counts":dict(sentiments),
        "geo_signal_counts":dict(geo_mentions),
        "verified_incident_counts":dict(verified_locations),
        "watchlist_profiles":watchlist['items'],
        "watchlist_source":watchlist['source'],
        "sentiment_coverage":{'classified':sum(sentiments.get(v,0) for v in ('POSITIVE','NEGATIVE','NEUTRAL')),
                              'unclassified':sentiments.get('UNCLASSIFIED',0)},
        "geographic_scope_note":"Saved location labels are unverified context; verified incidents require human confirmation.",
        "reviewed_total":sum(bool(finding["human_reviewed"]) for finding in findings),
        "mode":"SAVED_INBOX_SOURCE_OF_TRUTH","scoring_ready":False,
        "feed_source":"CAMPAIGN_INTELLIGENCE_INBOX_SAVED_ASSESSMENTS",
        "inbox_source_scope":"PERMISSION_SCOPED_RELEVANT_ONLY",
        "inbox_window_limit":300,
        "truncated_to_inbox_window":len(inbox.get("findings") or [])>=300,
        "disclaimer":"Only authorized, relevant saved Inbox assessments. Topic groups do not establish a shared incident or legal conclusion. No AI calls.",
        "jurisdictions":[],"timezone":"Asia/Jakarta","paid_provider_called":False}

@router.get("/finding/{finding_id}")
def finding_detail(finding_id:str,response:Response,user:User=Depends(current_user),db:Session=Depends(get_db)):
    response.headers["Cache-Control"]="private, no-store"
    result=next((f for f in access_findings(db,user) if f["id"]==finding_id),None)
    if result is None:raise HTTPException(404,"Finding unavailable")
    return result

@router.get("/history/{finding_id}")
def history(finding_id:str,user:User=Depends(current_user),db:Session=Depends(get_db)):
    findings=access_findings(db,user)
    if finding_id not in {f["id"] for f in findings}:raise HTTPException(404,"Finding unavailable")
    try:
        events=[dict(x) for x in db.execute(text(
            "SELECT action,note,actor_id,created_at,next_followup FROM pilot_smart_radar.review_events "
            "WHERE finding_id=:id ORDER BY created_at DESC,id DESC"),{"id":finding_id}).mappings()]
    except Exception:
        db.rollback();events=[]
    for e in events:
        e["created_at"]=str(e["created_at"])
        if e["next_followup"]:e["next_followup"]=str(e["next_followup"])
    return {"events":events}

class Decision(BaseModel):
    finding_id:str
    action:str
    note:str=""
    next_followup:str|None=None

@router.post("/decision")
def decision(body:Decision,user:User=Depends(current_user),db:Session=Depends(get_db)):
    authorised(db,user,decision=True)
    # Never permit old pilot finding IDs to receive new operational decisions.
    findings=access_findings(db,user)
    f=next((x for x in findings if x["id"]==body.finding_id),None)
    if not f:raise HTTPException(404,"Finding does not exist")
    old=f["status"]
    transitions={
      "awareness":{"queue":"pending"},
      "pending":{"close":"closed","investigate":"investigating","monitor":"monitoring"},
      "investigating":{"update":"investigating","close":"closed","escalate":"escalated","monitor":"monitoring"},
      "monitoring":{"investigate":"investigating","close":"closed","monitor":"monitoring"},
      "closed":{"reopen":"pending"},"escalated":{"reopen":"pending"}}
    if body.action not in transitions.get(old,{}):raise HTTPException(409,f"Cannot {body.action} from {old}")
    if body.action in {"reopen","escalate"} and not body.note.strip():
        raise HTTPException(400,"A short reason or escalation reference is required")
    if len(body.note)>6000:raise HTTPException(400,"Note too long")
    if body.next_followup:
        try:datetime.strptime(body.next_followup,"%Y-%m-%d")
        except ValueError:raise HTTPException(400,"Invalid follow-up date")
    new=transitions[old][body.action]
    try:
        # One transaction: current status + immutable event, locked against competing decisions.
        db.execute(text("""INSERT INTO pilot_smart_radar.finding_states
          (finding_id,status,first_reviewed_at,updated_at)
          VALUES(:id,:status,NULL,now()) ON CONFLICT(finding_id) DO NOTHING"""),
          {"id":body.finding_id,"status":old})
        current=db.execute(text("SELECT status,first_reviewed_at FROM pilot_smart_radar.finding_states WHERE finding_id=:id FOR UPDATE"),
            {"id":body.finding_id}).mappings().first()
        if current["status"]!=old: raise HTTPException(409,"Finding changed; refresh and retry")
        first_review=(body.action in {"close","investigate","monitor"} and old=="pending")
        db.execute(text("""UPDATE pilot_smart_radar.finding_states SET
           status=:status,first_reviewed_at=CASE WHEN :first_review THEN COALESCE(first_reviewed_at,now()) ELSE first_reviewed_at END,
           next_followup=CASE WHEN :followup <> '' THEN CAST(:followup AS date)
                        WHEN :action IN ('close','escalate','reopen') THEN NULL ELSE next_followup END,
           updated_at=now() WHERE finding_id=:id"""),
           {"id":body.finding_id,"status":new,"first_review":first_review,
            "followup":body.next_followup or "", "action":body.action})
        db.execute(text("""INSERT INTO pilot_smart_radar.review_events
            (finding_id,action,note,actor_id,next_followup,created_at)
            VALUES(:id,:action,:note,:actor,:followup,now())"""),
           {"id":body.finding_id,"action":body.action,"note":body.note.strip(),
            "actor":str(user.id),"followup":body.next_followup})
        db.commit()
    except HTTPException:
        db.rollback();raise
    except Exception as exc:
        db.rollback();raise HTTPException(503,"Decision store not installed or unavailable") from exc
    return {"ok":True,"finding_id":body.finding_id,"status":new,"action":body.action}
