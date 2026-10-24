"""Phase-3 Smart Radar API. Reads original 109 source posts, not synthetic demo data.
This is a PILOT heuristic view; AI-scored findings should replace heuristic groups after review.
No Supabase credentials are sent to the browser. Routes use app authentication and role grants.
"""
from collections import Counter, defaultdict
from datetime import datetime, timezone
import re
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session
from .db import get_db
from .auth import current_user
from .models import User
from .access import profile, has

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
    # Pilot records have no verified event-location assignments. Showing them as a
    # provincial feed would violate geographic ACL and imply false precision.
    if p.get("geographic_scope") != "Nationwide":
        raise HTTPException(403, "Pilot records require verified jurisdiction before regional access")
    return p

def fetch_sources(db):
    try:
        return [dict(x) for x in db.execute(text(SOURCE_SQL), {"batch": BATCH}).mappings()]
    except Exception as exc:
        db.rollback()
        raise HTTPException(503, "Pilot source table unavailable: check staging DATABASE_URL and import") from exc

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

def fetch_states(db):
    try:
        return {x["finding_id"]: dict(x) for x in db.execute(text(
            "SELECT finding_id,status,first_reviewed_at,next_followup,updated_at "
            "FROM pilot_smart_radar.finding_states")).mappings()}
    except Exception:
        db.rollback()
        return {}

def source_view(p):
    return {k:p.get(k) for k in ("pilot_post_id","platform","published_at_raw","account_raw",
            "message_original","source_url","source_verification_status","original_category_hint")}

def build_findings(posts, states):
    buckets={}
    for p in posts:
        ident,title,player=grouping(p)
        if ident not in buckets:
            buckets[ident]={"id":ident,"title":title,"player":player,"perspective":"operations",
                "topics":set(),"posts":[],"actors":set(),"published_at":p["published_at_raw"] or "",
                "priority_score":None,"priority_label":"Unscored","geography":"Unresolved"}
        b=buckets[ident]
        b["posts"].append(source_view(p))
        b["topics"].add(detect_topic(p))
        b["actors"].update(actors(p["message_original"]))
        if perspective(p)=="reputation":b["perspective"]="reputation"
        b["published_at"]=max(b["published_at"],p["published_at_raw"] or "")
    for b in buckets.values():
        st=states.get(b["id"],{})
        b["status"]=st.get("status") or "awareness"
        b["human_reviewed"]=bool(st.get("first_reviewed_at"))
        b["next_followup"]=str(st["next_followup"]) if st.get("next_followup") else ""
        b["updated_at"]=str(st.get("updated_at") or "")
        b["topics"]=sorted(b["topics"]);b["actors"]=sorted(b["actors"])
        b["summary"]=(f"{len(b['posts'])} original source post(s) discussing this topic. "
             "Grouping and labels are preliminary; original claims have not been verified.")
        b["supporting_posts"]=len(b["posts"])
    return sorted(buckets.values(),key=lambda x:x["published_at"],reverse=True)

def access_findings(db,user):
    authorised(db,user)
    return build_findings(fetch_sources(db),fetch_states(db))

@router.get("/dashboard")
def dashboard(user:User=Depends(current_user),db:Session=Depends(get_db)):
    findings=access_findings(db,user)
    posts=fetch_sources(db)
    platform_counts=Counter((p.get("platform") or "Unknown").title() for p in posts)
    mention_counts=Counter()
    for p in posts: mention_counts.update(set(actors(p["message_original"])))
    return {"batch_id":BATCH,"source_total":len(posts),"source_unique_urls":len(set(p["source_url"] for p in posts)),
        "findings":findings,"platform_counts":dict(platform_counts),
        "candidate_mentions":mention_counts.most_common(10),
        "reviewed_total":sum(x["human_reviewed"] for x in findings),
        "mode":"PRELIMINARY_SOURCE_GROUPING","scoring_ready":False,
        "disclaimer":"Preliminary source-based grouping. No AI relevance or risk scores have been generated. Claims are unverified.",
        "jurisdictions":["Indonesia - National"],"timezone":"Asia/Jakarta"}

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
    findings=build_findings(fetch_sources(db),fetch_states(db))
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
