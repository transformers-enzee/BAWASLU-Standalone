"""Provisional institutional competence matrix; never declares a violation."""
import re
from .analytics import quote_in_source

AUTHORITIES={
 "BAWASLU":"Election supervision, prevention and certain election-law procedures",
 "KPU":"Election administration and candidacy administration",
 "DKPP":"Ethics of election organizers",
 "MPR":"Constitutional vice-presidential succession",
 "GAKKUMDU":"Coordinated electoral-crime handling, where legally applicable",
 "POLRI":"Potential general crimes, subject to applicable criminal process",
 "KOMDIGI":"Government digital-sector regulatory matters",
 "PLATFORM":"Platform content rules and moderation",
}

def scope_hints(question):
    q=question.casefold()
    flags=[]
    if re.search(r"pemilu|pilkada|election|bawaslu|pengawasan|kampanye|campaign",q):flags.append("POSSIBLE_ELECTORAL_NEXUS")
    if re.search(r"dkpp|etik|ethics|komisioner",q):flags.append("ELECTION_ORGANIZER_ETHICS")
    if re.search(r"mpr|vice president|wakil presiden|succession|pengunduran diri",q):flags.append("CONSTITUTIONAL_PROCESS")
    if re.search(r"platform|tiktok|instagram|facebook|media sosial|social media",q):flags.append("DIGITAL_PLATFORM_ISSUE")
    return {"signals":flags or ["JURISDICTION_NOT_ESTABLISHED"],
        "authorities":AUTHORITIES,
        "rule":"A political controversy alone does not establish BAWASLU jurisdiction or wrongdoing.",
        "checks":["Identify election type, stage, date and place",
                  "Check the currently applicable official legal text and version",
                  "Identify legally competent institution and any referral threshold",
                  "Verify primary documents; distinguish allegation from official finding"]}

def review_legal(rows,records):
    allowed={s["id"]:s for s in records if s.get("read_status") in ("READ","SAVED_SNAPSHOT")}
    legal=[]
    for r in rows[:16] if isinstance(rows,list) else []:
        if not isinstance(r,dict):continue
        citations=list(dict.fromkeys(s for s in r.get("source_ids",[])
                       if isinstance(s,str) and s in allowed))[:4]
        official=any(allowed[s].get("kind")=="OFFICIAL" and allowed[s].get("read_status")=="READ"
                     and re.search(r"jdih|peraturan|putusan|undang|regulation",allowed[s].get("resolved_url") or allowed[s].get("url") or "",re.I)
                     and quote_in_source(r.get("source_quote",""),allowed[s])
                     and re.search(r"\b(?:pasal|article)\s+\d+",str(r.get("source_quote") or ""),re.I)
                     for s in citations)
        reference=str(r.get("legal_reference") or "")[:240]
        legal.append({
            "issue":str(r.get("issue") or "")[:240],
            "institution":str(r.get("institution") or "Authority not established")[:130],
            "legal_reference":reference if official else "Controlling official provision not verified",
            "applicability":str(r.get("applicability") or "Human legal review required")[:380],
            "verification_needed":str(r.get("verification_needed") or "Read controlling rule and check applicable stage")[:350],
            "source_ids":citations,
            "instrument_version":str(r.get("instrument_version") or "")[:200] if official else "",
            "source_quote":str(r.get("source_quote") or "")[:700] if official else "",
            "practical_gap":str(r.get("practical_gap") or "")[:350],
            "proposed_reform":str(r.get("proposed_reform") or "")[:350],
            "reform_owner":str(r.get("reform_owner") or "")[:160],
            "tradeoff":str(r.get("tradeoff") or "")[:300],
            "primary_legal_text_confirmed":False,
            "primary_text_excerpt_matched":official,
            "officer_review_required":True})
    return legal
