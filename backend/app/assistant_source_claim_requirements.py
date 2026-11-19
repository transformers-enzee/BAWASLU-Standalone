"""Offline claim-level reference requirement triage for synthetic QA.

Narrowly detects missing expected *quoted/source-matched* phrasing, explicit
Indonesian obligation polarity reversal, and missing local source citations.
Does NOT verify semantic entailment or accuracy of arbitrary generated prose.
"""
import re

_CITE = re.compile(r"\[(DOC-\d+-P\d+|INT-[A-Za-z0-9:_-]+|SOCIAL-[A-Za-z0-9:_-]+)\]")
_SPANS = re.compile(r"(?<=[.!?;])\s+|\n+")
_SPACE = re.compile(r"\s+")
_NEGATION = re.compile(r"\b(?:tidak|bukan|belum)\s+")


def _norm(value):
    return _SPACE.sub(" ", str(value or "")).strip().casefold()


def check_source_claim_requirements(answer, requirements, evidence, cited_ids):
    """Return warnings for narrow explicit source-anchored requirements.

    requirements: list of {source_id, anchor, expected_polarity?}
    expected_polarity optional: POSITIVE or NEGATIVE, applying only to
    literal negation directly preceding the anchor.
    """
    by_id = {str(x.get("record_id")): x for x in evidence or []
             if isinstance(x, dict) and x.get("record_id")}
    metadata = set(str(x) for x in cited_ids or [])
    spans = _SPANS.split(str(answer or ""))
    issues = []
    for index, requirement in enumerate(requirements or []):
        ref = str(requirement.get("source_id") or "")
        anchor = _norm(requirement.get("anchor"))
        expected = requirement.get("expected_polarity", "POSITIVE")
        if expected not in {"POSITIVE", "NEGATIVE"} or not ref or not anchor:
            issues.append({"requirement_index": index, "reason": "INVALID_REQUIREMENT"})
            continue
        source = by_id.get(ref)
        if source is None or anchor not in _norm(source.get("source_excerpt")):
            issues.append({"requirement_index": index, "reason": "ANCHOR_NOT_IN_SELECTED_SOURCE",
                           "source_id": ref})
            continue
        candidates = []
        for i, span in enumerate(spans):
            norm_span = _norm(_CITE.sub("", span))
            if anchor not in norm_span:
                continue
            # The required text must belong to a locally cited claim.
            refs = _CITE.findall(span)
            if not refs and i + 1 < len(spans):
                next_span = spans[i + 1].strip()
                maybe = _CITE.findall(next_span)
                if maybe and not _CITE.sub("", next_span).strip():
                    refs = maybe
            if ref not in refs or ref not in metadata:
                continue
            # Evaluate only immediately preceding negation of the exact
            # anchor; more complex claims are explicitly out of scope.
            matches = re.finditer(r"(?<!\\w)" + re.escape(anchor) + r"(?!\\w)", norm_span)
            for match in matches:
                before = norm_span[:match.start()]
                negated = bool(re.search(r"\\b(?:tidak|bukan|belum)\\s+$", before))
                candidates.append("NEGATIVE" if negated else "POSITIVE")
        if not candidates:
            issues.append({"requirement_index": index,
                           "reason": "NO_LOCALLY_CITED_ANCHOR", "source_id": ref})
        elif expected not in candidates:
            issues.append({"requirement_index": index,
                           "reason": "EXPLICIT_POLARITY_REVERSAL", "source_id": ref})
        elif len(set(candidates)) > 1:
            issues.append({"requirement_index": index,
                           "reason": "CONFLICTING_LOCAL_CLAIMS", "source_id": ref})
    return {
        "status": "REVIEW_REQUIRED" if issues else "PASS_NARROW_LEXICAL_ONLY",
        "requirement_count": len(requirements or []),
        "review_items": issues,
        "source_truth_verified": False,
        "semantic_entailment_verified": False,
        "model_answer_accuracy": None,
        "human_accuracy": None,
        "model_calls": 0,
    }
