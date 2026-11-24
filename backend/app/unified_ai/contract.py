"""Unified BAWASLU assistant request contract. Independent of legacy AI handlers.

Workspace selects analytical structure, never the permitted evidence population.
The officer's active access grant remains the sole source of jurisdiction.
"""
import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from fastapi import HTTPException

LEADERS=frozenset({"National Administrator","National Leadership","Provincial Administrator"})
SOURCES={
 "WEB_ONLY":{"publicWeb":True,"smartRadar":False,"legalReferences":False},
 "WEB_SMARTRADAR":{"publicWeb":True,"smartRadar":True,"legalReferences":True},
 "SMARTRADAR_ONLY":{"publicWeb":False,"smartRadar":True,"legalReferences":True},
}
PERSPECTIVES=frozenset({"AUTO","EXECUTIVE","OPERATIONAL","RESEARCH"})
WORKFLOWS=frozenset({"AUTO","RESEARCH","STRATEGY","DRAFTING"})
REFERENCE=re.compile(r"\b(?:SOCIAL-\d+|INT-[\w:-]+|DOC-\d+-P\d+|ATT-[a-f0-9]{32}-S\d+)\b",re.I)
PERSONAL=re.compile(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}|\b(?:\+?\d[\d\s().-]{9,}\d)\b",re.I)
RECENT=re.compile(r"\b(today|yesterday|this week|last|past|current|recent|latest|tonight|tomorrow|"
                  r"this month|now|hari ini|kemarin|terbaru|terkini|minggu ini|bulan ini|"
                  r"terakhir|sejak|jadwal|ditunda|postponed|correction|perkembangan)\b",re.I)
STEPS=re.compile(r"\b(strategy|strategi|solutions?|solusi|options?|opsi|taktik|tactics?|"
                 r"plans?|rencana|roadmap|recommend|rekomendasi|milestones?|tindak lanjut)\b",re.I)
DRAFT=re.compile(r"\b(draft|memo|email|reply|surat|balas|ringkas|shorten|rewrite|"
                 r"ubah|revise|translate|laporan|briefing|turn into an email)\b",re.I)
CONTEXT_WORDS=frozenset({"dengan","untuk","dalam","yang","berdasarkan","tentang","serta","apakah","pada",
    "mengenai","bagaimana","why","which","where","what","could","about","this","those","from","please",
    "past","last","weeks","days","recent","latest","since","bawaslu","intelijen","indonesia"})


def local_today(now=None):
    if now is None:now=datetime.now(timezone.utc)
    return now.astimezone(ZoneInfo("Asia/Jakarta")).date()


def window(question,today=None):
    """Calendar date bounds for an explicitly expressed recent period.

    Includes current day and the prior n-1 calendar days.
    This is not a claim that source coverage is complete.
    """
    q=question.casefold()
    today=today or local_today()
    match=re.search(r"(?:past|last|selama|dalam)\s+(\d{1,3})\s+(days?|weeks?|hari|minggu)(?:\s+terakhir)?",q)
    if not match:
        match=re.search(r"(\d{1,3})\s+(days?|weeks?|hari|minggu)\s+terakhir",q)
    if match:
        amount=min(int(match.group(1)),365)
        unit=match.group(2)
        days=amount*(7 if unit.startswith("week") or unit.startswith("minggu") else 1)
        return {"start":(today-timedelta(days=max(0,days-1))).isoformat(),
                "end":today.isoformat(),"kind":"EXPLICIT_RECENT","days":days}
    if re.search(r"\b(this week|minggu ini|pekan ini)\b",q):
        return {"start":(today-timedelta(days=today.weekday())).isoformat(),
                "end":today.isoformat(),"kind":"WEEK_TO_DATE"}
    if re.search(r"\b(this month|bulan ini)\b",q):
        return {"start":today.replace(day=1).isoformat(),"end":today.isoformat(),"kind":"MONTH_TO_DATE"}
    return None


def choose_workflow(question,chosen,previous_draft=""):
    if chosen!="AUTO":return chosen
    if DRAFT.search(question) or (previous_draft and re.search(r"\b(shorter|singkat|lebih formal|ubah jadi)\b",question,re.I)):
        return "DRAFTING"
    if STEPS.search(question):return "STRATEGY"
    return "RESEARCH"


def safe_for_public(question):
    return bool(str(question or "").strip()) and not REFERENCE.search(question) and not PERSONAL.search(question)


def validate(body,grant):
    if not isinstance(body,dict):raise HTTPException(422,"Expected an object")
    q=body.get("question")
    if not isinstance(q,str) or not q.strip() or len(q)>1600:
        raise HTTPException(422,"Question must contain 1–1600 characters")
    mode=str(body.get("workspace") or "OPERATIONAL").upper()
    if mode not in ("MANAGEMENT","OPERATIONAL"):
        raise HTTPException(422,"Invalid assistant workspace")
    if mode=="MANAGEMENT" and grant.get("role") not in LEADERS:
        raise HTTPException(403,"Management AI requires an authorised leadership role")
    choice=str(body.get("sourceMode") or "WEB_ONLY").upper()
    if choice not in SOURCES:
        raise HTTPException(422,"Select Web only, Web + SmartRadar or SmartRadar only")
    perspective=str(body.get("perspective") or "AUTO").upper()
    workflow=str(body.get("workflow") or "AUTO").upper()
    if perspective not in PERSPECTIVES or workflow not in WORKFLOWS:
        raise HTTPException(422,"Invalid perspective or workflow")
    history=body.get("history") or []
    if not isinstance(history,list) or len(history)>12:
        raise HTTPException(422,"Invalid conversation history")
    clean=[]
    for row in history:
        if not isinstance(row,dict) or row.get("role") not in ("assistant","user") or not isinstance(row.get("text"),str):
            raise HTTPException(422,"Invalid conversation item")
        clean.append({"role":row["role"],"text":row["text"][:1200]})
    prev=body.get("previousDraft") or ""
    if not isinstance(prev,str) or len(prev)>9000:
        raise HTTPException(422,"Invalid previous draft")
    q=q.strip()
    return {"question":q,"workspace":mode,"source_mode":choice,
            "sources":dict(SOURCES[choice]),"perspective":perspective,
            "workflow":choose_workflow(q,workflow,prev),"history":clean[-8:],
            "previous_draft":prev[:7500],"recent":bool(RECENT.search(q) or window(q)),
            "window":window(q),"as_of":local_today().isoformat()}


def jurisdiction(grant):
    scope=grant.get("geographic_scope") or "Unknown"
    return {"office_level":("BAWASLU RI" if scope=="Nationwide" else
            "BAWASLU province" if scope=="Province" else
            "BAWASLU kabupaten/kota" if scope=="Regency/City" else "Officer"),
            "scope":scope,"province":grant.get("province") or "",
            "regency_city":grant.get("regency_city") or "",
            "role":grant.get("role") or "Unknown"}
