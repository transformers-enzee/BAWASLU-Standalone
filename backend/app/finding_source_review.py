"""Read-only source-by-source investigation routing for Command Centre.

Consumes only the finding's already authorized saved Inbox posts.
Never creates assignments, declares legal/policy violations, or calls AI.
"""
from collections import Counter
from urllib.parse import urlsplit

_RANK={"P1":0,"P2":1,"P3":2}
_POLICY_CUES={"REVIEW_INDICATED","CONTEXT_REVIEW_REQUIRED"}

def _safe_url(value):
    value=str(value or "").strip()
    try:
        parsed=urlsplit(value)
        if parsed.scheme in {"http","https"} and parsed.hostname and not parsed.username and not parsed.password:
            return value
    except ValueError:
        pass
    return ""

def _numeric_id(value):
    val=str(value or "").strip()
    return val if val.isascii() and val.isdigit() and int(val)>0 else ""

def source_review_plan(rows,groups,outcomes,finding_flagged):
    """One bounded row per canonical source, never one per campaign link."""
    all_rows=[]
    for chosen,variants,outcome in zip(rows,groups,outcomes):
        sid=str(chosen.get("canonical_source_id") or chosen.get("result_id") or "").strip()[:120]
        urls={v for variant in variants if (v:=_safe_url(variant.get("source_url")))}
        texts={str(v.get("message_original") or "").strip()
               for v in variants if str(v.get("message_original") or "").strip()}
        platforms={str(v.get("platform") or "").strip().casefold()
                   for v in variants if str(v.get("platform") or "").strip()}
        original=next((v for v in variants if _safe_url(v.get("source_url"))),"")
        preferred_url=_safe_url(chosen.get("source_url")) or _safe_url(original.get("source_url") if isinstance(original,dict) else "")
        conflict=any((len(texts)>1,len(urls)>1,len(platforms)>1))
        has_text=bool(texts)
        has_url=bool(preferred_url)
        policy_status=str(outcome.get("status") or "INSUFFICIENT_SOURCE")
        steps=[]
        def add(code):
            if code not in steps:steps.append(code)
        if not has_text:add("RECOVER_ORIGINAL_POST_TEXT")
        if not has_url:add("RECOVER_OR_VALIDATE_ORIGINAL_POST_URL")
        if conflict:add("RECONCILE_SAVED_SOURCE_VARIANTS")
        add("VERIFY_ORIGINAL_POST_CONTEXT_AND_PUBLICATION")
        if policy_status in _POLICY_CUES:add("COMPARE_CURRENT_PLATFORM_RULES")
        elif policy_status=="POLICY_NOT_CONFIGURED":add("LOCATE_CURRENT_PLATFORM_POLICY")
        if finding_flagged:
            add("CHECK_ELECTORAL_LAW_AND_JURISDICTION")
        add("OFFICER_DECISION_REQUIRED")
        priority="P1" if not has_text or not has_url or conflict else (
            "P2" if policy_status in _POLICY_CUES or policy_status=="POLICY_NOT_CONFIGURED" or finding_flagged
            else "P3")
        all_rows.append({
            "source_id":sid,"result_id":_numeric_id(chosen.get("result_id")),
            "campaign_id":_numeric_id(chosen.get("campaign_id")),
            "platform":str(outcome.get("platform") or "Unknown")[:70],
            "source_url":preferred_url,"source_url_verification":"SCHEME_ONLY_NOT_CONTENT_VERIFIED",
            "source_text_available":has_text,
            "original_url_available":has_url,
            "saved_text_conflict":len(texts)>1,
            "saved_url_conflict":len(urls)>1,
            "saved_platform_conflict":len(platforms)>1,
            "linked_variants":len(variants),
            "policy_status":policy_status,
            "policy_version_verified":False,
            "finding_level_potential_violation_flag":bool(finding_flagged),
            "source_level_legal_violation_confirmed":False,
            "source_level_platform_violation_confirmed":False,
            "priority":priority,"officer_check_codes":steps,
            "casework_url":None,
        })
    all_rows.sort(key=lambda row:(_RANK[row["priority"]],
              not row["saved_text_conflict"],not row["saved_url_conflict"],
              row["source_id"],row["result_id"]))
    counts=Counter(row["priority"] for row in all_rows)
    return {"schema":"BAWASLU_SOURCE_INVESTIGATION_PLAN_V1533",
            "source_count":len(all_rows),
            "priorities":{"P1":counts["P1"],"P2":counts["P2"],"P3":counts["P3"]},
            "actions":all_rows[:12],"sampled":len(all_rows)>12,
            "source_level_claims_not_confirmed":True,
            "review_priority_is_violation_severity":False,
            "casework_links_from_authorized_existing_workflow_only":True,
            "source_urls_not_truth_verified":True,
            "human_review_required":True,
            "automatic_assignment_created":False,
            "automatic_takedown_requested":False,
            "paid_provider_called":False}
