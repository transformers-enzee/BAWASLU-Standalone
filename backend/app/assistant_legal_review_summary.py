"""Priority-ordered officer review consolidation for existing legal AI checks.

Only selected/displayed source IDs are included. This is offline triage,
not approval, legal severity, source truth, or a factual accuracy estimate.
"""
import re

_ID=re.compile(r"^(?:DOC-[0-9]+-P[0-9]+|(?:INT|SOCIAL)-[A-Za-z0-9:_-]+)$")
_PRIORITIES=("P1","P2","P3")
_CODES={
    "LEGAL_OUTCOME_OR_ACTION","ELIGIBLE_LEGAL_SOURCE_MISSING","CITATION_INTEGRITY",
    "ARTICLE_OR_CLAIM_ATTRIBUTION","PASSAGE_POLARITY","NUMERIC_OR_DATE",
    "ELECTION_SCOPE","DOCUMENT_REVIEW_PENDING","SOURCE_RELEVANCE",
    "VERSION_OR_EFFECTIVE_DATE",
}

def build_legal_review_summary(evidence,cited_ids,grounding,quality):
    base={"schema":"BAWASLU_LEGAL_REVIEW_SUMMARY_V1529",
          "applicable":bool((grounding or {}).get("legal_question")),
          "status":"OFFICER_REVIEW_REQUIRED",
          "priority_is_legal_severity":False,
          "automated_legal_approval":False,
          "source_truth_verified":False,
          "legal_applicability_verified":False,
          "legal_currentness_verified":False,
          "semantic_entailment_verified":False,
          "human_review_required":True,
          "no_paid_provider_called":True,
          "issues":[],"issue_count":0,"priority_counts":{"P1":0,"P2":0,"P3":0}}
    if not base["applicable"]:
        return {**base,"status":"NOT_APPLICABLE","human_review_required":False}
    g=grounding or {}
    selected={str(row["record_id"]) for row in evidence or []
              if isinstance(row,dict) and row.get("record_id")}
    cited=list(dict.fromkeys(str(x) for x in cited_ids or []
                             if isinstance(x,str) and _ID.fullmatch(x)
                             and x in selected))
    allowed=set(cited)
    docs={str(row["record_id"]):row for row in evidence or []
          if isinstance(row,dict) and str(row.get("record_id")) in allowed}
    legal=[ref for ref in cited if docs[ref].get("record_type")=="PDF_KNOWLEDGE"
           and docs[ref].get("document_type") in {"REGULATION","SOP","GUIDANCE"}]
    issues=[]
    def add(code,priority,refs=(),signals=1,detail_kinds=()):
        if code not in _CODES or priority not in _PRIORITIES:
            return
        valid=list(dict.fromkeys(ref for ref in refs if ref in allowed))[:12]
        issues.append({"code":code,"priority":priority,"source_ids":valid,
                       "signal_count":min(max(int(signals or 1),1),99),
                       "detail_kinds":[k for k in detail_kinds
                                       if k in {"DATE","QUANTITY","ARTICLE","CLAIM"}][:4],
                       "officer_review_required":True})
    if g.get("legal_categorical_outcome_needs_officer_review") or g.get("legal_enforcement_recommendation_needs_officer_review"):
        add("LEGAL_OUTCOME_OR_ACTION","P1",legal,
            int(bool(g.get("legal_categorical_outcome_needs_officer_review")))+
            int(bool(g.get("legal_enforcement_recommendation_needs_officer_review"))))
    if not legal:
        add("ELIGIBLE_LEGAL_SOURCE_MISSING","P1")
    if g.get("rejected_unavailable_citations") or g.get("omitted_excess_citation_count"):
        add("CITATION_INTEGRITY","P1",cited,
            (g.get("rejected_unavailable_citations") or 0)+
            (g.get("omitted_excess_citation_count") or 0))
    article_issues=(len(g.get("legal_article_numbers_not_found_in_cited_pdf") or [])+
                    len(g.get("legal_article_claim_citation_mismatches") or [])+
                    len(g.get("legal_article_claims_without_local_pdf_citation") or []))
    prescriptive=int(g.get("prescriptive_legal_claims_without_local_legal_citation_count") or 0)
    if article_issues or prescriptive:
        add("ARTICLE_OR_CLAIM_ATTRIBUTION","P1",legal,article_issues+prescriptive,
            (["ARTICLE"] if article_issues else [])+(["CLAIM"] if prescriptive else []))
    consistency=(quality or {}).get("legal_claim_passage_consistency") or {}
    if consistency.get("possible_reversal_count"):
        refs=[x.get("cited_page_id") for x in consistency.get("possible_reversals") or []]
        add("PASSAGE_POLARITY","P1",refs,consistency["possible_reversal_count"],["CLAIM"])
    numeric=(quality or {}).get("legal_numeric_claim_source_alignment") or {}
    if numeric.get("unsupported_detail_count"):
        details=numeric.get("unsupported_details") or []
        add("NUMERIC_OR_DATE","P2",
            [r for issue in details for r in issue.get("cited_page_ids",[])],
            numeric["unsupported_detail_count"],
            list(dict.fromkeys(x.get("kind") for x in details)))
    scope=[x for x in g.get("legal_election_type_scope_review_ids") or [] if x in allowed]
    if scope:
        add("ELECTION_SCOPE","P2",scope,len(scope))
    unreviewed=[x for x in legal if docs[x].get("review_status")!="OFFICER_REVIEWED"]
    if unreviewed:
        add("DOCUMENT_REVIEW_PENDING","P2",unreviewed,len(unreviewed))
    align=(quality or {}).get("legal_source_alignment") or {}
    if legal and not scope and align.get("status")=="REVIEW_REQUIRED":
        add("SOURCE_RELEVANCE","P2",legal)
    missing_meta=list(dict.fromkeys(
        [x for x in g.get("legal_document_version_missing_ids") or [] if x in legal]+
        [x for x in g.get("legal_document_effective_date_missing_ids") or [] if x in legal]))
    if missing_meta:
        add("VERSION_OR_EFFECTIVE_DATE","P3",missing_meta,len(missing_meta))
    issues.sort(key=lambda x:(_PRIORITIES.index(x["priority"]),x["code"]))
    counts={p:sum(x["priority"]==p for x in issues) for p in _PRIORITIES}
    return {**base,"issues":issues[:10],"issue_count":len(issues),
            "priority_counts":counts,"cited_legal_pages":len(legal),
            "selected_source_count":len(selected),
            "displayed_source_count":len(cited),
            "status":"OFFICER_REVIEW_REQUIRED"}
