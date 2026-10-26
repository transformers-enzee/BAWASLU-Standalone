"""No-credit Shahrin reference diagnostics, separate from the paid QA runner.

This is deliberately an audit, NOT a classifier. It never reads any sealed
holdout labels and never calls a model provider.
"""
from collections import Counter
from sqlalchemy import text

AUDIT_SQL=text("""
SELECT c.qa_id,s.message_original,s.source_hash,s.source_url,
       h.category AS shahrin_category
FROM pilot_smart_radar.qa_prompt_cohort c
JOIN pilot_smart_radar.qa_source_posts s ON s.qa_id=c.qa_id
JOIN pilot_smart_radar.qa_imported_human_categories h
  ON h.original_excel_row=s.original_excel_row AND h.source_url=s.source_url
WHERE c.cohort='development' ORDER BY c.qa_id
""")

CANDIDATES_SQL=text("""
WITH target AS (
 SELECT pilot_smart_radar.qa_reference_tokens(message_original) tokens,
        source_url,source_hash
 FROM pilot_smart_radar.qa_source_posts WHERE qa_id=:qa_id
)
SELECT e.qa_id,e.shahrin_category,
       pilot_smart_radar.qa_reference_jaccard(e.tokens,t.tokens) similarity
FROM pilot_smart_radar.qa_shahrin_exemplars e CROSS JOIN target t
WHERE e.eligible AND e.source_hash<>t.source_hash
AND e.source_url<>t.source_url
ORDER BY similarity DESC,e.qa_id LIMIT 5
""")

def reference_diagnostic(rows, candidates_by_id):
    """Compare lexical reference relevance against held-out development labels.

    This NEVER supplies a target label to the model. Labels are used only after
    assembling candidate rankings, for offline evaluation. No retraining.
    """
    items=[]
    for target in rows:
        ranked=candidates_by_id.get(target["qa_id"], [])
        best=ranked[0] if ranked else None
        top_category=best["shahrin_category"] if best else None
        score=float(best["similarity"]) if best else 0.0
        competition=(next((x for x in ranked[1:]
            if x["shahrin_category"]!=top_category),None) if best else None)
        margin=(score-float(competition["similarity"])
                if competition else None)
        items.append({
            "qa_id":target["qa_id"],
            "reference_category":top_category,
            "reference_similarity":round(score,4),
            "category_margin":round(margin,4) if margin is not None else None,
            "reference_agrees":top_category==target["shahrin_category"],
            "candidate_count":len(ranked),
            "nearest_example_id":best["qa_id"] if best else None,
        })
    n=len(items)
    return {
        "evaluated_development_posts":n,
        "nearest_reference_agreement":sum(x["reference_agrees"] for x in items),
        "nearest_reference_rate":round(sum(x["reference_agrees"] for x in items)/n,4) if n else None,
        "weak_or_conflicting":sum(x["reference_similarity"]<.25
             or (x["category_margin"] is not None and x["category_margin"]<.08)
             for x in items),
        "items":items,
        "warning":"Lexical retrieval diagnostic only; not measured AI classification accuracy",
    }

def audit_development_references(db):
    rows=[dict(r) for r in db.execute(AUDIT_SQL).mappings().all()]
    candidates={}
    for item in rows:
        candidates[item["qa_id"]]=[dict(r) for r in db.execute(
            CANDIDATES_SQL,{"qa_id":item["qa_id"]}).mappings().all()]
    return reference_diagnostic(rows,candidates)
