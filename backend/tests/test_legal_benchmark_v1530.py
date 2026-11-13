"""v153.0 independent synthetic benchmark gate and admin-only API."""
import pytest
from fastapi import HTTPException,Response
from app.assistant_legal_benchmark import CORPUS,run_legal_signal_benchmark
from app import assistant_eval_sampling as router

def test_fixed_synthetic_cases_all_match_expected_review_signals():
    result=run_legal_signal_benchmark()
    assert result["number_of_cases"]>=30
    assert result["case_checks_failed"]==0,[
        (x["id"],x["expected_issue_present"],x["expected_issue_absent"],
         x["observed_issue_codes"]) for x in result["cases"] if not x["case_matched"]]
    assert result["matched_signal_assertions"]==result["labeled_signal_assertions"]
    assert result["synthetic_signal_precision"]==1
    assert result["synthetic_signal_recall"]==1

def test_real_human_acceptance_is_not_inferred_from_synthetic_benchmark():
    result=run_legal_signal_benchmark()
    assert result["dataset_kind"]=="DEVELOPER_LABELED_SYNTHETIC_SCENARIOS"
    assert result["human_gold_answers_evaluated"]==0
    assert result["human_acceptance_complete"] is False
    assert result["real_model_accuracy_measured"] is False
    assert result["real_model_answers_generated"] is False
    assert result["statistically_representative"] is False
    assert result["paid_ai_calls"]==0
    assert result["database_writes"]==0
    assert result["crawls"]==0

def test_fixed_corpus_has_diverse_positive_negative_and_nonlegal_cases():
    ids=[x["id"] for x in CORPUS]
    assert len(ids)==len(set(ids))
    categories=set(x["category"] for x in CORPUS)
    assert len(categories)>=9
    assert {k for x in CORPUS for k in x["expected_present"]}>={
        "ELIGIBLE_LEGAL_SOURCE_MISSING","CITATION_INTEGRITY",
        "ARTICLE_OR_CLAIM_ATTRIBUTION","PASSAGE_POLARITY","NUMERIC_OR_DATE",
        "ELECTION_SCOPE","DOCUMENT_REVIEW_PENDING","SOURCE_RELEVANCE",
        "LEGAL_OUTCOME_OR_ACTION","VERSION_OR_EFFECTIVE_DATE"}
    assert any(x["expected_status"]=="NOT_APPLICABLE" for x in CORPUS)
    assert all(not any("http://" in str(v) or "https://" in str(v)
                       for v in x["documents"]) for x in CORPUS)

def test_benchmark_never_exposes_internal_answer_text_or_corpus_excerpts():
    response=run_legal_signal_benchmark()
    assert not any("documents" in row or "answer" in row or "question" in row
                   for row in response["cases"])
    assert all(row["synthetic_only"] for row in response["cases"])

def test_endpoint_is_admin_permission_scoped(monkeypatch):
    monkeypatch.setattr(router,"profile",lambda db,user:{"role":"viewer"})
    monkeypatch.setattr(router,"has",lambda p,permission:False)
    with pytest.raises(HTTPException) as error:
        router.legal_benchmark(response=Response(),user=object(),db=None)
    assert error.value.status_code==403

def test_endpoint_success_has_no_store_headers(monkeypatch):
    monkeypatch.setattr(router,"profile",lambda db,user:{"role":"admin"})
    monkeypatch.setattr(router,"has",lambda p,permission:permission in {"administration","view_intelligence"})
    r=Response()
    result=router.legal_benchmark(response=r,user=object(),db=None)
    assert r.headers["Cache-Control"]=="private, no-store"
    assert r.headers["X-Evaluation-Generation"]=="NONE"
    assert result["human_gold_answers_evaluated"]==0
    assert result["number_of_cases"]==len(CORPUS)

def test_benchmark_has_no_real_authorized_evidence_ids():
    result=run_legal_signal_benchmark()
    assert all(not str(v).startswith("SOCIAL-") for item in result["cases"]
               for v in item["observed_issue_codes"])
