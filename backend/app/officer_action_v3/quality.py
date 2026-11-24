"""Independent quality gate for claim, legal, action and response provenance."""
import re
from .claims import verify_claims
from .legal import review_legal
from .depth import depth_for
from .language import requested_language,wrong_language
from .analytics import build_series,audit_report

CITE=re.compile(r"\[((?:P|R)-\d+)\]")
HTTP=re.compile(r"https?://[^\s\)\]>]+",re.I)
UNSAFE=re.compile(r"\b(?:immediately sanction|automatically file|issue a penalty|"
    r"arrest|order a takedown|ban the candidate|declare guilty|"
    r"langsung menghukum|otomatis melaporkan pidana|tetapkan bersalah)\b",re.I)
RELEVANCES={"DIRECT","POSSIBLE","NOT_ESTABLISHED","NONE"}

def _text(v,cap=1500):
    return str(v or "").strip()[:cap]

def finalize(raw,sources,question,task,web_status,mode,hints):
    usable={s["id"]:s for s in sources if s.get("read_status") in ("READ","SAVED_SNAPSHOT")}
    ids=set(usable)
    def citations(row):
        return list(dict.fromkeys(x for x in (row.get("source_ids") or [])
                                  if isinstance(x,str) and x in ids))[:5]
    def prose(v,cap=1500):
        text=_text(v,cap)
        text=CITE.sub(lambda m:m.group(0) if m.group(1) in ids else "",text)
        # LLM-authored web URLs are not trustworthy unless source URLs were
        # retrieved by this fresh pipeline and have been read.
        urls={s.get("url") for s in usable.values() if s.get("read_status")=="READ"}
        return HTTP.sub(lambda m:m.group(0) if m.group(0).rstrip(".,;") in urls else "[unverified link omitted]",text)
    raw=raw if isinstance(raw,dict) else {}
    lang=requested_language(question)
    mismatch=wrong_language(raw,lang)
    if mismatch:raw={}
    claims=verify_claims(raw.get("claims",[]),sources)
    legal=review_legal(raw.get("legal",[]),sources)
    relevance=_text(raw.get("relevance"),50).upper()
    if relevance not in RELEVANCES:relevance="NOT_ESTABLISHED"
    # An AI cannot establish direct institutional jurisdiction from a news
    # headline or from an automatic, unverified legal interpretation.
    if relevance=="DIRECT" and not any(
        s.get("kind")=="OFFICIAL" and s.get("read_status")=="READ" and
        re.search(r"bawaslu|pengawas|dkpp",s.get("excerpt",""),re.I)
        for s in sources):
        relevance="POSSIBLE"
    actions=[];seen=set()
    for row in (raw.get("actions") if isinstance(raw.get("actions"),list) else [])[:8]:
        if not isinstance(row,dict):continue
        task_text=prose(row.get("task"),450)
        if not task_text or UNSAFE.search(task_text) or task_text.casefold() in seen:continue
        seen.add(task_text.casefold())
        entry={"task":task_text,"owner_role":prose(row.get("owner_role"),140),
               "evidence_needed":prose(row.get("evidence_needed"),350),
               "deliverable":prose(row.get("deliverable"),300),
               "decision_gate":prose(row.get("decision_gate"),350),
               "source_ids":citations(row),"status":"PROPOSED_NOT_ASSIGNED",
               "target_period":prose(row.get("target_period"),100),"priority_reason":prose(row.get("priority_reason"),300),
               "success_metric":prose(row.get("success_metric"),240)}
        if min(len(entry[k]) for k in ("owner_role","evidence_needed","deliverable","decision_gate"))<5:continue
        actions.append(entry)
    opts=[]
    for row in (raw.get("options") if isinstance(raw.get("options"),list) else [])[:8]:
        if not isinstance(row,dict) or not row.get("option"):continue
        opts.append({"option":prose(row.get("option"),160),"benefit":prose(row.get("benefit"),320),
                    "tradeoff":prose(row.get("tradeoff"),320),
                    "change_trigger":prose(row.get("change_trigger"),320),
                    "source_ids":citations(row)})
    depth=depth_for(question)
    answer=prose(raw.get("answer"),72000 if depth=="DEEP" else 32000)
    takeaway=prose(raw.get("key_takeaway"),500)
    headline=prose(raw.get("headline"),170)
    impact=prose(raw.get("bawaslu_implication"),600)
    decision=prose(raw.get("recommended_decision"),520)
    limits=[prose(x,260) for x in (raw.get("limitations") or [])[:5] if isinstance(x,str) and x.strip()]
    if not usable:
        # Source-free general concepts/planning are allowed only if clearly labeled;
        # do not promote generated text to findings or official casework.
        answer=(("Panduan umum — bukan temuan yang didukung sumber. " if lang=="id" else "General guidance only — no source-backed factual finding. ")+answer if raw and answer and depth=="QUICK" else "No source-backed finding can be established for this question.")
        takeaway="Verify an authoritative source before making an institutional decision."
        impact="BAWASLU relevance cannot be established without consulted evidence."
        decision="No formal casework action. Request an official-source verification."
        claims=[];legal=[];actions=[];opts=[]
        headline="Evidence unavailable — review required"
        limits=["No independent public page or authorized saved record was consulted."]
    if mode!="RECORDS_ONLY" and web_status not in ("READ","NOT_SELECTED"):
        prefix="Riset web belum memperoleh sumber yang dapat dibaca. " if lang=="id" else "Live public research could not verify readable sources. "
        answer=prefix+answer
        limits.insert(0,"Current public developments remain unverified; search did not return readable pages.")
    if task=="DRAFT":
        draft=prose(raw.get("draft"),6000) if usable else ""
    else:draft=""
    if not actions and usable and task!="DRAFT" and relevance not in ("NONE","NOT_ESTABLISHED"):
        actions=[{"task":"Verify the original source and decide whether BAWASLU has a legally relevant oversight role.",
                  "owner_role":"Authorized supervision/legal reviewer",
                  "evidence_needed":"Original dated source, relevant election stage and applicable rule",
                  "deliverable":"Documented jurisdiction and evidence check",
                  "decision_gate":"Escalate only after verified electoral nexus and competent approval; otherwise close with reasons",
                  "source_ids":[],"status":"PROPOSED_NOT_ASSIGNED"}]
    if mismatch:
        answer="A report in the requested language could not be generated. Please retry." if lang!="id" else "Laporan dalam bahasa yang diminta belum dapat dihasilkan. Silakan coba lagi."
        limits.insert(0,answer)
    if not usable and lang=="id" and not (raw and depth=="QUICK" and not mismatch):
        answer=("Riset web belum memperoleh sumber yang dapat dibaca. " if mode!="RECORDS_ONLY" else "")+"Belum ada temuan faktual yang didukung sumber untuk pertanyaan ini."
        takeaway="Verifikasi sumber resmi sebelum mengambil keputusan kelembagaan."
        impact="Bukti yang tersedia belum cukup untuk menilai kewenangan Bawaslu."
        decision="Belum ada dasar untuk tindakan formal; verifikasi sumber primer terlebih dahulu."
        headline="Bukti belum tersedia"
        limits=["Tidak ada halaman publik terbaca atau catatan tersimpan yang diizinkan."]
    series=build_series(raw.get("numeric_series",[]),sources)
    report_audit=audit_report(answer,sources)
    # Only structured, attributed findings are shown as facts in the UI;
    # narrative is an AI interpretation requiring officer review.
    return {
        "headline":headline or "Officer decision brief",
        "answer":answer or "The question requires further documented verification.",
        "key_takeaway":takeaway or "A verified institutional decision is not yet established.",
        "bawaslu_implication":impact or "Confirm whether BAWASLU has jurisdiction before casework.",
        "relevance":relevance if usable else "NOT_ESTABLISHED",
        "recommended_decision":decision or "Verify primary records before escalation.",
        "claims":claims[:30],"legal":legal,"options":opts,"actions":actions[:8],
        "draft":draft,"limitations":limits[:8],"research_depth":depth,"answer_language":lang,
        "numeric_series":series,"report_audit":report_audit,
        "quality":{"read_public_count":sum(s.get("read_status")=="READ" for s in sources),
                   "saved_snapshot_count":sum(s.get("kind")=="SAVED_RECORD" for s in sources),
                   "attributed_claims":sum(bool(x["source_ids"]) for x in claims),
                   "unsupported_claims":sum(not x["source_ids"] for x in claims),
                   "legal_applicability_officer_verified":False,
                   "actions_executed":False,
                   "human_approval_required":True,
                   "no_prior_assistant_context":True},
        "notice":"Proposed AI decision support only. No official finding, assignment, referral, enforcement or public communication."
    }

def fallback(question,mode,web_status,hints,records):
    return finalize({},records,question,"RESEARCH",web_status,mode,hints)
