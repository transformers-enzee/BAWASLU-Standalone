"""v148.8 bounded source-linked questions for the independent Assistant review.

This route reuses already permission-scoped, cached Inbox findings; it neither
runs an AI model nor crawls any new posts. Prepared questions are NOT executed.
The result is a diversity-oriented convenience sample, not a random or complete
population sample and never a substitute for officer selection.
"""
from collections import Counter
from urllib.parse import urlsplit
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from .access import has, profile
from .auth import current_user
from .db import get_db
from .models import User

router=APIRouter(prefix="/api/assistant-evaluation",tags=["assistant-evaluation"])

CATEGORIES=(
    "POTENTIAL_VIOLATION_SIGNAL",
    "PUBLIC_CONCERN",
    "EMERGING_NARRATIVE",
    "GEOGRAPHIC_UNCERTAINTY",
    "PLATFORM_POLICY_COMPARISON",
    "CROSS_MODULE_COMPARISON",
    "GENERAL_SOURCE_REVIEW",
)
BASE_QUOTAS={
    "POTENTIAL_VIOLATION_SIGNAL":5,
    "PUBLIC_CONCERN":5,
    "EMERGING_NARRATIVE":4,
    "GEOGRAPHIC_UNCERTAINTY":3,
    "PLATFORM_POLICY_COMPARISON":3,
    "CROSS_MODULE_COMPARISON":2,
    "GENERAL_SOURCE_REVIEW":2,
}
KIND_SCORE={
    "source_review":4,
    "discussion":3,
    "narrative_candidate":2,
    "source_awareness":1,
}
ALLOWED_PLATFORMS={
    "Instagram","TikTok","YouTube","X","Facebook","Threads",
    "Reddit","LinkedIn","Telegram"
}

def _http_url(raw):
    value=str(raw or "").strip()
    if len(value)>1500 or any(ch in value for ch in "\r\n\t"):
        return ""
    try:
        parts=urlsplit(value)
    except ValueError:
        return ""
    if parts.scheme not in ("https","http") or not parts.netloc or parts.username or parts.password:
        return ""
    return value

def _platform(raw):
    value=str(raw or "").strip()
    return value if value in ALLOWED_PLATFORMS else "Other"

def _categories(row):
    flags=[]
    kind=row["kind"]
    if kind=="source_review":flags.append("POTENTIAL_VIOLATION_SIGNAL")
    if kind=="discussion":flags.append("PUBLIC_CONCERN")
    if kind=="narrative_candidate":flags.append("EMERGING_NARRATIVE")
    if row["has_unverified_region"] or row["verified_incident_province"]:
        flags.append("GEOGRAPHIC_UNCERTAINTY")
    if row["platform"]!="Other":
        flags.append("PLATFORM_POLICY_COMPARISON")
    flags.extend(("CROSS_MODULE_COMPARISON","GENERAL_SOURCE_REVIEW"))
    return flags

def _prompt(category, source_id, platform):
    base=f"saved relevant Social Listening source [{source_id}] on {platform}"
    if category=="POTENTIAL_VIOLATION_SIGNAL":
        task=("Describe only what the post alleges, what original evidence and "
              "incident jurisdiction need officer verification, and which legal "
              "questions remain open. Do not determine a violation.")
    elif category=="PUBLIC_CONCERN":
        task=("Describe the public concern attributed to this post, separate "
              "assertions from verified facts, and identify checks BAWASLU "
              "should make before escalating it.")
    elif category=="EMERGING_NARRATIVE":
        task=("Summarize the narrative from this exact saved post. Explain "
              "why one post alone cannot establish a recurring trend, "
              "audience size or coordinated behavior.")
    elif category=="GEOGRAPHIC_UNCERTAINTY":
        task=("Distinguish province mentions from verified incident location. "
              "Identify what proof of location and jurisdiction is still needed.")
    elif category=="PLATFORM_POLICY_COMPARISON":
        task=("Separate potential election-law issues from official platform "
              "community rules. If current official platform policy is not in "
              "the authorized evidence, state that it is unverified.")
    elif category=="CROSS_MODULE_COMPARISON":
        task=("Compare this post to relevant authorized Intelligence Inbox "
              "records, cite an actual INT ID only if available, and say "
              "explicitly when no matching formal record was retrieved.")
    else:
        task=("Summarize the post's attributed claims, saved sentiment label "
              "and limitations. Do not extrapolate to all posts or voters.")
    return (f"For the {base}, {task} Cite the exact [{source_id}] source "
            "only if actually retrieved. Do not invent source IDs.")

def build_evaluation_question_plan(findings, target=24):
    """Pure transform of already authorized cached Inbox findings."""
    if type(target) is not int or not 1<=target<=30:
        raise ValueError("Target must be between 1 and 30")
    candidates={}
    skip=Counter()
    for finding in findings or []:
        if not isinstance(finding,dict):
            continue
        kind=str(finding.get("kind") or "source_awareness")
        if kind not in KIND_SCORE:
            continue
        for post in finding.get("posts") or []:
            if not isinstance(post,dict):
                continue
            canonical=str(post.get("canonical_source_id") or "")
            rid=str(post.get("result_id") or "")
            if not rid.isdigit() or int(rid)<=0 or canonical!="social:"+rid:
                skip["invalid_source_id"]+=1
                continue
            url=_http_url(post.get("source_url"))
            if not url:
                skip["missing_or_unsafe_original_url"]+=1
                continue
            candidate={
                "source_record_id":"SOCIAL-"+rid,
                "source_id":rid,
                "source_url":url,
                "campaign_id":str(post.get("campaign_id") or ""),
                "platform":_platform(post.get("platform")),
                "kind":kind,
                "published_at_raw":str(post.get("published_at_raw") or "")[:40],
                "has_unverified_region":bool(post.get("geographic_mentions_unverified")),
                "verified_incident_province":bool(post.get("verified_incident_province")),
            }
            existing=candidates.get(rid)
            if existing and KIND_SCORE[existing["kind"]]>=KIND_SCORE[kind]:
                skip["duplicate_cross_campaign_link"]+=1
                continue
            if existing:skip["duplicate_cross_campaign_link"]+=1
            candidates[rid]=candidate

    rows=sorted(candidates.values(),key=lambda x:(
        x["published_at_raw"],int(x["source_id"])),reverse=True)
    available={name:sum(name in _categories(row) for row in rows)
               for name in CATEGORIES}
    selected=[]
    used=set()
    selected_platforms=Counter()
    selected_buckets=Counter()
    quota={key:min(value,max(1,round(target*value/24)))
           for key,value in BASE_QUOTAS.items()}
    def add(category,platform_limit=None):
        if selected_buckets[category]>=quota.get(category,target):
            return False
        for candidate in rows:
            rid=candidate["source_id"]
            if rid in used or category not in _categories(candidate):
                continue
            if platform_limit is not None and selected_platforms[candidate["platform"]]>=platform_limit:
                continue
            used.add(rid)
            selected_platforms[candidate["platform"]]+=1
            selected_buckets[category]+=1
            source_id=candidate["source_record_id"]
            selected.append({
                "question_number":len(selected)+1,
                "category":category,
                "source_record_id":source_id,
                "source_url":candidate["source_url"],
                "campaign_id":candidate["campaign_id"],
                "platform":candidate["platform"],
                "source_publication_time_unverified":candidate["published_at_raw"],
                "question":_prompt(category,source_id,candidate["platform"]),
                "execution_mode":"AUTHORIZED_SAVED_EVIDENCE_DATA_ONLY",
                "not_run":True,
                "officer_must_verify_original":True,
                "legal_verdict_confirmed":False,
                "ai_credit_spent":False,
            })
            return True
        return False
    # First pass spreads categories and platforms where available.
    platform_cap=max(2,(target+3)//4)
    for cap in (platform_cap,None):
        while len(selected)<target:
            changed=False
            for category in CATEGORIES:
                if len(selected)>=target:break
                changed=add(category,cap) or changed
            if not changed:break
    # Fill any remaining positions from genuinely distinct eligible sources.
    for candidate in rows:
        if len(selected)>=target:break
        if candidate["source_id"] in used:continue
        quota["GENERAL_SOURCE_REVIEW"]=target
        add("GENERAL_SOURCE_REVIEW")
    gaps=[c for c in CATEGORIES if not available[c]]
    return {
        "framework":"BAWASLU_ASSISTANT_EVALUATION_PLAN_V1488",
        "sampling_method":"BOUNDED_DETERMINISTIC_DIVERSITY_CONVENIENCE_SAMPLE",
        "target_questions":target,
        "prepared_questions":len(selected),
        "shortfall":target-len(selected),
        "observed_eligible_unique_sources":len(rows),
        "category_available_sources":available,
        "category_selected_questions":dict(selected_buckets),
        "missing_categories":gaps,
        "skipped_source_links":dict(skip),
        "questions":selected,
        "negative_control":{
            "category":"NO_EVIDENCE_CONTROL",
            "source_record_id":"SOCIAL-0",
            "question":("Using saved source [SOCIAL-0] only, report whether an "
                        "authorized relevant source exists. Do not infer content "
                        "or cite any other source."),
            "not_a_real_source":True,
            "excluded_from_real_source_count":True,
            "not_run":True,
        },
        "missing_review_tracks":[
            "OFFICER_REVIEWED_LEGAL_PDF_QUESTIONS_NOT_SAMPLED",
            "INDEPENDENT_FORMAL_RECORD_MATCH_NOT_VERIFIED",
        ],
        "population_scope":"PERMISSION_SCOPED_RELEVANT_SAVED_INBOX",
        "source_window_limit":"UP_TO_300_LINKS_PER_AUTHORIZED_CAMPAIGN",
        "window_completeness_verified":False,
        "statistically_representative":False,
        "individual_claims_verified":False,
        "officer_approval_granted":False,
        "human_accuracy_measured":False,
        "real_model_answers_generated":False,
        "paid_ai_calls":0,
        "new_social_crawls":0,
        "database_writes":0,
        "status":"PREPARED_FOR_EXPLICIT_OFFICER_REVIEW",
    }

@router.get("/questions")
def evaluation_questions(
    response:Response,
    target:int=Query(default=24,ge=1,le=30),
    user:User=Depends(current_user),
    db:Session=Depends(get_db)
):
    principal=profile(db,user)
    if not has(principal,"view_intelligence"):
        raise HTTPException(403,"Intelligence evaluation requires view permission")
    from .inbox_radar import live_inbox_findings
    try:
        findings,_=live_inbox_findings(db,principal)
    except PermissionError:
        raise HTTPException(403,"Saved Inbox source access denied")
    # Operational errors must not silently produce a fabricated "empty" sample.
    response.headers["Cache-Control"]="private, no-store"
    response.headers["X-Evaluation-Generation"]="NONE"
    return build_evaluation_question_plan(findings,target=target)
