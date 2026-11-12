"""Conservative zero-credit checks on *selected, authorized* Assistant evidence.

These are reproducible warning signals, NOT factual entailment, officer approval,
accuracy scores, or a substitute for a human-scored answer benchmark. No IO.
"""
import re

PASS="PASS"
REVIEW="REVIEW_REQUIRED"
NA="NOT_APPLICABLE"

# Broad question wording, system terms and connectors are not topical entities.
_STOP=set("""
bawaslu assistant intelligence inbox social listening monitoring source sources
saved records record relevant recordnya source_id yang untuk dari dalam dengan pada
menurut apakah jelaskan tentang bagaimana apakah dimana kapan berapa ringkasan
ringkas analisis analisa data ini itu tersebut terkait menurut dibawah berdasarkan
berikan periksa laporan laporanlah pengguna pertanyaan dokumen pdf regulasi hukum
pelanggaran tindak lanjut kebijakan platform media publik pertanyaan terbaru selama
narrative narratives trend trends sentiment sentimen pola pertumbuhan
what where when which about with that this those there show explain discuss please
analysis analytical insights report reports case cases legal policy policies platform
social public concerns news document documents uploaded pdf recent latest most
information evidence source available selected system data summarize summary
compare comparison across from between both each original cite citations
the and for are was have has can should would been into only does did
violations oversight electoral election law laws rules regulatory
""".split())
_WORD=re.compile(r"(?u)\b[\w]{4,}\b")


def _terms(text):
    return set(x.casefold() for x in _WORD.findall(str(text or ""))
               if x.casefold() not in _STOP and not x.isdigit())


def _status(name,status,reason,**details):
    return {"id":name,"status":status,"reason":reason,**details}


def evaluate_answer_quality(question,evidence,answer,cited_ids,
                            profile="SOCIAL_ANALYSIS",grounding=None):
    """Four conservative checks on the post-citation-audit answer.

    Cited sources can still be irrelevant or contain false claims. Token
    overlap is never treated as factual verification or semantic entailment.
    Only records pre-authorized by the Assistant endpoint may be supplied.
    """
    rows={str(x.get("record_id")):x for x in evidence or []
          if isinstance(x,dict) and x.get("record_id")}
    authorized=set(rows)
    cited=list(dict.fromkeys(str(x) for x in cited_ids or []))
    invalid=[x for x in cited if x not in authorized]
    actual=set(re.findall(r"\[((?:INT|SOCIAL)-[A-Za-z0-9:_-]+|DOC-\d+-P\d+)\]",
                          str(answer or "")))
    grounding=grounding or {}
    checks=[]

    if not rows:
        checks.append(_status("citation_grounding",NA,
            "No selected record exists; citation accuracy is not measurable."))
    elif invalid or any(x not in actual for x in cited):
        checks.append(_status("citation_grounding",REVIEW,
            "Citation metadata is not identical to the displayed, authorized answer.",
            invalid_count=len(invalid)))
    elif not cited:
        checks.append(_status("citation_grounding",REVIEW,
            "Selected evidence is not cited within the visible answer."))
    elif grounding.get("rejected_unavailable_citations",0):
        checks.append(_status("citation_grounding",REVIEW,
            "Unselected references were removed; inspect the affected claim.",
            rejected_count=grounding["rejected_unavailable_citations"]))
    else:
        checks.append(_status("citation_grounding",PASS,
            "Displayed citation identifiers match selected authorized records; truth not checked.",
            displayed_count=len(cited)))

    focus=sorted(_terms(question))[:12]
    quoted=[rows[k] for k in cited if k in rows]
    candidates=quoted or list(rows.values())
    excerpt=" ".join(str(v) for row in candidates for v in
        (row.get("title") or "",row.get("source_excerpt") or "",
         row.get("source_publisher") or "",row.get("campaign") or ""))
    tokens=_terms(excerpt)
    missing=[x for x in focus if x not in tokens]
    if not rows or not focus or profile=="PDF_GUIDANCE":
        checks.append(_status("source_relevance",NA,
            "Topical overlap not assessed for a broad, absent or PDF-only source question.",
            focus_terms=focus))
    elif not excerpt.strip():
        checks.append(_status("source_relevance",REVIEW,
            "Selected sources have no text excerpts for a topical overlap check.",
            focus_terms=focus))
    elif missing:
        checks.append(_status("source_relevance",REVIEW,
            "Some question-specific terms do not appear in cited source excerpts; review their relevance, not just keyword overlap.",
            focus_terms=focus,missing_terms=missing))
    else:
        checks.append(_status("source_relevance",PASS,
            "Question-specific terms appear in selected source excerpts; topical matching is lexical only.",
            focus_terms=focus))

    legal_question=bool(grounding.get("legal_question"))
    if not legal_question and profile!="PDF_GUIDANCE":
        checks.append(_status("legal_uncertainty",NA,
            "Legal-document verification was not requested."))
    elif legal_question:
        valid_legal=int(grounding.get("cited_officer_reviewed_legal_pages") or 0)
        missing_articles=grounding.get("legal_article_numbers_not_found_in_cited_pdf") or []
        local_mismatches=grounding.get("legal_article_claim_citation_mismatches") or []
        unattributed=grounding.get("legal_article_claims_without_local_pdf_citation") or []
        unreviewed_cited=int(grounding.get("cited_unreviewed_pdf_pages") or 0)
        enforcement=bool(grounding.get("legal_enforcement_recommendation_needs_officer_review"))
        if enforcement:
            checks.append(_status("legal_uncertainty",REVIEW,
                "Assertive legal enforcement or penalty language requires authorized officer review, irrespective of cited PDF review status. No legal conclusion is verified.",
                enforcement_directive_flags=grounding.get("legal_enforcement_directive_flags") or []))
        elif missing_articles or local_mismatches or unattributed:
            checks.append(_status("legal_uncertainty",REVIEW,
                "A named legal article is missing from cited excerpts, attributed to the wrong page, or lacks a sentence-level PDF reference.",
                unmatched_article_count=len(missing_articles),
                claim_citation_mismatch_count=len(local_mismatches),
                unattributed_article_count=len(unattributed)))
        elif unreviewed_cited:
            checks.append(_status("legal_uncertainty",REVIEW,
                "At least one cited PDF page is not officer-reviewed, even though another cited page may be reviewed.",
                cited_unreviewed_pdf_pages=unreviewed_cited,
                cited_officer_reviewed_legal_pages=valid_legal))
        elif valid_legal==0:
            checks.append(_status("legal_uncertainty",REVIEW,
                "No cited officer-reviewed legal page; legal currentness and applicable law require official verification.",
                reviewed_legal_pages=0))
        elif grounding.get("legal_currentness_verified") is not False:
            checks.append(_status("legal_uncertainty",REVIEW,
                "Legal-currentness status must remain unverified until checked externally."))
        else:
            checks.append(_status("legal_uncertainty",PASS,
                "An officer-reviewed legal page is cited, with legal currentness still explicitly unverified.",
                reviewed_legal_pages=valid_legal))
    else:
        if int(grounding.get("selected_unreviewed_pdf_pages") or 0):
            checks.append(_status("legal_uncertainty",REVIEW,
                "An unreviewed PDF was selected; it cannot be presented as official authority."))
        else:
            checks.append(_status("legal_uncertainty",NA,
                "No legal question or unreviewed reference requires a legal-currentness check."))

    formal={x for x in rows if rows[x].get("record_type")=="FORMAL_INTELLIGENCE" or x.startswith("INT-")}
    social={x for x in rows if rows[x].get("record_type")=="SOCIAL_LISTENING" or x.startswith("SOCIAL-")}
    # Evidence can arrive with repeated source IDs: do not count such rows as
    # independent posts, nor quietly accept conflicting saved classifications.
    duplicates={}
    for row in evidence or []:
        if not isinstance(row,dict):continue
        identifier=str(row.get("record_id") or "")
        if identifier.startswith("SOCIAL-"):
            duplicates.setdefault(identifier,[]).append(str(row.get("sentiment") or "UNKNOWN").upper())
    conflicts=[sid for sid,values in duplicates.items() if len(set(values))>1]
    if profile=="CROSS_MODULE_REVIEW":
        if conflicts or not formal or not social:
            checks.append(_status("cross_module_consistency",REVIEW,
                "Both source types are needed for a two-module comparison; conflicting duplicate social classifications require review.",
                formal_selected=len(formal),social_selected=len(social),
                duplicate_sentiment_conflicts=len(conflicts)))
        else:
            checks.append(_status("cross_module_consistency",PASS,
                "Formal and social evidence both selected; consistency of factual claims still requires officer review.",
                formal_selected=len(formal),social_selected=len(social),
                duplicate_sentiment_conflicts=0))
    elif conflicts:
        checks.append(_status("cross_module_consistency",REVIEW,
            "The same selected social source has conflicting sentiment labels.",
            duplicate_sentiment_conflicts=len(conflicts)))
    else:
        checks.append(_status("cross_module_consistency",NA,
            "No cross-module comparison or conflicting saved-source classification in this answer."))

    needs=[x["id"] for x in checks if x["status"]==REVIEW]
    return {
        "framework":"ASSISTANT_ANSWER_READINESS_V1484",
        "evaluation_type":"DETERMINISTIC_HEURISTICS_NOT_HUMAN_ACCURACY",
        "checks":checks,"passed_checks":sum(x["status"]==PASS for x in checks),
        "review_required_checks":len(needs),
        "not_applicable_checks":sum(x["status"]==NA for x in checks),
        "needs_review":needs,
        "human_accuracy":None,"human_gold_answers_evaluated":0,
        "claim_truth_verified":False,"semantic_entailment_verified":False,
        "legal_currentness_verified":False,"legal_verdict_confirmed":False,
        "user_jurisdiction_verified_by_this_check":False,
        "no_paid_provider_called_by_this_check":True,
        "human_review_required":True,
    }
