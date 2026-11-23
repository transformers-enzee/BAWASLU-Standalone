"""Evidence-bounded public research -> BAWASLU officer decisions.

No database access, case assignment, legal verdict or external message is performed.
Only the selected public research summary and returned public URLs enter the second
model call; private conversation records and officer identities are never sent.
"""
import json
import re
from urllib.parse import urlsplit

import httpx

from .assistant_web_first import safe_web_urls

FIELDS=("task","owner_role","evidence_required","expected_output","escalation_condition")
URLS={"type":"array","items":{"type":"string"}}
ACTION={
    "type":"object",
    "properties":{**{name:{"type":"string"} for name in FIELDS},"source_urls":URLS},
    "required":[*FIELDS,"source_urls"],
    "additionalProperties":False
}
LEGAL_FIELDS=("domain","competent_authority","rule_reference","applicability","verification_needed")
LEGAL={
    "type":"object",
    "properties":{**{name:{"type":"string"} for name in LEGAL_FIELDS},"source_urls":URLS},
    "required":[*LEGAL_FIELDS,"source_urls"],
    "additionalProperties":False
}
CLAIM={
    "type":"object",
    "properties":{"claim":{"type":"string"},"source_urls":URLS,
                  "evidence_status":{"type":"string","enum":["PRIMARY_SOURCE_REPORTED","MEDIA_REPORTED","ALLEGATION","UNRESOLVED"]}},
    "required":["claim","source_urls","evidence_status"],
    "additionalProperties":False
}
DECISION_SCHEMA={
    "type":"object",
    "properties":{
        "answer":{"type":"string"},
        "relevance":{"type":"string","enum":["DIRECT_OVERSIGHT","POSSIBLE_NEXUS","NO_ESTABLISHED_NEXUS"]},
        "institutional_implication":{"type":"string"},
        "recommended_decision":{"type":"string"},
        "reason":{"type":"string"},
        "legal_review":LEGAL,
        "actions":{"type":"array","items":ACTION},
        "claims":{"type":"array","items":CLAIM},
        "missing_evidence":{"type":"string"}
    },
    "required":["answer","relevance","institutional_implication","recommended_decision",
                "reason","legal_review","actions","claims","missing_evidence"],
    "additionalProperties":False
}

# Never infer legal authenticity just because a citation is at a government hostname.
OFFICIAL_HOSTS=("bawaslu.go.id","kpu.go.id","dkpp.go.id","mkri.id","mahkamahagung.go.id",
                "mpr.go.id","dpr.go.id","peraturan.bpk.go.id","jdihn.go.id",
                "komdigi.go.id","polri.go.id","setkab.go.id")
BAD_ACTION=re.compile(
    r"\b(?:automatically (?:file|assign|refer|sanction|remove)|"
    r"(?:langsung|otomatis) (?:hukum|tetapkan|hapus|blokir|laporkan sebagai pelanggaran)|"
    r"order (?:takedown|arrest|punishment)|declare (?:guilt|a violation))\b",re.I)
INLINE_LINK=re.compile(r"\[([^\]\n]{1,150})\]\((https?://[^\s)]+)\)")
BARE_URL=re.compile(r"https?://[^\s<>)]+")


def _text(value,limit=500):
    return str(value or "").strip()[:limit] if isinstance(value,str) else ""


def _urls(values,allowed):
    safe=set(safe_web_urls(values if isinstance(values,list) else []))
    return [url for url in allowed if url in safe]


def _official(url):
    try:
        host=(urlsplit(url).hostname or "").lower()
        return any(host==domain or host.endswith("."+domain) for domain in OFFICIAL_HOSTS)
    except (TypeError,ValueError):
        return False


def _clean_answer(text,allowed):
    """Strip hyperlinks to URLs not genuinely returned by the public search."""
    allowed=set(allowed)
    def replace_link(match):
        return match.group(0) if match.group(2) in allowed else match.group(1)+" [source not consulted]"
    text=INLINE_LINK.sub(replace_link,_text(text,5100))
    def replace_bare(match):
        candidate=match.group(0).rstrip(".,;!?")
        return match.group(0) if candidate in allowed else "[source not consulted]"
    return BARE_URL.sub(replace_bare,text)


def safe_decision(candidate,consulted_urls):
    """Reject invented citations, unsupported legal certainty and non-actionable tasks."""
    if not isinstance(candidate,dict):
        return None
    allowed=safe_web_urls(consulted_urls)
    if not allowed:return None
    answer=_clean_answer(candidate.get("answer"),allowed)
    if len(answer)<45:return None
    relevance=candidate.get("relevance")
    if relevance not in ("DIRECT_OVERSIGHT","POSSIBLE_NEXUS","NO_ESTABLISHED_NEXUS"):
        relevance="POSSIBLE_NEXUS"
    # A claim of direct BAWASLU responsibility needs a source-grounded supervision nexus.
    # Political succession or a public controversy alone does not establish it.
    context=_text(candidate.get("_research_summary"),4700).casefold()
    if relevance=="DIRECT_OVERSIGHT" and context and not re.search(
        r"bawaslu|panwaslu|pengawas(?:an)? pemilu|election supervis(?:or|ion)|"
        r"badan pengawas|election oversight",context,re.I):
        relevance="POSSIBLE_NEXUS"
    claims=[]
    for row in (candidate.get("claims") if isinstance(candidate.get("claims"),list) else [])[:5]:
        if not isinstance(row,dict):continue
        urls=_urls(row.get("source_urls"),allowed)
        claim=_text(row.get("claim"),360)
        if not claim or not urls:continue
        status=row.get("evidence_status")
        if status not in ("PRIMARY_SOURCE_REPORTED","MEDIA_REPORTED","ALLEGATION","UNRESOLVED"):
            status="UNRESOLVED"
        if status=="PRIMARY_SOURCE_REPORTED" and not any(_official(x) for x in urls):
            status="MEDIA_REPORTED"
        claims.append({"claim":claim,"source_urls":urls,
                       "evidence_status":status,"verified_by_officer":False})
    raw_legal=candidate.get("legal_review") or {}
    if not isinstance(raw_legal,dict):raw_legal={}
    legal={name:_text(raw_legal.get(name),380) for name in LEGAL_FIELDS}
    legal["source_urls"]=_urls(raw_legal.get("source_urls"),allowed)
    legal["official_primary_available"]=any(_official(x) for x in legal["source_urls"])
    legal["official_rule_document_located"]=any(
        _official(x) and re.search(r"jdih|peraturan|undang|regulation|putusan|law|\.pdf",x,re.I)
        for x in legal["source_urls"])
    legal["officer_verification_required"]=True
    if not legal["official_rule_document_located"]:
        legal["rule_reference"]="Official controlling provision not confirmed in consulted primary sources."
        if not legal["verification_needed"]:
            legal["verification_needed"]="Check controlling official text, election type, stage, location and current applicability."
    plan=[]
    seen_actions=set()
    for row in (candidate.get("actions") if isinstance(candidate.get("actions"),list) else [])[:3]:
        if not isinstance(row,dict):continue
        cleaned={name:_text(row.get(name),440) for name in FIELDS}
        if any(len(cleaned[name])<8 for name in FIELDS):continue
        if BAD_ACTION.search(cleaned["task"]):continue
        normalized=re.sub(r"\s+"," ",cleaned["task"].casefold())
        if normalized in seen_actions:continue
        seen_actions.add(normalized)
        plan.append({
            "owner_role":cleaned["owner_role"],
            "milestone":cleaned["task"],
            "required_evidence":cleaned["evidence_required"],
            "expected_output":cleaned["expected_output"],
            "review_point":cleaned["escalation_condition"],
            "source_urls":_urls(row.get("source_urls"),allowed),
            "source_ids":[],
            "status":"PROPOSED_ONLY_NO_AUTOMATED_ACTION"
        })
    # Without a demonstrated institutional nexus, an AI cannot initiate casework.
    if relevance=="NO_ESTABLISHED_NEXUS":
        plan=[row for row in plan if re.search(r"verif|check|assess|review|periksa|tinjau|confirm|clarif",row["milestone"],re.I)][:1]
    return {
        "answer":answer,
        "officer_decision":{
            "relevance":relevance,
            "institutional_implication":_text(candidate.get("institutional_implication"),520),
            "recommended_decision":_text(candidate.get("recommended_decision"),470),
            "reason":_text(candidate.get("reason"),470),
            "legal_review":legal,
            "claims":claims,
            "missing_evidence":_text(candidate.get("missing_evidence"),550),
            "status":"PROPOSED_ANALYSIS_REQUIRES_OFFICER_REVIEW",
            "consulted_urls":allowed,
            "quality":{
                "claim_count":len(claims),
                "attributed_claim_count":sum(bool(c["source_urls"]) for c in claims),
                "action_count":len(plan),
                "action_structure_complete":all(bool(r["required_evidence"] and r["expected_output"] and r["review_point"]) for r in plan),
                "primary_legal_reference_located":legal["official_rule_document_located"],
                "answer_has_consulted_citation":any(url in answer for url in allowed),
                "legal_applicability_verified":False,
                "review_required":True,
                "automated_actions_executed":False,
            },
        },
        "decision_plan":plan
    }


def fallback_decision(question,language="en",urls=()):
    """Transparent conservative fallback, never a fabricated legal or case finding."""
    is_id=language=="id"
    task=("Periksa dokumen resmi, konteks tanggal, dan apakah perkara terkait kewenangan BAWASLU."
          if is_id else "Check primary documents, dates and whether the matter falls within BAWASLU's legal remit.")
    return {"officer_decision":{
        "relevance":"POSSIBLE_NEXUS",
        "institutional_implication":("Kaitan langsung dengan tugas BAWASLU belum dinilai berdasarkan sumber primer."
                                     if is_id else "A direct BAWASLU oversight nexus has not been established from the available primary evidence."),
        "recommended_decision":("Verifikasi sumber dan kewenangan sebelum memutuskan tindak lanjut; tidak ada tindakan formal otomatis."
                                if is_id else "Verify the primary evidence and jurisdiction before choosing a follow-up; no automatic formal action."),
        "reason":"",
        "legal_review":{
            "domain":"UNRESOLVED","competent_authority":"",
            "rule_reference":"Official controlling provision not confirmed.",
            "applicability":"","verification_needed":task,
            "source_urls":[],"official_primary_available":False,
            "officer_verification_required":True},
        "claims":[],"missing_evidence":task,
        "status":"ACTION_SYNTHESIS_UNAVAILABLE",
        "consulted_urls":safe_web_urls(urls),
        "quality":{"claim_count":0,"attributed_claim_count":0,"action_count":1,
                   "action_structure_complete":True,"primary_legal_reference_located":False,
                   "legal_applicability_verified":False,"review_required":True,
                   "automated_actions_executed":False}},
        "decision_plan":[{
            "owner_role":"Authorized BAWASLU information-verification officer",
            "milestone":task,
            "required_evidence":"Original official documents, dates, actor role and incident location",
            "expected_output":"Documented verification and jurisdiction review note",
            "review_point":"Refer for competent legal review only if specific electoral conduct, authority and evidence are established.",
            "source_urls":[],"source_ids":[],"status":"PROPOSED_ONLY_NO_AUTOMATED_ACTION"}]}


def synthesize_public_decision(question,research,key,model,base,language="en",assistant_mode="OPERATIONAL",perspective="AUTO"):
    """One optional source-bounded synthesis call. Fail closed to a review-only plan."""
    urls=safe_web_urls((research or {}).get("urls"))
    summary=_text((research or {}).get("summary"),4700)
    if not key or not urls or not summary:
        return fallback_decision(question,language,urls)
    system=(
        "You are a politically neutral Indonesian BAWASLU supervision adviser. This is a second-stage assessment "
        "of public web research, not a new search. ONLY the URLs in public_urls were consulted in the prior step; "
        "the provided research summary may mix official records, journalism, allegations and interpretation. "
        "NEVER assert primary-source verification of a claim unless the cited specific official publication actually supports it. "
        "Cite claims immediately beside them using Markdown links to permitted public_urls and do not invent URLs, "
        "case statuses, court holdings, legislation, deadlines, statistics, political motivations or institutional authority. "
        "Start 'answer' in 2-3 sentences with the key takeaway AND what it changes for BAWASLU or why no action is warranted. "
        "Then explain what changed over which dates, relevant evidence, conflicts and the material uncertainty. "
        "Do not repeat the action list in 'answer': actions are displayed in separate officer cards. "
        "Write the answer in the language of the question. For a draft, put the draft first. "
        "Classify relevance DIRECT_OVERSIGHT only when the source-backed issue specifically concerns election supervision "
        "or BAWASLU conduct. POSSIBLE_NEXUS is unverified jurisdiction; NO_ESTABLISHED_NEXUS means no formal casework. "
        "Distinguish MPR constitutional succession from BAWASLU's election oversight, DKPP ethics adjudication, "
        "KPU administration, law enforcement, and platform moderation: those authorities are not interchangeable. "
        "A social media post or political criticism is not by itself evidence of an electoral violation. "
        "In legal_review explain the actual possible regulatory domain, competent authority, precise legal source ONLY if cited "
        "in public_urls and shown by the summary, outstanding election-type/stage/jurisdiction checks, and applicability limits. "
        "In actions give at most three role-specific, concrete, lawful officer verification/preparation tasks "
        "with evidence to collect, exact deliverable, and conditional review or closure gate. Propose no action if none is warranted. "
        "All formal referrals, assignment, enforcement and communications require an authorized human review. "
        "Even a PRIMARY_SOURCE_REPORTED claim is not human-authenticated as a legal fact. "
        "Never pretend 14-day sentiment trends were measured from narrower samples. "
        "Do not include private record references or details not in supplied research. "
        "Keep 'answer' concise; use no generic repeated warnings."
    )
    data={"question":_text(question,1000),"public_research_summary":summary,
          "public_urls":urls,"language":language,"workspace_mode":assistant_mode,"perspective":perspective}
    try:
        with httpx.Client(timeout=httpx.Timeout(48.0,connect=8.0,read=48.0,write=12.0,pool=8.0)) as client:
            response=client.post(base+"/responses",headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"},
                json={"model":model,"store":False,"input":[{"role":"system","content":system},
                    {"role":"user","content":json.dumps(data,ensure_ascii=False)}],
                    "text":{"format":{"type":"json_schema","name":"bawaslu_officer_decision_v1777",
                                       "strict":True,"schema":DECISION_SCHEMA}},
                    "max_output_tokens":2300})
        if response.status_code>=400:return fallback_decision(question,language,urls)
        payload=response.json()
        if payload.get("status")=="incomplete":return fallback_decision(question,language,urls)
        from .intelligence_assistant import _response_output_text
        candidate=json.loads(_response_output_text(payload))
        if isinstance(candidate,dict):
            candidate["_research_summary"]=summary
        result=safe_decision(candidate,urls)
        return result if result is not None else fallback_decision(question,language,urls)
    except (httpx.HTTPError,ValueError,TypeError,KeyError):
        return fallback_decision(question,language,urls)
