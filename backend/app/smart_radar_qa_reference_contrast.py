"""V3: conservative contrast-preserving Shahrin reference retrieval.

Reuses the independently eligible v1 SQL reference candidates. Preserves
opposite-label examples when they represent distinct framing, instead of
blanket rejection based on a category tie. No target human labels are read.
"""
from .smart_radar_qa_references import reference_examples_for_record

REFERENCE_REVISION_V3="shahrin-ref-v3"

def select_reference_v3(db, record, exemplars):
    """Return (examples, reason). No paid AI calls or target label access."""
    candidates=reference_examples_for_record(db,record,exemplars)
    if not candidates:
        return [],"no_eligible_candidate"
    # Opposing analyst categories are *contrastive evidence*, not a vote.
    # Keep at most two to bound token spending. The legacy selector already
    # ensures independent URLs/hashes, eligible cohort and diverse labels.
    if len(candidates)>1:
        return candidates[:2],"contrastive_categories"
    return candidates[:1],"single_reference_not_decisive"
