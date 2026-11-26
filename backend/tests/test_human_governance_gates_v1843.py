"""Offline regression for the BAWASLU v184.3 three-gate foundation."""
from app.human_governance_gates import (
    information_gate, insight_publication_gate, learning_release_gate, resolve_reviewed_field
)

def source(**changes):
    value={"source_id":"SOCIAL-1","original_text":"Diskusi pemilu dan kandidat",
           "review_status":"ai_assessed", "relevance":"relevant"}
    value.update(changes)
    return value

def finding(**changes):
    value={"state":"approved","approver_id":"officer-1","approved_revision":"r2",
           "finding_id":"F-1","evidence_refs":["SOCIAL-1"],"analysis_scope":"2026-11-01/2026-11-20",
           "source_revision_current":True,"claim_status":"preliminary"}
    value.update(changes)
    return value

def release(**changes):
    value={"release_id":"m-1","administrator_id":"admin-1","dataset_reviewed":True,
           "held_out_evaluation_passed":True,"regression_passed":True,
           "security_review_passed":True,"version_pinned":True}
    value.update(changes)
    return value

def test_general_election_discussion_enters_inbox_without_violation_flag():
    r=information_gate(source())
    assert r["inbox_visible"] and not r["human_verified"]
    assert not r["eligible_for_approved_claims"]
    assert r["requires_review"]  # sampling eligibility, not an automatic block

def test_high_impact_requires_verified_officer():
    r=information_gate(source(impact_category="consequential_allegation"))
    assert "HIGH_IMPACT_REQUIRES_OFFICER" in r["review_blockers"]
    reviewed=information_gate(source(review_status="officer_verified",reviewer_id="u1",
                                      impact_category="consequential_allegation"))
    assert reviewed["eligible_for_approved_claims"]

def test_missing_source_and_false_exclusion_cannot_be_silent():
    r=information_gate(source(source_id="",original_text=""))
    assert not r["inbox_visible"]
    assert "SOURCE_ID_REQUIRED" in r["review_blockers"]
    assert "ORIGINAL_SOURCE_REQUIRED" in r["review_blockers"]
    assert "IRRELEVANCE_REQUIRES_EXCLUSION_QA" in information_gate(
        source(relevance="irrelevant"))["review_blockers"]

def test_unreviewed_and_stale_insights_fail_closed():
    for data, code in [
        (finding(state="draft"), "INSIGHT_NOT_APPROVED"),
        (finding(source_revision_current=False), "SOURCE_REVISION_STALE_OR_UNKNOWN"),
        (finding(evidence_refs=[]), "TRACEABLE_EVIDENCE_REQUIRED"),
        (finding(approver_id=""), "APPROVER_REQUIRED"),
        (finding(claim_status="verified"), "VERIFIED_CLAIM_WITHOUT_VERIFICATION"),
        (finding(contains_high_impact_claims=True), "HIGH_IMPACT_REVIEW_REQUIRED"),
    ]:
        result=insight_publication_gate(data)
        assert not result["publish_allowed"] and code in result["review_blockers"]
    assert insight_publication_gate(finding())["publish_allowed"]

def test_learning_requires_all_separate_approvals():
    assert learning_release_gate(release())["release_allowed"]
    for field in ("administrator_id","dataset_reviewed","held_out_evaluation_passed",
                  "regression_passed","security_review_passed","version_pinned"):
        invalid="" if field=="administrator_id" else False
        assert not learning_release_gate(release(**{field:invalid}))["release_allowed"]

def test_approved_correction_wins_without_destroying_ai_provenance():
    assert resolve_reviewed_field("NEUTRAL","MIXED","approved")=="MIXED"
    assert resolve_reviewed_field("NEUTRAL","MIXED","proposed")=="NEUTRAL"
    assert resolve_reviewed_field("NEUTRAL",None,"approved")=="NEUTRAL"
