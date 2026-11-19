"""Human review scoring is opt-in, bounded, redacted and not an AI judge."""
import json
import pytest
from app.assistant_saved_reply_human_packet import build_authorized_saved_reply_review_packet, DIMENSIONS
from app.assistant_human_review_scoring import compile_human_review_scores


def packet():
    task={"thread_id":"123e4567-e89b-12d3-a456-426614174000",
          "answer_message_index":3,"status":"AUDITED",
          "response_quality_triage":{
              "status":"NO_DETERMINISTIC_FLAGS",
              "diagnostics_complete":True}}
    return build_authorized_saved_reply_review_packet({
        "selection_method":"EXPLICIT_USER_SELECTED_REPLIES",
        "requested":1,"results":[task]})


def submission(**changes):
    data={
        "thread_id":"123e4567-e89b-12d3-a456-426614174000",
        "answer_message_index":3,
        "ratings":{name:"PASS" for name in DIMENSIONS},
        "source_access_rechecked":True,
        "original_answer_reviewed":True,
        "independent_review_attested":True,
        "reviewer_free_text":"PRIVATE SOURCE TEXT",
    }
    data.update(changes)
    return data


def test_blank_packet_has_no_scored_outcome():
    result=compile_human_review_scores(packet(),[])
    assert result["complete_self_attested_reviews"]==0
    assert result["review_disposition_counts"]["NOT_SUBMITTED"]==1
    assert result["release_approved"] is False
    assert result["model_calls"]==0


def test_self_attested_complete_review_is_not_legal_signoff():
    result=compile_human_review_scores(packet(),[submission()])
    assert result["complete_self_attested_reviews"]==1
    assert result["review_disposition_counts"]["HUMAN_REPORTED_ALL_DIMENSIONS_PASS"]==1
    assert result["human_attestation_is_independently_verified"] is False
    assert result["model_output_provenance_verified"] is False
    assert result["formal_legal_signoff"] is False
    assert "PRIVATE SOURCE TEXT" not in json.dumps(result)


@pytest.mark.parametrize("bad",[
    {"source_access_rechecked":False},
    {"original_answer_reviewed":False},
    {"independent_review_attested":False},
    {"ratings":{"SOURCE_ID_ACCURACY":"PASS"}},
    {"ratings":{name:"UNKNOWN" for name in DIMENSIONS}},
])
def test_partial_or_unverified_review_does_not_count_as_complete(bad):
    result=compile_human_review_scores(packet(),[submission(**bad)])
    assert result["complete_self_attested_reviews"]==0
    assert result["review_disposition_counts"]["INCOMPLETE_REVIEW"]==1


def test_explicit_failure_is_preserved():
    ratings={name:"PASS" for name in DIMENSIONS}
    ratings["CLAIM_EVIDENCE_SUPPORT"]="FAIL"
    result=compile_human_review_scores(packet(),[
        submission(ratings=ratings)])
    assert result["review_disposition_counts"]["HUMAN_REPORTED_ISSUES"]==1
    assert result["dimension_rating_counts"]["CLAIM_EVIDENCE_SUPPORT"]["FAIL"]==1


def test_not_assessable_is_not_silent_pass():
    ratings={name:"PASS" for name in DIMENSIONS}
    ratings["LEGAL_AND_POLICY_BOUNDARY"]="NOT_ASSESSABLE"
    result=compile_human_review_scores(packet(),[
        submission(ratings=ratings)])
    assert result["review_disposition_counts"]["HUMAN_REPORTED_NOT_ASSESSABLE"]==1
    assert result["release_approved"] is False


def test_duplicate_or_unknown_submission_is_rejected():
    with pytest.raises(ValueError):
        compile_human_review_scores(packet(),[submission(),submission()])
    with pytest.raises(ValueError):
        compile_human_review_scores(packet(),[
            submission(thread_id="00000000-0000-0000-0000-000000000000")])


def test_invalid_review_packet_is_not_accepted():
    with pytest.raises(ValueError):
        compile_human_review_scores({"schema":"UNAUTHORIZED","items":[]},[])
