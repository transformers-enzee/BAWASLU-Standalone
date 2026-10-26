"""Evidence-quality selection for Shahrin reference examples (offline, no AI calls).

v2 is intentionally conservative: reject weak, conflicting or ambiguous
lexical neighbours. This improves reference reliability, not proven accuracy.
"""
from sqlalchemy import text

REFERENCE_REVISION_V2="shahrin-ref-v2"
CANDIDATE_SQL=text("""
WITH target AS (
  SELECT pilot_smart_radar.qa_reference_tokens(message_original) AS tokens,
         source_hash,source_url
  FROM pilot_smart_radar.qa_source_posts WHERE qa_id=:qa_id
), scored AS (
  SELECT e.qa_id,e.shahrin_category,e.message_original,e.source_url,
    pilot_smart_radar.qa_reference_jaccard(e.tokens,t.tokens) AS similarity
  FROM pilot_smart_radar.qa_shahrin_exemplars e CROSS JOIN target t
  WHERE e.eligible AND e.source_hash<>t.source_hash AND e.source_url<>t.source_url
)
SELECT qa_id,shahrin_category,left(message_original,900) AS excerpt,similarity
FROM scored WHERE similarity>=0.18 AND similarity<0.65
ORDER BY similarity DESC, qa_id LIMIT 20
""")

def select_reference_v2(db,record,exemplars):
    """Return (examples, diagnostic) using ONLY exemplar labels.

    Never peek at target label. If top categories have near-equal evidence,
    omit all examples rather than feeding conflicting guidance to the model.
    """
    if record.get("cohort")!="development":
        raise ValueError("Reference retrieval allowed for development only")
    allowed={x["qa_id"]:x for x in exemplars if x.get("cohort")=="exemplar"}
    rows=db.execute(CANDIDATE_SQL,{"qa_id":record["qa_id"]}).mappings().all()
    valid=[]
    for x in rows:
        ref=allowed.get(x["qa_id"])
        sim=x["similarity"]
        if (not ref or ref.get("gold_category")!=x["shahrin_category"]
            or ref.get("source_hash")==record.get("source_hash")
            or ref.get("source_url")==record.get("source_url")
            or not isinstance(sim,(int,float)) or isinstance(sim,bool)
            or not 0.18<=sim<0.65 or not x["excerpt"]):
            continue
        valid.append(x)
    if not valid:
        return [],"no_reliable_reference"
    top=valid[0]
    # A single somewhat similar exemplar is not enough to anchor a
    # new category decision; require at least 0.25 similarity.
    if top["similarity"]<0.25:
        return [],"weak_similarity"
    # Near-tied opposite categories indicate ambiguous lexical neighbours.
    nearest_opposite=next((x for x in valid
        if x["shahrin_category"]!=top["shahrin_category"]),None)
    if nearest_opposite and top["similarity"]-nearest_opposite["similarity"]<0.08:
        return [],"category_conflict"
    # Never use a reference from a different category if it does not offer
    # meaningful contrast; cap at 2 to conserve input tokens.
    selected=[top]
    second=next((x for x in valid[1:] if
        x["shahrin_category"]==top["shahrin_category"] and
        x["similarity"]>=0.20),None)
    if second:
        selected.append(second)
    result=[{"qa_id":x["qa_id"],"human_primary_category":x["shahrin_category"],
      "source_text":x["excerpt"],"similarity":round(x["similarity"],4)}
      for x in selected]
    return result,"qualified"
