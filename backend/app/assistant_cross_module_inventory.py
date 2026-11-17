"""Permission-scoped source inventory; record links never prove corroboration."""
import re
_SOCIAL=re.compile(r"^SOCIAL-([1-9][0-9]{0,17})$")
_ORIGIN=re.compile(r"^social:([1-9][0-9]{0,17})$",re.I)

def _kind(record):
    kind=str(record.get("record_type") or "").upper()
    rid=str(record.get("record_id") or "")
    if kind=="SOCIAL_LISTENING":return "SOCIAL_LISTENING"
    if kind=="FORMAL_INTELLIGENCE" or (not kind and rid.startswith("INT-")):return "FORMAL_INTELLIGENCE"
    if kind=="PDF_KNOWLEDGE":return "PDF_KNOWLEDGE"
    return "OTHER"

def cross_module_inventory(evidence,limit=12):
    """Exact selected source links only; no model/database calls."""
    records=[r for r in (evidence or []) if isinstance(r,dict) and r.get("record_id")]
    social=[r for r in records if _kind(r)=="SOCIAL_LISTENING"]
    formal=[r for r in records if _kind(r)=="FORMAL_INTELLIGENCE"]
    pdf=[r for r in records if _kind(r)=="PDF_KNOWLEDGE"]
    origins={}
    for row in social:
        match=_SOCIAL.fullmatch(str(row.get("record_id") or ""))
        if match:origins.setdefault(match.group(1),[]).append(str(row["record_id"]))
    links=[];seen=set();unlinked=0
    for row in formal:
        match=_ORIGIN.fullmatch(str(row.get("origin_source_id") or ""))
        matched=origins.get(match.group(1),[]) if match else []
        if not matched:unlinked+=1
        for social_id in matched:
            pair=(str(row["record_id"]),social_id)
            if pair in seen:continue
            seen.add(pair)
            if len(links)<limit:
                links.append({"inbox_record_id":pair[0],"social_record_id":pair[1],
                              "basis":"EXPLICIT_SAVED_SOCIAL_SOURCE_ID",
                              "independent_corroboration":False,"source_truth_verified":False})
    return {
        "basis":"CURRENT_PERMISSION_SCOPED_SELECTED_EVIDENCE_ONLY",
        "selected_social_posts":len(social),"selected_inbox_records":len(formal),
        "selected_pdf_pages":len(pdf),
        "selected_other_records":len(records)-len(social)-len(formal)-len(pdf),
        "explicit_source_links":links,"explicit_source_link_count":len(seen),
        "links_truncated":len(seen)>len(links),"unlinked_inbox_records":unlinked,
        "inbox_review_is_not_incident_verification":True,
        "shared_source_is_not_independent_witness":True,
        "cross_module_absence_is_not_no_incident":True,
        "duplicate_posts_are_not_independent_people":True,
        "formal_election_violation_determined":False,"source_truth_verified":False}

def cross_module_instruction(profile):
    if profile not in {"CROSS_MODULE_REVIEW","CASE_REVIEW","EXECUTIVE_REPORT"}:return ""
    return (
        "CROSS-MODULE SOURCE CONSISTENCY: Use cross_module_inventory for separate "
        "selected, authorized Social Listening and Inbox counts. An Inbox review_status "
        "is a workflow state, not proof of verified incident truth. Explain "
        "verification_status separately. explicit_source_links describe an explicit "
        "saved source ID relationship, NOT two independent witnesses or confirmed "
        "duplication. Never add linked Inbox records to social post counts. When "
        "selected_inbox_records=0, say no relevant authorized Inbox record was "
        "selected, not that no incident exists. Unlinked means unknown relationship, "
        "not independent corroboration. Tie empirical findings to exact bracket "
        "citations, identify allegations and uncertainty, and recommend checking "
        "original sources, incident jurisdiction, officer validation and genuinely "
        "independent corroboration. No invented legal verdict or accuracy score."
    )
