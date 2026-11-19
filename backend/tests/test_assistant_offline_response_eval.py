"""Offline AI-response triage report contracts. No network or paid model calls."""
import json
import pytest
from app.assistant_offline_response_eval import (
    load_bundled,evaluate_batch,evaluate_record,main,
)


def test_bundled_triage_fixtures_cover_44_multisource_answers():
    cases=load_bundled()
    assert len(cases)==44
    report=evaluate_batch(cases)
    assert report["case_count"]==44
    assert report["status_counts"]=={
        "PASS_NARROW_LEXICAL_ONLY":11,
        "REVIEW_REQUIRED":33,
    }
    assert report["model_calls"]==0
    assert report["accuracy_score"] is None
    assert report["human_gold_scoring_completed"] is False
    assert report["semantic_entailment_verified"] is False
    assert all(row["human_review_required"] for row in report["results"])


def test_report_never_exposes_answers_or_source_passages():
    case=load_bundled()[0]
    report=evaluate_record(case)
    serialized=json.dumps(report)
    assert case["candidate_answer"] not in serialized
    assert case["documents"][0]["source_excerpt"] not in serialized
    assert "candidate_answer" not in report
    assert "authorized_evidence" not in report
    assert report["model_answer_accuracy"] is None


def test_rejected_batch_duplicate_ids():
    case=load_bundled()[0]
    with pytest.raises(ValueError,match="unique"):
        evaluate_batch([case,case])


@pytest.mark.parametrize("field,value",[
    ("candidate_answer","x"*30001),
    ("requirements",[]),
    ("candidate_citation_ids",None),
    ("documents",[]),
])
def test_input_rejects_invalid_or_unbounded_records(field,value):
    case=load_bundled()[0].copy()
    case[field]=value
    with pytest.raises(ValueError):
        evaluate_batch([case])


def test_all_bundled_negative_cases_stay_review_required():
    for case in load_bundled():
        result=evaluate_record(case)
        expected=case["expected_status"]
        assert result["status"]==expected
        if expected=="REVIEW_REQUIRED":
            assert case["expected_issue"] in result["review_reasons"]


def test_cli_emits_redacted_json_report(tmp_path):
    path=tmp_path/"qa-output.json"
    assert main(["--output",str(path)])==0
    content=path.read_text(encoding="utf-8")
    report=json.loads(content)
    assert report["case_count"]==44
    assert report["model_calls"]==0
    assert "source_excerpt" not in content
    assert "candidate_answer" not in content
