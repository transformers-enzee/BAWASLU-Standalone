"""Conservative source-linked finding assessments for Command Centre.

This endpoint reads the same authorized Inbox-derived finding as the drawer.
It never determines a legal/platform violation, initiates a takedown,
creates a case, or invokes paid AI providers.
"""
from collections import Counter
from urllib.parse import urlencode, urlsplit
import re
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .auth import current_user
from .db import get_db
from .models import User
from .access import profile, has
from .platform_policy_screening import screen_platform_text
from .oversight_legal import STEPS
from .assistant_knowledge import retrieve_knowledge
from .finding_source_review import source_review_plan
from .finding_case_progress import summarize_authorized_case_progress
from .finding_review_readiness import build_finding_review_readiness

router = APIRouter(prefix="/api/finding-assessments", tags=["finding-assessments"])
LEGAL_TYPES = {"REGULATION", "SOP", "GUIDANCE"}
POLICY_PRIORITY = {
    "REVIEW_INDICATED": 0, "CONTEXT_REVIEW_REQUIRED": 1,
    "INSUFFICIENT_SOURCE": 2, "POLICY_NOT_CONFIGURED": 3,
    "NO_DIRECT_SIGNAL_IDENTIFIED": 4,
}


_SOURCE_LEGAL_SIGNALS = (
    (r"politik uang|serangan fajar|money politics|vote buying", "politik uang pidana pemilu"),
    (r"daftar pemilih|pdpb|voter register|registrasi pemilih", "pendaftaran pemilih pengawasan"),
    (r"rekapitulasi|penghitungan suara|vote count|vote tally", "penghitungan rekapitulasi suara"),
    (r"netralitas|tidak netral|impartiality", "netralitas penyelenggara pemilu"),
    (r"intimidasi|ancaman pemilih|voter intimidation", "intimidasi pemilih"),
)
def _legal_search_query(finding, posts):
    """Use bounded evidence-derived issue terms; never insert an inferred statute."""
    combined=" ".join(str(p.get("message_original") or "")[:1200] for p in posts[:6])
    evidence=(combined+" "+str(finding.get("title") or "")[:240]).casefold()
    themes=[hint for pattern,hint in _SOURCE_LEGAL_SIGNALS if re.search(pattern,evidence)]
    return "peraturan pengawasan pemilu penanganan pelanggaran bukti " + (
        " ".join(themes[:2]) if themes else "tata cara pengawasan")


def assess_finding(db, permission, finding):
    """Build read-only assessments only from the scoped finding's original posts."""
    posts = finding.get("posts") or []
    # A canonical post can have many campaign links and different saved URLs.
    groups={}
    for index,post in enumerate(posts):
        canonical=str(post.get("canonical_source_id") or "").strip()
        result_id=str(post.get("result_id") or "").strip()
        source_url=str(post.get("source_url") or "").strip()
        identity=(("canonical",canonical) if canonical else
                  ("result",result_id) if result_id else
                  ("url",source_url) if source_url else ("unidentified",str(index)))
        groups.setdefault(identity,[]).append(post)

    def safe_source_url(row):
        raw=str(row.get("source_url") or "").strip()
        try:
            parsed=urlsplit(raw)
            return raw if (parsed.scheme in ("http","https") and
                           parsed.hostname and not parsed.username and not parsed.password) else ""
        except ValueError:
            return ""

    ordered=[]
    linked_variants=[]
    text_conflicts=url_conflicts=platform_conflicts=0
    for variants in groups.values():
        texts={str(v.get("message_original") or "").strip() for v in variants
               if str(v.get("message_original") or "").strip()}
        urls={safe_source_url(v) for v in variants if safe_source_url(v)}
        keys={str(v.get("platform") or "").strip().casefold()
              for v in variants if str(v.get("platform") or "").strip()}
        text_conflicts+=int(len(texts)>1)
        url_conflicts+=int(len(urls)>1)
        platform_conflicts+=int(len(keys)>1)
        chosen=max(variants,key=lambda v:(
            bool(str(v.get("message_original") or "").strip()),
            bool(safe_source_url(v)),len(str(v.get("message_original") or ""))))
        ordered.append(chosen)
        linked_variants.append(variants)
    candidates = []
    source_outcomes=[]
    status_counts = Counter()
    missing_original_text = 0
    missing_original_url = 0
    platforms = {}
    for post, variants in zip(ordered,linked_variants):
        if not str(post.get("message_original") or "").strip():
            missing_original_text += 1
        if not safe_source_url(post):
            missing_original_url += 1
        outcomes=[screen_platform_text(v.get("platform"),v.get("message_original")) for v in variants]
        cues=[row for row in outcomes if row["status"] in ("REVIEW_INDICATED","CONTEXT_REVIEW_REQUIRED")]
        if cues:
            outcome=min(cues,key=lambda row:0 if row["status"]=="CONTEXT_REVIEW_REQUIRED" else 1)
            if len({row["platform_key"] for row in cues})>1:
                outcome={**outcome,"status":"CONTEXT_REVIEW_REQUIRED"}
        else:
            outcome=min(outcomes,key=lambda row:POLICY_PRIORITY.get(row["status"],10))
        source_outcomes.append(outcome)
        status_counts[outcome["status"]] += 1
        if outcome.get("policy_url"):
            platforms[outcome["platform_key"]] = {
                "platform": outcome["platform"],
                "policy_url": outcome["policy_url"],
                "link_checked_on": outcome["policy_url_checked_on"],
                "policy_version_verified": False,
                "policy_scope_note": outcome["policy_scope_note"],
            }
        if outcome["status"] in ("REVIEW_INDICATED", "CONTEXT_REVIEW_REQUIRED"):
            candidates.append({
                "source_id": str(post.get("canonical_source_id") or ""),
                "result_id": str(post.get("result_id") or ""),
                "campaign_id": str(post.get("campaign_id") or ""),
                "source_url": safe_source_url(post),
                "linked_source_variants": len(variants),
                "source_text_conflict": len({str(v.get("message_original") or "").strip()
                    for v in variants if str(v.get("message_original") or "").strip()})>1,
                "platform": outcome["platform"],
                "status": outcome["status"],
                "categories": outcome["review_categories"],
                "category_labels": outcome["category_labels"],
                "recommended_checks": outcome["recommended_checks"],
                "policy_url": outcome["policy_url"],
                "policy_scope_note": outcome["policy_scope_note"],
                "excerpt": str(post.get("message_original") or "")[:260],
            })
    candidates.sort(key=lambda x:(POLICY_PRIORITY.get(x["status"], 10), x["source_id"]))
    flagged = "violations" in (finding.get("players") or [])
    # Retrieval is bounded, permission-scoped and lexical-only: no new paid embeddings.
    # An officer-reviewed PDF still does NOT certify that its rules are current.
    search_query = _legal_search_query(finding, ordered) if flagged else ""
    legal_pages = retrieve_knowledge(
        db, permission, search_query, limit=8, semantic=False,
        reviewed_legal_only=True,
    ) if flagged else []
    # Defense in depth: only officer-reviewed legal types may be displayed,
    # even if a future retrieval implementation returns a mixed set.
    reviewed = [row for row in legal_pages
                if row.get("review_status") == "OFFICER_REVIEWED"
                and row.get("document_type") in LEGAL_TYPES
                and isinstance(row.get("page"), int) and row["page"] > 0]
    references = [{
        "document_id": row["document_id"], "page": row["page"],
        "title": row["title"], "issuer": row.get("issuer") or "",
        "legal_version_label": str(row.get("legal_version_label") or "")[:120],
        "legal_effective_date": str(row.get("legal_effective_date") or "")[:10],
        "legal_election_type": row.get("legal_election_type") if row.get("legal_election_type") in {"PEMILU","PILKADA","BOTH"} else "UNSPECIFIED",
        "record_id": row["record_id"],
        "download_url": row["source_url"],
        "excerpt": row.get("source_excerpt") or "",
        "review_status": row["review_status"],
        "legal_currentness_verified": False,
        "match_method": row.get("match_method") or "KEYWORD",
        "authority_is_currently_in_force": "NOT_VERIFIED",
    } for row in reviewed[:4]]
    assessment = {
        "finding_id": str(finding["id"]),
        "finding_title": str(finding.get("title") or ""),
        "source_count_assessed": len(ordered),
        "source_provenance": {
            "source_of_truth": "AUTHORIZED_SAVED_INTELLIGENCE_INBOX",
            "unique_source_ids": [str(p.get("canonical_source_id") or p.get("result_id") or "")
                                  for p in ordered][:80],
            "duplicate_links_removed": len(posts) - len(ordered),
            "reported_supporting_posts": finding.get("supporting_posts"),
            "source_count_matches_finding": (
                len(ordered) == finding["supporting_posts"]
                if isinstance(finding.get("supporting_posts"), int) else None),
            "missing_original_text": missing_original_text,
            "missing_original_url": missing_original_url,
            "source_text_conflicts": text_conflicts,
            "source_url_conflicts": url_conflicts,
            "source_platform_conflicts": platform_conflicts,
            "original_source_url_validation": "HTTP_OR_HTTPS_ONLY",
            "conflicting_source_metadata_requires_review": bool(
                text_conflicts or url_conflicts or platform_conflicts),
            "all_sources_verification_unresolved": True,
        },
        "assessment_mode": "READ_ONLY_SAVED_EVIDENCE",
        "legal": {
            "status": ("PRELIMINARY_REVIEW_RECOMMENDED" if flagged else
                       "NO_SAVED_POTENTIAL_VIOLATION_FLAG"),
            "possible_violation_confirmed": False,
            "official_legal_verdict": False,
            "statutory_articles_verified": False,
            "legal_currentness_verified": False,
            "approved_reference_pages": references,
            "approved_reference_missing": not bool(references),
            "reviewed_legal_documents_only": True,
            "unreviewed_matches_excluded_before_ranking": True,
            "unreviewed_matched_pages": None,
            "reference_search_basis": "SAVED_SOURCE_THEMES_AND_OFFICER_REVIEWED_PDFS",
            "relevant_statutory_provision_identified": False,
            "recommended_follow_up": STEPS["id"],
            "needs_human_review": True,
            "notice": ("The saved classification is only a suspected signal. "
                       "No applicable statute, article, legal element, deadline or liability "
                       "is established by this assessment. Check the current official rules "
                       "and full evidence with authorized legal officers."),
        },
        "platform_policy": {
            "status": "SOURCE_TEXT_TRIAGE_ONLY",
            "platform_violation_confirmed": False,
            "policy_versions_verified": False,
            "source_count_assessed": len(ordered),
            "official_platform_policy_coverage": len(platforms),
            "unconfigured_platform_source_count": status_counts.get("POLICY_NOT_CONFIGURED", 0),
            "source_text_context_only": True,
            "status_counts": dict(status_counts),
            "potential_review_queue": candidates[:12],
            "queue_is_sample": len(candidates) > 12,
            "policy_references": list(platforms.values()),
            "ordinary_criticism_is_not_violation": True,
            "needs_human_review": True,
            "notice": ("This is source-text screening, not a platform enforcement decision. "
                       "Check full context and current platform terms before reporting."),
        },
        "follow_up": {
            "casework_url": "/inbox?casework=1",
            "officer_decision_required": True,
            "created_assignment": False,
            "takedown_requested": False,
        },
        "paid_provider_called": False,
    }
    assessment["review_readiness"] = build_finding_review_readiness(finding, assessment)
    assessment["source_investigation"] = source_review_plan(ordered,linked_variants,source_outcomes,flagged)
    return assessment




def contextual_casework_links(db, permission, user_id, finding):
    """Read-only contextual handoff to existing, permission-scoped Inbox casework.

    Only saved posts inside the already-authorized finding can be offered.
    Non-numeric source IDs are rejected instead of being interpolated into a
    database query or a clickable case creation URL.
    """
    from .casework import (CaseAssignment, _visible as can_view_case,
                           _authorized_cases_query)
    available=[]
    seen=set()
    for post in finding.get("posts") or []:
        sid=str(post.get("result_id") or "").strip()
        cid=str(post.get("campaign_id") or "").strip()
        if not sid.isascii() or not sid.isdigit() or not cid.isascii() or not cid.isdigit() or int(sid)<1 or int(cid)<1:
            continue
        key=(sid,str(int(cid)))
        if key in seen:continue
        seen.add(key)
        available.append(key)
    # Bounded related-case lookup; the query is also keyed by explicit campaign.
    source_ids=[key[0] for key in available]
    campaign_ids=[int(key[1]) for key in available]
    related=[]
    if source_ids:
        related=_authorized_cases_query(db,permission,user_id).filter(
            CaseAssignment.source_type=="SOCIAL",
            CaseAssignment.source_id.in_(source_ids),
            CaseAssignment.campaign_id.in_(campaign_ids)
        ).order_by(CaseAssignment.updated_at.desc(),CaseAssignment.id.desc()).limit(200).all()
    visible=[case for case in related if can_view_case(case,permission,user_id)
             and (case.source_id,str(case.campaign_id or "")) in seen]
    chosen={}
    for case in visible:
        key=(case.source_id,str(case.campaign_id))
        if key not in chosen or (chosen[key].status=="CLOSED" and case.status!="CLOSED"):
            chosen[key]=case
    # Only up to eight authorized source-linked cases are summarized.
    selected_cases=[chosen[(sid,cid)] for sid,cid in available[:8] if (sid,cid) in chosen]
    progress_by_case=summarize_authorized_case_progress(db,selected_cases)
    can_create=has(permission,"add_intelligence")
    links=[]
    for sid,cid in available[:8]:
        case=chosen.get((sid,cid))
        if case:
            url="/inbox?"+urlencode({"casework":1,"case_id":case.id,"tab":"reports"})
        else:
            url="/inbox?"+urlencode({
                "casework":1,"source_type":"SOCIAL","source_id":sid,
                "campaign_id":cid,"tab":"assignments"})
        links.append({
            "source_type":"SOCIAL","source_id":sid,"campaign_id":cid,
            "existing_case_id":case.id if case else None,
            "existing_case_status":case.status if case else None,
            "existing_case_department":case.target_department if case else "",
            "workflow_progress":progress_by_case.get(case.id) if case else None,
            "can_create_assignment":can_create,
            # No officer is auto-assigned. The link opens the *existing*
            # embedded Inbox workflow which rechecks source permissions.
            "casework_url":url if can_create or case is not None else None,
        })
    return {
        "casework_url":next((item["casework_url"] for item in links
                             if item["casework_url"]),"/inbox?casework=1"),
        "source_actions":links,
        "source_actions_total":len(available),
        "source_actions_sampled":len(available)>len(links),
        "related_case_lookup_sampled":len(related)>=200,
        "visible_existing_case_count":len({c.id for c in visible}),
        "can_create_assignment":can_create,
        "no_assignment_created":True,
        "officer_confirmation_required":True,
        "evidence_must_be_rechecked":True,
    }

@router.get("/{finding_id}")
def finding_assessments(finding_id: str, user: User = Depends(current_user),
                        db: Session = Depends(get_db)):
    permission = profile(db, user)
    if not has(permission, "view_intelligence"):
        raise HTTPException(403, "Intelligence access required")
    # Never fetch a source record directly by ID: use the identical
    # jurisdiction-checked Inbox finding feed used by the Command Centre.
    from .smart_radar import access_findings
    finding = next((item for item in access_findings(db, user)
                    if item.get("id") == finding_id), None)
    if finding is None:
        raise HTTPException(404, "Finding unavailable")
    assessment=assess_finding(db, permission, finding)
    assessment["follow_up"].update(
        contextual_casework_links(db,permission,user.id,finding))
    # Only the casework module may authorize actionable URLs. Never synthesize
    # links from a canonical source ID or a preliminary policy status.
    allowed={(item["source_id"],item["campaign_id"]):item
             for item in assessment["follow_up"].get("source_actions",[])
             if item.get("casework_url")}
    for row in assessment["source_investigation"]["actions"]:
        action=allowed.get((row["result_id"],row["campaign_id"])) or {}
        row["casework_url"]=action.get("casework_url")
        row["workflow_progress"]=action.get("workflow_progress")
    return assessment
