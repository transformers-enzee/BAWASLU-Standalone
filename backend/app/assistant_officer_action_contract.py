"""Officer action guidance; no AI, database, or external network calls."""
import re
_ACTION=re.compile(
 r"apa\s+(?:yang\s+)?(?:harus|perlu)\s+(?:dilakukan|ditindaklanjuti)|"
 r"apa\s+langkah|bagaimana\s+(?:menindaklanjuti|tindak\s+lanjut|penanganan)|"
 r"tindak\s+lanjut|rencana\s+tindakan|rekomendasi\s+(?:aksi|tindakan|bawaslu)|"
 r"what\s+should\s+(?:bawaslu|officers?|the\s+team|we)\s+do|"
 r"next\s+steps?|action\s+plan|recommended\s+actions?|follow.up\s+actions?",re.I)
def officer_action_intent(q):
    return bool(_ACTION.search(str(q or "")))
OFFICER_DECISION_CONTRACT = """
BAWASLU INTERNAL DECISION BRIEF: Serve impartial HQ/provincial election
supervisors, not a generic PR audience. For relevant news, allegations and
intelligence, provide 1) VIOLATION TYPE: reported conduct, tentative legal
domain and allegation vs investigation vs court-confirmed status;
2) GEOGRAPHICAL IMPACT: directly affected province/city only when supported,
never from publication address, government-office location, or monitoring
campaign geography; otherwise state not established;
3) RECOMMENDATION: why it matters for electoral supervision, what electoral
nexus and BAWASLU jurisdiction is or is not demonstrated;
4) PRIORITIZED NEXT ACTIONS: next_checks should contain 3-4 specific distinct
steps, each stating suggested REVIEWING ROLE, evidence to obtain, EXPECTED
OUTPUT and conditional ESCALATION or closure criterion. Begin with source
verification, then assess electoral nexus and law, then decide authorized
routing, referral review, monitoring or reasoned closure.
EVIDENCE HIERARCHY: authorized Inbox and social/news records describe what
was reported; independently verified decisions establish official case status.
PDF passages are supporting page-cited legal/SOP REFERENCES, not the sole
brain or proof that an alleged event occurred. Use professional analysis,
consider alternative explanations and show uncertainty. Cite only authorized
IDs for source-dependent claims. Never invent a violation, criminal guilt,
legal article, province, court ruling, deadline, formal case, officer
assignment, or referral. All decisions require authorized officer review.
If evidence is sparse, explain the gap AND give concrete conditional tasks,
not a repetitive no-evidence disclaimer.
Place immediate decision in direct_answer; observations are source-backed
signals; next_checks are actionable officer review tasks.
"""
_FALLBACK={
"id":[
"Tim intelijen Bawaslu: verifikasi sumber asli, tanggal dan bukti pendukung atau bantahan; keluaran: catatan verifikasi dengan ID sumber.",
"Petugas hukum/kewenangan: telaah hubungan konkret dengan Pemilu/Pilkada dan dasar hukum berlaku; keluaran: kajian kewenangan, bukan penetapan pelanggaran.",
"Koordinator pengawasan: konfirmasi lokasi kejadian sebelum penugasan provinsi; dengan persetujuan, pilih pendalaman, pemantauan, rujukan sah atau penutupan beralasan."
],
"en":[
"BAWASLU intelligence team: check original reporting, dates and corroboration; output: a source-linked verification note.",
"Legal/jurisdiction officer: assess electoral nexus and current law; output: a written jurisdiction recommendation, not a verdict.",
"Oversight supervisor: verify incident location before provincial routing; with approval decide inquiry, limited monitoring, lawful referral review or reasoned closure."
]
}
def complete_officer_steps(question, profile, steps, language="id"):
    current=[x.strip() for x in (steps or []) if isinstance(x,str) and x.strip()]
    if profile in ("PDF_GUIDANCE","EXECUTIVE_REPORT"):
        return current,False
    if not officer_action_intent(question) and profile not in ("CASE_REVIEW","ACTION_REQUEST"):
        return current,False
    if len(current)>=3:
        return current,False
    return (current+_FALLBACK.get(language,_FALLBACK["en"])[len(current):])[:4],True


# Strict Responses API section: no official status or geography is inferred here.
BRIEF_FIELDS=("violation_type","legal_status","geographical_impact",
              "electoral_nexus","recommended_decision","evidence_limit")
OFFICER_BRIEF_SCHEMA={
    "type":"object",
    "properties":{key:{"type":"string"} for key in BRIEF_FIELDS},
    "required":list(BRIEF_FIELDS),
    "additionalProperties":False,
}
_CITATION=re.compile(r"\[([A-Z]+-[A-Za-z0-9:_-]+)\]")

def sanitize_officer_brief(candidate,allowed_record_ids):
    obj=candidate if isinstance(candidate,dict) else {}
    allowed={str(x) for x in allowed_record_ids or []}
    def clean(value):
        value=str(value or "").strip()[:650] if isinstance(value,str) else ""
        return _CITATION.sub(lambda m:m.group(0) if m.group(1) in allowed else "",value).strip()
    return {key:clean(obj.get(key)) for key in BRIEF_FIELDS}

def officer_response_mode(depth):
    return {"EXECUTIVE":"QUICK_BRIEF",
            "DEEP":"ACTION_PLAN",
            "INVESTIGATION":"LEGAL_DEEP_DIVE"}.get(
                str(depth or "").upper(),"ACTION_PLAN")

def officer_mode_prompt(depth):
    mode=officer_response_mode(depth)
    if mode=="QUICK_BRIEF":
        return ("QUICK BRIEF: concise decision, the clearest evidenced issue, "
                "province only if substantiated, and at most two specific "
                "officer next steps. Keep all six brief fields short.")
    if mode=="LEGAL_DEEP_DIVE":
        return ("LEGAL DEEP DIVE: analyze alleged conduct, relevant Pemilu/Pilkada "
                "regime, jurisdiction and alternative interpretations. "
                "Distinguish sources from legal authority. Without a verified "
                "current law or official decision, explicitly ask officers to "
                "verify it. Provide up to four detailed officer next steps.")
    return ("ACTION PLAN (DEFAULT): explain the justified immediate decision, "
            "violation domain, geographical impact or uncertainty, jurisdiction, "
            "and three to four practical officer next steps with role, "
            "evidence required, expected output and escalation condition.")

def render_officer_brief(brief, language="id", depth="DEEP",
                         profile="SOCIAL_ANALYSIS"):
    """Rendered text is part of the original citation audit, not an uncited card."""
    if profile in ("PDF_GUIDANCE","EXECUTIVE_REPORT") or language not in ("id","en"):
        return ""
    if not isinstance(brief,dict):
        return ""
    essential=("violation_type","geographical_impact","recommended_decision")
    if not any(str(brief.get(k) or "").strip() for k in essential):
        return ""
    headings=({
        "violation_type":"1. Kategori dugaan pelanggaran / isu",
        "geographical_impact":"2. Dampak geografis",
        "recommended_decision":"3. Rekomendasi keputusan",
        "legal_status":"Status hukum",
        "electoral_nexus":"Keterkaitan Pemilu/Pilkada dan kewenangan",
        "evidence_limit":"Keterbatasan bukti utama",
    } if language=="id" else {
        "violation_type":"1. Violation type / issue",
        "geographical_impact":"2. Geographical impact",
        "recommended_decision":"3. Recommended decision",
        "legal_status":"Legal status",
        "electoral_nexus":"Electoral nexus and jurisdiction",
        "evidence_limit":"Key evidence limitation",
    })
    keys=list(essential)
    if officer_response_mode(depth)!="QUICK_BRIEF":
        keys+=["legal_status","electoral_nexus","evidence_limit"]
    unknown=("Belum ditetapkan; perlu verifikasi petugas."
             if language=="id" else "Not established; officer review required.")
    return "\n\n".join("**"+headings[k]+":** "+(brief.get(k) or unknown)
                      for k in keys)

def operational_brief_readiness(brief,actions,profile,depth):
    """Completeness diagnostic only: does NOT measure factual/legal accuracy."""
    if profile in ("PDF_GUIDANCE","EXECUTIVE_REPORT"):
        return {"status":"NOT_APPLICABLE","factually_verified":False}
    essential=("violation_type","geographical_impact","recommended_decision")
    missing=[k for k in essential if not str((brief or {}).get(k) or "").strip()]
    count=sum(isinstance(x,str) and bool(x.strip()) for x in actions or [])
    minimum=1 if officer_response_mode(depth)=="QUICK_BRIEF" else 3
    return {"status":"REVIEW_REQUIRED" if missing or count<minimum
            else "STRUCTURE_PRESENT_UNVERIFIED",
            "missing_fields":missing,"action_count":count,
            "minimum_actions":minimum,"factually_verified":False,
            "officer_approved":False}
