"""Warning-only categorization of diagnostic findings; no human accuracy claims."""
from collections import Counter
MAPPING={"citation_grounding":"CITATION_INTEGRITY",
         "source_relevance":"SOURCE_RELEVANCE",
         "cross_module_consistency":"CROSS_MODULE_COVERAGE",
         "legal_uncertainty":"LEGAL_SCOPE_REVIEW"}
LEGAL={"PLATFORM_POLICY_BOUNDARY":"PLATFORM_POLICY_AUTHORITY",
       "FORMAL_OUTCOME_SOCIAL_ONLY":"FORMAL_DECISION_PROVENANCE"}
def classify_answer_audit(quality,ground,cited,kinds):
    findings=[]
    seen=set()
    def add(category,code):
        if (category,code) not in seen and len(findings)<24:
            seen.add((category,code))
            findings.append({"category":category,"code":code,
                             "human_confirmed":False,"status":"CANDIDATE_REQUIRES_REVIEW"})
    if int(ground.get("rejected_unavailable_citations") or 0):
        add("CITATION_INTEGRITY","UNAVAILABLE_DISPLAYED_REFERENCE")
    if int(ground.get("omitted_excess_citation_count") or 0):
        add("CITATION_INTEGRITY","EXCESS_CITATIONS_REMOVED")
    for check in quality.get("checks") or []:
        if check.get("status")=="REVIEW_REQUIRED":
            key=str(check.get("id") or "")[:80]
            add(MAPPING.get(key,"HUMAN_EVIDENCE_VERIFICATION"),key.upper())
    for entry in (quality.get("legal_review_summary") or {}).get("issues") or []:
        code=str(entry.get("code") or "")[:80]
        if code:add(LEGAL.get(code,"LEGAL_SCOPE_REVIEW"),code)
    cited_kinds={kinds[x] for x in cited if x in kinds}
    missing=sorted(set(kinds.values())-cited_kinds)
    for kind in missing:add("CROSS_MODULE_COVERAGE","SELECTED_UNCITED_"+kind)
    return {"schema":"BAWASLU_ANSWER_AUDIT_CANDIDATES_V1611",
            "issue_candidates":findings,
            "issue_category_counts":dict(sorted(Counter(x["category"] for x in findings).items())),
            "issue_candidate_count":len(findings),
            "selected_uncited_source_kinds":missing,
            "observed_model_accuracy":None,"human_confirmed_issue_count":0,
            "human_review_completed":False,"legal_approval_granted":False,
            "status":"AUTOMATED_TRIAGE_PENDING_HUMAN_VERIFICATION"}
