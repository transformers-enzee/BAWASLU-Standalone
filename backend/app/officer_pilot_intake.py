"""Read-only shortlist of authorized saved Inbox sources for an officer pilot.

This only prepares a link to the EXISTING, separately permission-checked Inbox
casework flow. No legal finding, case assignment, AI inference, or database write
is ever performed here. Input findings must come from live_inbox_findings()
after its usual authorization and relevance filters.
"""
from urllib.parse import urlencode

_RANK={"source_review":0,"discussion":1,"narrative_candidate":2,"source_awareness":3}
_REASONS={
    "source_review":"SAVED_SOURCE_FLAG_REVIEW",
    "discussion":"SAVED_PUBLIC_CONCERN_DISCUSSION",
    "narrative_candidate":"SAVED_EMERGING_NARRATIVE",
    "source_awareness":"SAVED_RELEVANT_INBOX_SOURCE",
}

def _original_url_available(value):
    # Original link must be HTTP(S), with a host and no credentials.
    # This is syntactic screening, never verification of source content.
    from urllib.parse import urlsplit
    try:
        p=urlsplit(str(value or "").strip())
        return bool(p.scheme in ("http","https") and p.hostname
                    and not p.username and not p.password)
    except ValueError:
        return False

def _positive_id(value):
    """Reject huge, non-ASCII, signed and forged IDs before SQL or URLs."""
    if isinstance(value,bool):
        return ""
    value=str(value or "").strip()
    if not value or len(value)>19 or not value.isascii() or not value.isdigit():
        return ""
    number=int(value)
    if not 0<number<=9223372036854775807:
        return ""
    return str(number)

def officer_pilot_candidates(findings,visible_cases=(),limit=12):
    """Deduplicate by original post ID. Prefer a complete available source
    before the saved signal rank; never rank by legal severity."""
    found={}
    for finding in findings or []:
        if not isinstance(finding,dict):continue
        kind=str(finding.get("kind") or "")
        if kind not in _RANK:continue
        posts=finding.get("posts") or []
        if not isinstance(posts,list):continue
        for post in posts:
            if not isinstance(post,dict):continue
            sid=_positive_id(post.get("result_id"))
            cid=_positive_id(post.get("campaign_id"))
            if not sid or not cid:continue
            has_text=bool(str(post.get("message_original") or "").strip())
            has_url=_original_url_available(post.get("source_url"))
            # Never let a flagged but unusable campaign version hide a
            # separately authorized version with both text and a safe URL.
            rank=(not (has_text and has_url), _RANK[kind], int(sid), int(cid))
            current=found.get(sid)
            if current is None or rank<current[0]:
                found[sid]=(rank,{
                    "source_id":sid,"campaign_id":cid,
                    "platform":str(post.get("platform") or "Unknown")[:55],
                    "review_signal":_REASONS[kind],
                    "saved_assessment_only":True,
                    "source_text_available":has_text,
                    "original_source_url_available":has_url,
                    "original_source_verified":False,
                    "incident_jurisdiction_verified":bool(
                        post.get("verified_incident_province")),
                    "verified_incident_province":str(
                        post.get("verified_incident_province") or "")[:128],
                    "review_step":"REVIEW_IN_INBOX" if has_text and has_url
                                  else "RECOVER_SOURCE_EVIDENCE",
                    "source_link":"/inbox?"+urlencode({
                        "campaign_id":cid,"result_id":sid}),
                    "casework_link":(
                        "/inbox?"+urlencode({
                            "casework":"1","source_type":"SOCIAL",
                            "source_id":sid,"campaign_id":cid,
                            "tab":"assignments"})
                        if has_text and has_url else None),
                    "visible_open_case_id":None,
                    "case_already_exists_in_visible_scope":False,
                    "legal_violation_confirmed":False,
                    "automatic_assignment_created":False,
                })
    rows=[value[1] for value in sorted(found.values(),key=lambda x:x[0])]
    source_prefill_available=sum(int(row["source_text_available"] and
        row["original_source_url_available"]) for row in rows)
    visible={}
    for case in visible_cases or ():
        if str(getattr(case,"source_type","")).upper()!="SOCIAL" or getattr(case,"status","")=="CLOSED":
            continue
        sid=_positive_id(getattr(case,"source_id",None))
        cid=_positive_id(getattr(case,"campaign_id",None))
        case_id=_positive_id(getattr(case,"id",None))
        if sid and cid and case_id:
            visible.setdefault((sid,cid),case_id)
    for row in rows:
        existing=visible.get((row["source_id"],row["campaign_id"]))
        if existing:
            row["visible_open_case_id"]=int(existing)
            row["case_already_exists_in_visible_scope"]=True
            row["casework_link"]="/inbox?"+urlencode({
                "casework":"1","case_id":existing,"tab":"reports"})
            row["review_step"]="CONTINUE_VISIBLE_CASEWORK"
    return {
        "schema":"BAWASLU_OFFICER_PILOT_INTAKE_V1544",
        "observed_authorized_unique_sources":len(rows),
        "source_prefill_available_count":source_prefill_available,
        "source_recovery_required_count":len(rows)-source_prefill_available,
        "selection_basis":"USABLE_SOURCE_FIRST_THEN_SAVED_REVIEW_SIGNAL",
        "returned_count":min(len(rows),limit),
        "preview_limit":limit,
        "preview_is_sample":len(rows)>limit,
        "source_population":"SAVED_RELEVANT_PERMISSION_SCOPED_INBOX_WINDOW",
        "not_complete_social_collection":True,
        "priorities_are_not_legal_severity":True,
        "items":rows[:limit],
        "no_paid_provider_called":True,
        "no_assignment_created":True,
        "requires_officer_confirmation":True,
        "original_source_truth_not_verified":True,
        "casework_requires_fresh_source_and_jurisdiction_authorization":True,
    }
