"""No-provider tests: CLI must refuse ambiguous or potentially re-billed assessment jobs."""
from types import SimpleNamespace
import pytest
from scripts.resume_zocialeye_assessment import assert_job_assessment_alignment


def record(label):
    return SimpleNamespace(relevance_label=label)


@pytest.mark.parametrize("label", ["RELEVANT", "IRRELEVANT", "UNCERTAIN"])
def test_completed_job_requires_saved_classification(label):
    assert_job_assessment_alignment("COMPLETED", record(label))


def test_completed_without_classification_is_rejected():
    with pytest.raises(ValueError, match="lacks a saved"):
        assert_job_assessment_alignment("COMPLETED", None)


def test_sentiment_only_does_not_count_as_completed():
    with pytest.raises(ValueError, match="lacks a saved"):
        assert_job_assessment_alignment("COMPLETED", record(""))


def test_pending_without_classification_is_safe():
    assert_job_assessment_alignment("PENDING", None)


def test_pending_with_saved_result_cannot_be_rebilled():
    with pytest.raises(ValueError, match="already has a saved"):
        assert_job_assessment_alignment("PENDING", record("RELEVANT"))


def test_failed_job_is_not_reclassified_by_integrity_guard():
    assert_job_assessment_alignment("FAILED", None)
