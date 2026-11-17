"""v148.8 bounded source-linked questions for the independent Assistant review.

This route reuses already permission-scoped, cached Inbox findings; it neither
runs an AI model nor crawls any new posts. Prepared questions are NOT executed.
The result is a diversity-oriented convenience sample, not a random or complete
population sample and never a substitute for officer selection.
"""
from collections import Counter
from urllib.parse import urlsplit
from pydantic import BaseModel, Field
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
    if len(value)>1500 or any(ch.isspace() or ord(ch)<32 or ord(ch)==127 or ch=="\\" for ch in value):
        return ""
    try:
        parts=urlsplit(value)
    except ValueError:
        return ""
    if parts.scheme not in ("https","http") or not parts.netloc or not parts.hostname or parts.username or parts.password:
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



class SavedAnswerAuditRequest(BaseModel):
    """A reviewer-supplied answer; never generated, retained or scored as truth."""
    source_ids:list[str]=Field(min_length=1,max_length=8)
    question:str=Field(min_length=3,max_length=1200)
    answer:str=Field(min_length=3,max_length=10000)


def _authorized_saved_social_rows(findings,identifiers):
    """Fail closed on every requested Social Listening source; no source drift."""
    import re
    if len(set(identifiers))!=len(identifiers) or any(
        re.fullmatch(r"SOCIAL-[1-9][0-9]{0,11}",ref) is None for ref in identifiers
    ):
        raise HTTPException(422,"Distinct valid saved SOCIAL source IDs required")
    wanted=set(identifiers)
    found={}
    for finding in findings or []:
        if not isinstance(finding,dict):
            continue
        for post in finding.get("posts") or []:
            if not isinstance(post,dict):
                continue
            rid=str(post.get("result_id") or "")
            source_id="SOCIAL-"+rid
            if source_id not in wanted or post.get("canonical_source_id")!="social:"+rid:
                continue
            excerpt=str(post.get("message_original") or "").strip()[:5000]
            if not excerpt:
                continue
            # Source inclusion is tied to the permission-scoped saved Inbox.
            # Deduplicate the same original post across campaign links.
            row={"record_id":source_id,"record_type":"SOCIAL_LISTENING",
                 "source_excerpt":excerpt,
                 "sentiment":str(post.get("sentiment") or "UNCLASSIFIED").upper(),
                 "source_verification_status":"SAVED_INBOX_ASSESSMENT_UNVERIFIED"}
            previous=found.get(source_id)
            if previous is None:
                found[source_id]=row
            elif previous["sentiment"]!=row["sentiment"]:
                # Conflicting saved labels must not be quietly treated as fact.
                raise HTTPException(409,"Conflicting saved source versions; review the Inbox record")
    if set(found)!=wanted:
        raise HTTPException(404,"One or more saved sources are unavailable in the authorized Inbox scope")
    return [found[key] for key in identifiers]


def build_saved_answer_audit(findings, request:SavedAnswerAuditRequest):
    """Read-only single-source answer review, without retaining response text."""
    from .assistant_grounding import audit_assistant_answer
    from .assistant_answer_quality import evaluate_answer_quality
    identifiers=request.source_ids
    evidence=_authorized_saved_social_rows(findings,identifiers)
    visible,cited,ground=audit_assistant_answer(
        request.question,evidence,request.answer,profile="SOCIAL_ANALYSIS",language="en")
    qa=evaluate_answer_quality(
        request.question,evidence,visible,cited,
        profile="SOCIAL_ANALYSIS",grounding=ground)
    # Return a deliberately minimal whitelist. Diagnostic internals can
    # contain question tokens; never export raw source text or pasted answers.
    checks=[{"id":c["id"],"status":c["status"],"reason":c["reason"]}
            for c in qa["checks"]]
    from .assistant_audit_issue_register import classify_answer_audit
    triage=classify_answer_audit(qa,ground,cited,{row["record_id"]:row["record_type"] for row in evidence})
    return {
        "schema":"BAWASLU_SAVED_ANSWER_AUDIT_V1608",
        "issue_triage":triage,
        "evaluation_type":"READ_ONLY_DETERMINISTIC_REVIEW_NOT_HUMAN_ACCURACY",
        "sample_scope":"CURRENT_PERMISSION_SCOPED_SAVED_INBOX_WINDOW",
        "source_record_ids":identifiers,
        "source_count":len(evidence),
        "cited_authorized_ids":cited,
        "cited_count":len(cited),
        "rejected_unavailable_citation_count":int(ground.get("rejected_unavailable_citations") or 0),
        "checks":checks,
        "review_required_checks":qa["review_required_checks"],
        "human_accuracy":None,
        "source_truth_verified":False,
        "claimed_answer_is_original_model_output_verified":False,
        "pasted_answer_stored":False,
        "raw_source_text_included":False,
        "legal_signoff_verified":False,
        "formal_client_acceptance_verified":False,
        "database_writes":0,"paid_ai_calls":0,
        "status":"OFFICER_SOURCE_VERIFICATION_PENDING",
    }


@router.post("/saved-answer-audit")
def saved_answer_audit(
    request:SavedAnswerAuditRequest,response:Response,
    user:User=Depends(current_user),db:Session=Depends(get_db)
):
    """Real saved-evidence comparison of an answer pasted by an officer.

    No model calls or source crawler requests; no DB mutations.
    """
    principal=profile(db,user)
    if not has(principal,"view_intelligence"):
        raise HTTPException(403,"Intelligence evaluation requires view permission")
    from .inbox_radar import live_inbox_findings
    try:
        findings,_=live_inbox_findings(db,principal)
    except PermissionError:
        raise HTTPException(403,"Saved Inbox source access denied")
    response.headers["Cache-Control"]="private, no-store"
    response.headers["X-Evaluation-Generation"]="NONE"
    response.headers["X-Acceptance-Status"]="PENDING_HUMAN_REVIEW"
    return build_saved_answer_audit(findings,request)



class MixedAnswerAuditRequest(BaseModel):
    """Bounded source IDs; never allow the client to send its own evidence."""
    source_ids:list[str]=Field(min_length=1,max_length=20)
    question:str=Field(min_length=3,max_length=1200)
    answer:str=Field(min_length=3,max_length=10000)


def build_mixed_answer_audit(evidence,request:MixedAnswerAuditRequest):
    """Pure post-retrieval QA: no claim truth, source leaks or signed approval."""
    from .assistant_grounding import audit_assistant_answer
    from .assistant_answer_quality import evaluate_answer_quality
    from collections import Counter as _Counter

    ids=request.source_ids
    if len(ids)!=len(evidence) or [row["record_id"] for row in evidence]!=ids:
        raise HTTPException(404,"One or more selected evidence records are unavailable")
    kinds={row["record_id"]:row["record_type"] for row in evidence}
    requested_kinds=sorted(set(kinds.values()))
    selected_profile=("CROSS_MODULE_REVIEW" if {"SOCIAL_LISTENING","FORMAL_INTELLIGENCE"}.issubset(set(requested_kinds))
                      else "PDF_GUIDANCE" if "PDF_KNOWLEDGE" in requested_kinds
                      else "SOCIAL_ANALYSIS")
    visible,cited,ground=audit_assistant_answer(
        request.question,evidence,request.answer,profile=selected_profile,language="en",
        citation_limit=20)
    quality=evaluate_answer_quality(request.question,evidence,visible,cited,
                                   profile=selected_profile,grounding=ground)
    issues=(quality.get("legal_review_summary") or {}).get("issues") or []
    from .assistant_audit_issue_register import classify_answer_audit
    triage=classify_answer_audit(quality,ground,cited,kinds)
    return {
        "schema":"BAWASLU_MIXED_ANSWER_AUDIT_V1609",
        "issue_triage":triage,
        "evaluation_type":"AUTHORIZED_SAVED_EVIDENCE_DETERMINISTIC_REVIEW",
        "profile":selected_profile,
        "source_record_ids":list(ids),
        "selected_source_count":len(evidence),
        "audit_citation_reference_limit":20,
        "normal_assistant_citation_reference_limit":12,
        "audit_does_not_rewrite_original_answer":True,
        "selected_source_kinds":dict(_Counter(kinds.values())),
        "cited_authorized_ids":list(cited),
        "cited_source_kinds":dict(_Counter(kinds[x] for x in cited if x in kinds)),
        "missing_cited_source_kinds":sorted(set(requested_kinds)-{kinds[x] for x in cited if x in kinds}),
        "rejected_unavailable_citation_count":int(ground.get("rejected_unavailable_citations") or 0),
        "checks":[{"id":x["id"],"status":x["status"],"reason":x["reason"]}
                  for x in quality["checks"]],
        "review_required_checks":quality["review_required_checks"],
        "legal_review_issue_codes":sorted({str(x["code"]) for x in issues}),
        "legal_review_issue_count":len(issues),
        "human_accuracy":None,"source_truth_verified":False,
        "real_model_provenance_verified":False,
        "legal_applicability_verified":False,"platform_policy_currentness_verified":False,
        "pasted_answer_stored":False,"raw_source_text_included":False,
        "legal_signoff_verified":False,"formal_client_acceptance_verified":False,
        "database_writes":0,"paid_ai_calls":0,
        "status":"OFFICER_FACT_AND_LEGAL_REVIEW_PENDING",
    }


def resolve_mixed_audit_sources(db,principal,request:MixedAnswerAuditRequest):
    """Authorize all exact IDs before evaluating; never substitute sources."""
    import re
    from .domain import list_intelligence
    from .intelligence_assistant import assistant_evidence_record
    from .assistant_knowledge import retrieve_exact_pdf_pages

    ids=request.source_ids
    formats=(r"SOCIAL-[1-9][0-9]{0,11}|INT-[A-Za-z0-9:_-]{1,80}|DOC-[1-9][0-9]{0,11}-P[1-9][0-9]{0,7}")
    if len(set(ids))!=len(ids) or any(re.fullmatch(formats,x) is None for x in ids):
        raise HTTPException(422,"Distinct valid SOCIAL, INT or DOC-page source IDs required")
    wanted_social=[x for x in ids if x.startswith("SOCIAL-")]
    wanted_formal=[x for x in ids if x.startswith("INT-")]
    wanted_pdf=[x for x in ids if x.startswith("DOC-")]
    resolved={}
    # The batch cache belongs only to this authenticated request and principal.
    # Each selected ID still must occur in the authorized source inventory.
    cache=principal.get("_assistant_eval_batch_cache") if isinstance(principal,dict) else None
    if wanted_social:
        from .inbox_radar import live_inbox_findings
        if cache is not None and "scoped_findings" in cache:
            findings=cache["scoped_findings"]
        else:
            try:
                findings,_=live_inbox_findings(db,principal)
            except PermissionError:
                raise HTTPException(403,"Saved Inbox source access denied")
            if cache is not None:
                cache["scoped_findings"]=findings
        rows=_authorized_saved_social_rows(findings,wanted_social)
        resolved.update({row["record_id"]:row for row in rows})
    if wanted_formal:
        # Existing domain reader enforces jurisdiction and the recent-500 window.
        # Out-of-window records are unavailable, never silently substituted.
        if cache is not None and "scoped_formal" in cache:
            formal=cache["scoped_formal"]
        else:
            formal=list_intelligence(db,principal)
            if cache is not None:
                cache["scoped_formal"]=formal
        for item in formal:
            if item.intelligence_id in wanted_formal:
                row=assistant_evidence_record(item)
                if row["record_id"] in resolved:
                    raise HTTPException(409,"Conflicting source identities")
                resolved[row["record_id"]]=row
    if wanted_pdf:
        # Existing exact page method enforces doc visibility, active status and
        # page presence, and returns [] for *any* missing requested page.
        question=" ".join(wanted_pdf)
        pages=retrieve_exact_pdf_pages(db,principal,question,limit=12)
        resolved.update({row["record_id"]:row for row in pages})
    if set(resolved)!=set(ids):
        raise HTTPException(404,"One or more selected evidence records are unavailable")
    return [resolved[key] for key in ids]


@router.post("/mixed-answer-audit")
def mixed_answer_audit(
    request:MixedAnswerAuditRequest,response:Response,
    user:User=Depends(current_user),db:Session=Depends(get_db)
):
    principal=profile(db,user)
    if not has(principal,"view_intelligence"):
        raise HTTPException(403,"Intelligence evaluation requires view permission")
    response.headers["Cache-Control"]="private, no-store"
    response.headers["X-Evaluation-Generation"]="NONE"
    response.headers["X-Acceptance-Status"]="PENDING_HUMAN_REVIEW"
    return build_mixed_answer_audit(
        resolve_mixed_audit_sources(db,principal,request),request)

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

@router.get("/review-packet")
def human_review_packet(
    response:Response,
    target:int=Query(default=24,ge=1,le=30),
    user:User=Depends(current_user),
    db:Session=Depends(get_db)
):
    """Permission-scoped unscored worksheet; no generated model answers."""
    plan=evaluation_questions(response,target=target,user=user,db=db)
    from .assistant_human_review import build_human_review_packet
    return build_human_review_packet(plan)


@router.get("/acceptance-readiness")
def acceptance_readiness(response:Response,
                         target:int=Query(default=24,ge=1,le=30),
                         user:User=Depends(current_user),
                         db:Session=Depends(get_db)):
    """Admin-only count-based acceptance prep, never an approval decision."""
    principal=profile(db,user)
    if not has(principal,"administration") or not has(principal,"view_intelligence"):
        raise HTTPException(403,"Administrator intelligence QA access required")
    from .inbox_radar import live_inbox_findings
    try:
        findings,_=live_inbox_findings(db,principal)
    except PermissionError:
        raise HTTPException(403,"Saved Inbox source access denied")
    from .assistant_human_review import build_human_review_packet
    from .assistant_acceptance_readiness import build_acceptance_readiness
    from .assistant_legal_benchmark import run_legal_signal_benchmark
    plan=build_evaluation_question_plan(findings,target)
    packet=build_human_review_packet(plan)
    result=build_acceptance_readiness(packet,run_legal_signal_benchmark())
    response.headers["Cache-Control"]="private, no-store"
    response.headers["X-Evaluation-Generation"]="NONE"
    return result


@router.get("/acceptance-evidence.csv")
def acceptance_evidence_csv(
    target:int=Query(default=24,ge=1,le=30),
    user:User=Depends(current_user),
    db:Session=Depends(get_db)
):
    """Admin-only CSV handoff of pending requirements, never signed approval."""
    from .assistant_acceptance_evidence import (
        build_evidence_register,render_evidence_register_csv)
    prepared_response=Response()
    readiness=acceptance_readiness(
        response=prepared_response,target=target,user=user,db=db)
    register=build_evidence_register(readiness)
    csv_text=render_evidence_register_csv(register)
    return Response(
        content=csv_text,media_type="text/csv; charset=utf-8",
        headers={"Cache-Control":"private, no-store",
                 "Content-Disposition":"attachment; filename=bawaslu-acceptance-evidence-v1588.csv",
                 "X-Evaluation-Generation":"NONE",
                 "X-Acceptance-Status":"PENDING_HUMAN_REVIEW"})


@router.get("/legal-benchmark")
def legal_benchmark(response:Response,user:User=Depends(current_user),
                    db:Session=Depends(get_db)):
    """Admin-only fixed synthetic quality-gate results, never user records."""
    principal=profile(db,user)
    if not has(principal,"administration") or not has(principal,"view_intelligence"):
        raise HTTPException(403,"Administrator intelligence QA access required")
    response.headers["Cache-Control"]="private, no-store"
    response.headers["X-Evaluation-Generation"]="NONE"
    from .assistant_legal_benchmark import run_legal_signal_benchmark
    return run_legal_signal_benchmark()

