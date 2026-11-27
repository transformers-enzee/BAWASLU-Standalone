"""BAWASLU Gate 1 v188.2: explainable, read-only attention selection.

Needs Attention is NOT equivalent to the legacy information-review status.
Only material quality exceptions, revalidation, and a bounded false-negative
audit sample require officer attention; all other eligible records remain
inspectable through All Information. This module never modifies source data.
"""
import hashlib


def _confidence(raw):
    if raw is None or isinstance(raw, bool):
        return None
    val = str(raw).strip()
    if not val:
        return None
    try:
        parsed = float(val[:-1]) / 100 if val.endswith("%") else float(val)
    except (ValueError, TypeError):
        return None
    return parsed if 0 <= parsed <= 1 else None


def _sampled_exclusion(campaign_id, source_id):
    """Stable 4% safety audit, never a claim that the post is incorrect."""
    digest = hashlib.sha256(f"{campaign_id}:{source_id}:gate1-excluded-1882".encode()).digest()
    return int.from_bytes(digest[:4], "big") % 25 == 0


def attention_reasons(label, state, source, assessment, campaign_id):
    """Classify review exceptions without treating every unchecked item as bad."""
    reasons = []
    action = str(label.get("action") or "")
    relevance = str(label.get("relevance") or "").upper()
    status = str(state.get("information_review_status") or "").upper()
    confidence = _confidence(label.get("relevance_confidence"))
    def add(code, description, kind="EXCEPTION"):
        if code not in {x["code"] for x in reasons}:
            reasons.append({"code":code, "label":description, "kind":kind})
    if status == "REVALIDATION_REQUIRED":
        add("REVALIDATION_REQUIRED", "Saved assessment or correction needs revalidation")
    elif status == "HELD":
        add("HELD_FOR_VERIFICATION", "Previously held information needs verification")
    if action == "VERIFY_UNASSESSED":
        add("UNASSESSED", "Election relevance has not been assessed")
    elif action == "REVIEW_UNCERTAIN":
        add("UNCERTAIN", "Election relevance is uncertain")
    elif action == "REVIEW_UNKNOWN_LABEL":
        add("UNKNOWN_LABEL", "Unrecognized AI relevance assessment")
    if relevance in ("RELEVANT", "HIGHLY_RELEVANT"):
        # Do not flag ordinary optional blanks. A source lacking both usable
        # text and a working provenance reference is a material evidence gap.
        if not str(getattr(source, "text_content", "") or "").strip() and not str(
            getattr(source, "canonical_url", "") or ""
        ).strip():
            add("MISSING_PRIMARY_EVIDENCE", "Both post content and source link are missing")
        if confidence is not None and confidence < 0.55:
            add("LOW_RELEVANCE_CONFIDENCE", "AI election relevance confidence is low")
    elif relevance == "IRRELEVANT":
        if confidence is not None and confidence < 0.70:
            add("LOW_CONFIDENCE_EXCLUSION", "Low-confidence exclusion: check for missed election context")
        elif _sampled_exclusion(campaign_id, getattr(source, "id", 0)):
            add("EXCLUDED_QUALITY_SAMPLE", "Sampled excluded post for false-negative quality check", "SAMPLE")
    # A confident, relevant and sufficiently evidenced post is not a task
    # just because its legacy status happens to be NEEDS_REVIEW.
    return reasons
