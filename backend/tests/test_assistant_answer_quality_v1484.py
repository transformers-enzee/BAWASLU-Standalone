"""v148.4: 16 synthetic adversarial cases; offline QA, no paid model use.

This measures whether deterministic safeguards detect deliberately injected
problems, NOT how often model answers match real human ground truth.
"""
import json
from pathlib import Path
import pytest

from app.assistant_grounding import audit_assistant_answer
from app.assistant_answer_quality import (
    evaluate_answer_quality,PASS,REVIEW,NA
)

_PATH=Path(__file__).parent/"fixtures"/"assistant_answer_readiness_v1484.json"
DATA=json.loads(_PATH.read_text(encoding="utf-8"))


@pytest.mark.parametrize("example",DATA["cases"],ids=lambda x:x["case_id"])
def test_synthetic_answer_quality_acceptance(example):
    visible,cited,grounding=audit_assistant_answer(
        example["question"],example["evidence"],example["answer"],
        example["model_cited_ids"],profile=example["profile"],language="en")
    qa=evaluate_answer_quality(
        example["question"],example["evidence"],visible,cited,
        profile=example["profile"],grounding=grounding)
    assert [x["id"] for x in qa["checks"]]==DATA["checks"]
    assert [x["status"] for x in qa["checks"]]==example["expected"]
    assert len(qa["checks"])==4
    assert qa["human_accuracy"] is None
    assert qa["human_gold_answers_evaluated"]==0
    assert qa["evaluation_type"]=="DETERMINISTIC_HEURISTICS_NOT_HUMAN_ACCURACY"
    assert qa["human_review_required"] is True
    assert qa["claim_truth_verified"] is False
    assert qa["semantic_entailment_verified"] is False
    assert qa["legal_currentness_verified"] is False
    assert qa["legal_verdict_confirmed"] is False
    assert qa["no_paid_provider_called_by_this_check"] is True
    assert qa["review_required_checks"]==example["expected"].count(REVIEW)
    assert qa["passed_checks"]==example["expected"].count(PASS)
    assert qa["not_applicable_checks"]==example["expected"].count(NA)
    assert qa["needs_review"]==[
        name for name,status in zip(DATA["checks"],example["expected"])
        if status==REVIEW]
    assert set(cited).issubset({r["record_id"] for r in example["evidence"]})
    assert "accuracy_percent" not in qa and "accuracy_score" not in qa


def test_fixture_inventory_contains_negative_cases_in_all_four_dimensions():
    assert len(DATA["cases"])==16
    for dimension in range(4):
        statuses={case["expected"][dimension] for case in DATA["cases"]}
        assert REVIEW in statuses, "A failing example is required per dimension"
        assert NA in statuses
        assert PASS in statuses
    assert DATA["fixture_type"].startswith("SYNTHETIC_")
    assert DATA["version"]=="148.4"


def test_case_relevance_is_based_on_displayed_cited_source_not_uncited_other_source():
    evidence=[
        {"record_id":"SOCIAL-8","record_type":"SOCIAL_LISTENING",
         "source_excerpt":"Riau local administrative operations"},
        {"record_id":"SOCIAL-9","record_type":"SOCIAL_LISTENING",
         "source_excerpt":"Gibran public election oversight"}
    ]
    answer,refs,audit=audit_assistant_answer(
        "Gibran",evidence,"Source [SOCIAL-8]",["SOCIAL-8"],
        profile="SOCIAL_ANALYSIS",language="en")
    q=evaluate_answer_quality("Gibran",evidence,answer,refs,
                              grounding=audit)
    assert q["checks"][1]["status"]==REVIEW
    assert "gibran" in q["checks"][1]["missing_terms"]


def test_source_sentinels_not_confused_with_legal_currentness():
    evidence=[{"record_id":"INT-77","record_type":"FORMAL_INTELLIGENCE",
               "source_excerpt":"Riau human-reviewed relevance; source remains unverified",
               "verification_status":"UNVERIFIED"}]
    answer,refs,audit=audit_assistant_answer("Riau",evidence,
        "Relevance was reviewed, not source truth. [INT-77]",
        ["INT-77"],profile="CASE_REVIEW",language="en")
    result=evaluate_answer_quality("Riau",evidence,answer,refs,
                                   profile="CASE_REVIEW",grounding=audit)
    assert result["checks"][0]["status"]==PASS
    assert result["claim_truth_verified"] is False
    assert result["human_accuracy"] is None
    assert result["human_review_required"] is True


def test_readiness_evaluator_has_no_IO_side_effects(monkeypatch):
    import socket
    def forbidden(*args,**kwargs):
        raise AssertionError("Network access is forbidden in this evaluation")
    monkeypatch.setattr(socket,"create_connection",forbidden)
    social={"record_id":"SOCIAL-4","record_type":"SOCIAL_LISTENING",
            "source_excerpt":"Riau oversight source"}
    out=evaluate_answer_quality(
        "Riau",[social],"The saved Riau post needs verification. [SOCIAL-4]",
        ["SOCIAL-4"],profile="SOCIAL_ANALYSIS",
        grounding={"citation_ids_valid":True})
    assert out["checks"][0]["status"]==PASS
    assert out["no_paid_provider_called_by_this_check"] is True
