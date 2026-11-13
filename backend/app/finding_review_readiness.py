"""Conservative operational readiness for an authorized Command Centre finding.

Read-only workflow cues, not election-law applicability or platform verdicts.
No database/model access; data must already be permission-scoped by the caller.
"""
from .assistant_grounding import _election_types

LEVELS=("P1","P2","P3")

def build_finding_review_readiness(finding,assessment):
    prov=assessment.get("source_provenance") or {}
    legal=assessment.get("legal") or {}
    policy=assessment.get("platform_policy") or {}
    pages=[p for p in legal.get("approved_reference_pages") or []
           if p.get("review_status")=="OFFICER_REVIEWED"]
    reviewed_ids={str(p.get("record_id")) for p in pages}
    flagged=legal.get("status")=="PRELIMINARY_REVIEW_RECOMMENDED"
    counts=policy.get("status_counts") or {}
    cues=int(counts.get("REVIEW_INDICATED") or 0)+int(counts.get("CONTEXT_REVIEW_REQUIRED") or 0)
    issues=[]
    def add(code,priority,count=1,page_ids=()):
        refs=list(dict.fromkeys(str(x) for x in page_ids if str(x) in reviewed_ids))[:8]
        issues.append({"code":code,"priority":priority,
                       "affected_count":min(max(int(count),1),9999),
                       "legal_page_ids":refs,"officer_review_required":True})
    if not int(assessment.get("source_count_assessed") or 0):
        add("NO_SAVED_SOURCE_EVIDENCE","P1")
    if prov.get("source_count_matches_finding") is False:
        add("SOURCE_COUNT_RECONCILIATION","P1")
    conflicts=sum(int(prov.get(k) or 0) for k in
                  ("source_text_conflicts","source_url_conflicts","source_platform_conflicts"))
    if conflicts:add("CONFLICTING_SAVED_SOURCE_METADATA","P1",conflicts)
    missing=int(prov.get("missing_original_text") or 0)+int(prov.get("missing_original_url") or 0)
    if missing:add("ORIGINAL_POST_VERIFICATION","P1",missing)
    if flagged and not pages:add("REVIEWED_LEGAL_REFERENCE_REQUIRED","P1")
    if flagged and pages:
        metadata_missing=[p["record_id"] for p in pages
                          if not p.get("legal_version_label") or not p.get("legal_effective_date")]
        if metadata_missing:
            add("LEGAL_VERSION_METADATA_INCOMPLETE","P2",len(metadata_missing),metadata_missing)
        election=_election_types(str(finding.get("title") or ""))
        if len(election)==1:
            conflicts=[p["record_id"] for p in pages
                       if p.get("legal_election_type") in {"PEMILU","PILKADA"}
                       and p.get("legal_election_type")!=election[0]]
            unknown=[p["record_id"] for p in pages
                     if p.get("legal_election_type") not in {"PEMILU","PILKADA","BOTH"}]
            if conflicts:add("POSSIBLE_ELECTION_TYPE_MISMATCH","P2",len(conflicts),conflicts)
            if unknown:add("ELECTION_TYPE_METADATA_UNKNOWN","P3",len(unknown),unknown)
        add("LEGAL_CURRENTNESS_AND_AUTHORITY_UNVERIFIED","P3",len(pages),
            [p["record_id"] for p in pages])
    if cues:
        add("PLATFORM_POST_CONTEXT_REVIEW","P2",cues)
        if policy.get("policy_references"):
            add("CURRENT_PLATFORM_POLICY_UNVERIFIED","P3",len(policy["policy_references"]))
    unsupported=int(counts.get("POLICY_NOT_CONFIGURED") or 0)
    if unsupported:add("PLATFORM_POLICY_REFERENCE_UNAVAILABLE","P2",unsupported)
    issues.sort(key=lambda x:(LEVELS.index(x["priority"]),x["code"]))
    return {
        "schema":"BAWASLU_COMMAND_CENTRE_FINDING_READINESS_V1531",
        "finding_id":str(assessment.get("finding_id") or ""),
        "status":"OFFICER_REVIEW_REQUIRED",
        "review_order_is_legal_severity":False,
        "legal_violation_confirmed":False,
        "platform_violation_confirmed":False,
        "legal_applicability_verified":False,
        "legal_currentness_verified":False,
        "current_platform_policy_verified":False,
        "automatic_assignment_created":False,
        "automatic_takedown_requested":False,
        "human_review_required":True,
        "issue_count":len(issues),"issues":issues,
        "priority_counts":{key:sum(row["priority"]==key for row in issues)
                           for key in LEVELS},
        "source_count_assessed":int(assessment.get("source_count_assessed") or 0),
        "preliminary_platform_cue_count":cues,
        "preliminary_legal_flag":flagged,
        "evaluation_basis":"AUTHORIZED_SAVED_INBOX_AND_REVIEWED_LEGAL_PDF_METADATA",
        "paid_provider_called":False,
    }
