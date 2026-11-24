"""Fresh assistant contracts: independent from any previous AI Assistant."""
import re
from datetime import datetime, timezone

SOURCE_MODES = ("WEB_ONLY", "WEB_AND_RECORDS", "RECORDS_ONLY")
TASKS = ("AUTO", "RESEARCH", "LEGAL", "STRATEGY", "PLAN", "DRAFT")
LEADERS = frozenset(("National Administrator","National Leadership","Provincial Administrator"))
REDACT = re.compile(r"\b(?:INT-[A-Za-z0-9:_-]+|SOCIAL-\d+|DOC-\d+-P\d+)\b|"
    r"[\w.+-]+@[\w.-]+\.[a-z]{2,}|\b(?:\+?\d[\d -]{9,}\d)\b",re.I)
DATE_RE = re.compile(r"\b(?:today|yesterday|latest|recent|current|"
    r"last|past|this week|this month|202[5-9]|terbaru|terkini|hari ini|kemarin|"
    r"pekan ini|minggu ini|bulan ini|terakhir|jadwal|sidang|putusan)\b",re.I)


def utc_now():
    return datetime.now(timezone.utc).isoformat()

def validate(body,role):
    if not isinstance(body,dict):raise ValueError("Expected a JSON object")
    q=body.get("question")
    if not isinstance(q,str) or not q.strip() or len(q)>1000:
        raise ValueError("Question must contain 1–1000 characters")
    mode=body.get("source_mode","WEB_ONLY")
    task=body.get("task","AUTO")
    perspective=body.get("perspective","AUTO")
    if mode not in SOURCE_MODES:raise ValueError("Invalid source mode")
    if task not in TASKS:raise ValueError("Invalid task type")
    if perspective not in ("AUTO","OFFICER","LEADERSHIP"):raise ValueError("Invalid perspective")
    if perspective=="LEADERSHIP" and role not in LEADERS:
        raise PermissionError("Leadership perspective requires leadership access")
    return {"question":q.strip(),"source_mode":mode,"task":task,
            "perspective":perspective,"recent":bool(DATE_RE.search(q))}

def classification(question,task):
    if task!="AUTO":return task
    q=question.casefold()
    if re.search(r"\b(draft|memo|email|letter|surat|buatkan memo|susun laporan)\b",q):return "DRAFT"
    if re.search(r"\b(strategy|strategi|options?|trade-offs?|pilihan strategi)\b",q):return "STRATEGY"
    if re.search(r"\b(action plan|rencana aksi|rencana tindak lanjut|langkah tindak lanjut)\b",q):return "PLAN"
    if re.search(r"\b(law|legal|pasal|peraturan|hukum|kewenangan|yurisdiksi)\b",q):return "LEGAL"
    return "RESEARCH"

def safe_public_query(q):
    return bool(q) and not REDACT.search(q)
