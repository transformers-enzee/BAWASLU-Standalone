"""v151.6: legal review status is not legal approval."""
from app.assistant_grounding import audit_assistant_answer
from app.assistant_answer_quality import evaluate_answer_quality

def item(ref, kind, status):
    return {"record_id":ref,"record_type":"PDF_KNOWLEDGE","document_type":kind,
            "review_status":status,"source_excerpt":"Pasal 21 appears in this page."}

def run(items, answer):
    output,cited,ground=audit_assistant_answer("Which law applies?",items,answer,
                                                profile="PDF_GUIDANCE",language="en")
    quality=evaluate_answer_quality("Which law applies?",items,output,cited,
                                    profile="PDF_GUIDANCE",grounding=ground)
    return ground,quality

def legal_check(quality):
    return next(c for c in quality["checks"] if c["id"]=="legal_uncertainty")

def test_unreviewed_regulation_has_explicit_pending_state():
    meta,quality=run([item("DOC-1-P1","REGULATION","UNREVIEWED")],"Pasal 21 [DOC-1-P1].")
    assert meta["legal_source_review_state"]=="REVIEW_PENDING"
    assert meta["cited_unreviewed_legal_pages"]==1
    assert legal_check(quality)["status"]=="REVIEW_REQUIRED"
    assert meta["legal_source_review_is_approval"] is False

def test_mixed_legal_pages_do_not_hide_unreviewed_source():
    meta,quality=run([item("DOC-1-P1","SOP","OFFICER_REVIEWED"),
                      item("DOC-2-P1","REGULATION","UNREVIEWED")],
                     "Pasal 21 [DOC-1-P1] [DOC-2-P1].")
    assert meta["cited_reviewed_legal_pages"]==1
    assert meta["cited_unreviewed_legal_pages"]==1
    assert meta["legal_source_review_state"]=="REVIEW_PENDING"
    assert legal_check(quality)["status"]=="REVIEW_REQUIRED"

def test_all_reviewed_still_never_certifies_legal_currentness():
    meta,quality=run([item("DOC-1-P1","REGULATION","OFFICER_REVIEWED")],
                     "Pasal 21 [DOC-1-P1].")
    assert meta["legal_source_review_state"]=="OFFICER_REVIEWED_NOT_LEGALLY_VERIFIED"
    assert meta["legal_currentness_verified"] is False
    assert meta["legal_source_review_is_approval"] is False

def test_report_is_not_an_eligible_legal_reference():
    meta,quality=run([item("DOC-1-P1","REPORT","OFFICER_REVIEWED")],
                     "Pasal 21 [DOC-1-P1].")
    assert meta["legal_source_review_state"]=="NO_ELIGIBLE_LEGAL_REFERENCE"
    assert meta["cited_reviewed_legal_pages"]==0
    assert meta["cited_unreviewed_legal_pages"]==0
