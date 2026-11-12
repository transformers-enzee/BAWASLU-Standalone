"""Conservative source-linked finding assessments for Command Centre.

This endpoint reads the same authorized Inbox-derived finding as the drawer.
It never determines a legal/platform violation, initiates a takedown,
creates a case, or invokes paid AI providers.
"""
from collections import Counter
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
    seen = set()
    ordered = []
    for post in posts:
        ident = (str(post.get("canonical_source_id") or post.get("result_id") or ""),
                 str(post.get("source_url") or ""))
        if ident == ("", ""):
            ident = ("fallback", str(len(ordered)))
        if ident in seen:
            continue
        seen.add(ident)
        ordered.append(post)
    candidates = []
    status_counts = Counter()
    missing_original_text = 0
    missing_original_url = 0
    platforms = {}
    for post in ordered:
        if not str(post.get("message_original") or "").strip():
            missing_original_text += 1
        if not str(post.get("source_url") or "").strip():
            missing_original_url += 1
        outcome = screen_platform_text(post.get("platform"), post.get("message_original"))
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
                "source_url": str(post.get("source_url") or ""),
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
        "record_id": row["record_id"],
        "download_url": row["source_url"],
        "excerpt": row.get("source_excerpt") or "",
        "review_status": row["review_status"],
        "legal_currentness_verified": False,
        "match_method": row.get("match_method") or "KEYWORD",
        "authority_is_currently_in_force": "NOT_VERIFIED",
    } for row in reviewed[:4]]
    return {
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
    return assess_finding(db, permission, finding)
