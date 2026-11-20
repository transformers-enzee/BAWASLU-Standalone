"""Conservative action cards from ALREADY AUTHORIZED Command Centre records.

No model calls, database mutations, guessed incident provinces, findings of
guilt, legal determinations, assignments or referrals.
"""
import re

def category_domain(value):
    name=str(value or "").strip()
    if not name or name.casefold() in ("officer-reviewed issue","classification review needed"):
        return "UNCLASSIFIED", "Officer classification required"
    patterns=(
        (r"penyadap|intersepsi|wiretap|interception","GENERAL_CRIMINAL_LAW","General criminal-law allegation"),
        (r"mkmk|judicial ethics|etik hakim|konflik kepentingan hakim","INSTITUTIONAL_ETHICS","Institutional or judicial ethics"),
        (r"kolom kosong|surat suara|ballot|rekapitulasi|pemungutan suara ulang","ELECTORAL_ADMINISTRATION","Electoral administration issue"),
        (r"politik uang|money politics|vote buying","ELECTORAL_OFFENCE_SIGNAL","Potential election-related offence"),
    )
    for pattern,code,description in patterns:
        if re.search(pattern,name,re.I):
            return code,description
    return "SAVED_ISSUE_UNVERIFIED","Saved potential-issue category"

def action_steps(domain,original_available):
    return [
        ("Verify the original saved publication, exact quote, date and source."
         if original_available else "Obtain and verify the original source; the saved excerpt alone is insufficient."),
        "Determine the actual incident location and electoral impact; monitoring or assigned jurisdiction does not prove either.",
        ("Request HQ legal review of specific electoral connection and jurisdiction before considering routing or referral."
         if domain in ("GENERAL_CRIMINAL_LAW","INSTITUTIONAL_ETHICS") else
         "Request authorized officer review of the applicable election rules, source evidence and appropriate next step."),
    ]

def build_action_intelligence(alerts,manual_rows,geographic_scope,limit=10):
    """Only call with records prefiltered through access.allowed and run scope."""
    owner=("HQ Intelligence / Legal Reviewer" if geographic_scope=="Nationwide"
           else "Authorized Provincial / Local Reviewer")
    items=[]
    seen=set()
    for row in alerts or []:
        cid=str(row.get("campaign_id") or "")
        rid=str(row.get("result_id") or "")
        if not cid.isdigit() or not rid.isdigit() or rid in seen:
            continue
        seen.add(rid)
        category=str(row.get("category") or "Officer-reviewed issue")[:160]
        domain,domain_label=category_domain(category)
        monitoring=str(row.get("province") or "").strip()
        if monitoring.lower() in ("unknown / unclassified","unclassified","unknown"):
            monitoring=""
        items.append({
            "id":"SOCIAL-"+rid,"record_type":"ASSESSED_SOCIAL",
            "campaign_id":cid,"result_id":rid,
            "title":str(row.get("campaign_name") or "Saved social evidence")[:180],
            "violation_type":category,"domain":domain,"domain_label":domain_label,
            "legal_status":"NOT_DETERMINED","electoral_nexus":"OFFICER_REVIEW_REQUIRED",
            "officer_flag_status":str(row.get("review_status") or "AWAITING_REVIEW"),
            "evidence_excerpt":str(row.get("evidence_quote") or row.get("summary") or "")[:300],
            "source_provenance":str(row.get("signal_provenance") or "SAVED_ASSESSMENT")[:80],
            "review_geography":monitoring or "Unclassified",
            "review_geography_basis":"CAMPAIGN_MONITORING_SCOPE_ONLY",
            "affected_provinces":[],"incident_location_verified":False,
            "owner_role_suggested":owner,"officer_assigned":False,
            "actions":action_steps(domain,bool(row.get("source_url"))),
        })
    for row in manual_rows or []:
        category=str(row.get("potential_issue_category") or "").strip()
        state=str(row.get("review_status") or "")
        if not category and state not in ("Pending Review","Awaiting Validation"):
            continue
        rid=str(row.get("id") or "")
        if not rid.isdigit() or "INT-"+rid in seen:
            continue
        seen.add("INT-"+rid)
        domain,domain_label=category_domain(category)
        review_geo=str(row.get("province") or "").strip()
        if not review_geo:
            review_geo=("National — no affected province established"
                        if row.get("jurisdiction_type")=="National" else "Unclassified")
        items.append({
            "id":str(row.get("campaign_name") or "INT-"+rid)[:64],
            "record_type":"INTELLIGENCE_ITEM","item_id":rid,
            "title":str(row.get("title") or row.get("summary") or "Saved intelligence")[:180],
            "violation_type":category[:160] or "Classification review needed",
            "domain":domain,"domain_label":domain_label,
            "legal_status":"NOT_DETERMINED","electoral_nexus":"OFFICER_REVIEW_REQUIRED",
            "officer_flag_status":state or "NOT_REVIEWED",
            "evidence_excerpt":str(row.get("summary") or "")[:300],
            "source_provenance":"SAVED_INTELLIGENCE_RECORD",
            "review_geography":review_geo,
            "review_geography_basis":"RECORDED_JURISDICTION_NOT_INCIDENT_LOCATION",
            "affected_provinces":[],"incident_location_verified":False,
            "owner_role_suggested":owner,"officer_assigned":False,
            "actions":action_steps(domain,bool(row.get("source_url"))),
        })
    total=len(items)
    output=items[:max(1,min(int(limit),20))]
    return {
        "items":output,"candidate_count":total,"displayed_count":len(output),
        "scope":"HQ" if geographic_scope=="Nationwide" else "PROVINCIAL_OR_LOCAL",
        "basis":"AUTHORIZED_SAVED_ASSESSMENTS_AND_INBOX",
        "generation_mode":"DETERMINISTIC_NO_PAID_AI",
        "confirmed_violation_count":None,
        "created_assignments":False,
        "affected_provinces_not_inferred":True,
        "notice":"These are review prompts from saved evidence, not newly generated AI verdicts or registered election violations. Monitoring campaign and record jurisdictions are not verified incident locations. All legal and geographic decisions require officer review.",
    }
