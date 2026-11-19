"""Offline acceptance evidence must never masquerade as real-answer approval."""
import json
from pathlib import Path
import pytest
from app.assistant_acceptance_snapshot import summarize, main


def write_inputs(tmp_path, *, tests=12, failures=0, skipped=0, counts=None):
    junit = tmp_path / "results.xml"
    junit.write_text(
        f'<testsuites><testsuite tests="{tests}" failures="{failures}" errors="0" skipped="{skipped}"/></testsuites>',
        encoding="utf-8",
    )
    triage = tmp_path / "triage.json"
    triage.write_text(json.dumps({
        "schema": "BAWASLU_OFFLINE_ANSWER_TRIAGE_V1",
        "model_calls": 0, "accuracy_score": None,
        "human_gold_scoring_completed": False,
        "case_count": 3, "status_counts": counts or {"REVIEW_REQUIRED": 2, "PASS_NARROW_LEXICAL_ONLY": 1},
        "private_source_excerpt": "NEVER EXPOSE THIS",
    }), encoding="utf-8")
    return junit, triage


def test_snapshot_reports_test_evidence_not_human_accuracy(tmp_path):
    junit, triage = write_inputs(tmp_path)
    result = summarize(junit, triage)
    assert result["automated_tests"] == {
        "total": 12, "passed": 12, "failed": 0, "skipped": 0, "result": "PASS",
    }
    assert result["real_model_answers_scored"] == 0
    assert result["human_gold_scoring_completed"] is False
    assert result["real_pdf_source_validation_completed"] is False
    assert result["officer_acceptance_completed"] is False
    assert result["release_approved"] is False
    assert result["overall_completion_percentage"] is None
    assert "NEVER EXPOSE THIS" not in json.dumps(result)


def test_failed_or_skipped_automated_checks_do_not_pass(tmp_path):
    junit, triage = write_inputs(tmp_path, failures=1, skipped=2)
    result = summarize(junit, triage)
    assert result["automated_tests"]["passed"] == 9
    assert result["automated_tests"]["result"] == "NOT_PASSED"
    assert result["release_approved"] is False


@pytest.mark.parametrize("bad_counts", [{"REVIEW_REQUIRED": 4}, {"REVIEW_REQUIRED": -1, "PASS": 4}])
def test_rejects_unreconciled_triage_counts(tmp_path, bad_counts):
    junit, triage = write_inputs(tmp_path, counts=bad_counts)
    with pytest.raises(ValueError):
        summarize(junit, triage)


def test_cli_writes_only_redacted_aggregate(tmp_path):
    junit, triage = write_inputs(tmp_path)
    target = tmp_path / "snapshot.json"
    assert main(["--junit", str(junit), "--triage", str(triage), "--output", str(target)]) == 0
    raw = target.read_text(encoding="utf-8")
    assert "NEVER EXPOSE THIS" not in raw
    assert json.loads(raw)["paid_ai_calls"] == 0
