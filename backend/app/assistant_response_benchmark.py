"""Conservative lexical rubric for an offline answer benchmark.

This is not a factual accuracy score: a required phrase can appear in a false
sentence, a negation, or a quotation. Never interpret lexical coverage as
semantic entailment, official legal validation, or model performance.
"""
import re


def check_required_answer_points(answer, points):
    normalized=lambda value: re.sub(r"\s+", " ", str(value or "")).strip().casefold()
    body=normalized(answer)
    required=[normalized(point) for point in points or [] if normalized(point)]
    missing=[point for point in required if point not in body]
    return {
        "status": "NEEDS_REVIEW" if missing else "PASS_LEXICAL_ONLY",
        "required_point_count": len(required),
        "missing_points": missing,
        "semantic_entailment_verified": False,
        "accuracy_score": None,
        "human_scoring_completed": False,
    }
