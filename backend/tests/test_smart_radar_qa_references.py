"""No-credit tests for the actual QA runner's reference adapter."""
import hashlib
import json
import pytest
from fastapi import HTTPException

from app.smart_radar_qa_references import (
    REFERENCE_REVISION, reference_examples_for_record,
    build_reference_messages, reference_audit_metadata,
)

RUBRIC = "Seven categories; output JSON only."
HASH = hashlib.sha256(RUBRIC.encode()).hexdigest()
VERSION = {
    "instructions": RUBRIC,
    "instructions_sha256": HASH,
    "reference_revision": REFERENCE_REVISION,
}
RECORD = {
    "qa_id": "QA-10649", "cohort": "development",
    "source_hash": "a" * 64, "source_url": "https://test.local/source",
    "message_original": "Original post not given an analyst label.",
}
EXEMPLARS = [{
    "qa_id": "QA-1", "cohort": "exemplar",
    "source_hash": "b" * 64, "source_url": "https://test.local/other",
    "gold_category": "Election Operations",
}]
CANDIDATE = {
    "example_qa_id": "QA-1",
    "shahrin_category": "Election Operations",
    "example_excerpt": "Reference text describing administrative procedures.",
    "similarity": .3,
}


class DB:
    def __init__(self, rows):
        self.rows = rows
    def execute(self, query, params):
        self.params = params
        self.query = str(query)
        return self
    def mappings(self):
        return self
    def all(self):
        return self.rows


def test_retrieval_uses_only_exemplar_labels():
    db = DB([CANDIDATE])
    examples = reference_examples_for_record(db, RECORD, EXEMPLARS)
    assert len(examples) == 1
    messages, fingerprint = build_reference_messages(
        "System guard", VERSION, RECORD, examples)
    prompt = json.dumps(messages, ensure_ascii=False)
    assert "Election Operations" in prompt
    assert "QA-10649" not in prompt
    assert "QA-1" not in prompt
    assert "curated_category" not in prompt
    assert "qa_imported_human_categories" not in db.query
    assert reference_audit_metadata(examples, fingerprint)["qa_reference_count"] == 1


def test_no_similar_examples_is_valid():
    examples = reference_examples_for_record(DB([]), RECORD, EXEMPLARS)
    messages, _ = build_reference_messages("Guard", VERSION, RECORD, examples)
    assert json.loads(messages[1]["content"])["reference_examples"] == []


@pytest.mark.parametrize("candidate", [
    {**CANDIDATE, "example_qa_id": "QA-10649"},
    {**CANDIDATE, "shahrin_category": "Disputes / Legal"},
    {**CANDIDATE, "similarity": .99},
    {**CANDIDATE, "similarity": .05},
    {**CANDIDATE, "example_excerpt": ""},
])
def test_bad_reference_not_passed_to_model(candidate):
    assert reference_examples_for_record(DB([candidate]), RECORD, EXEMPLARS) == []


def test_wrong_cohort_rejected():
    with pytest.raises(HTTPException):
        reference_examples_for_record(DB([CANDIDATE]), {**RECORD, "cohort": "sealed_holdout"}, EXEMPLARS)


def test_wrong_rubric_hash_fails_closed():
    with pytest.raises(HTTPException):
        build_reference_messages("Guard", {**VERSION, "instructions": RUBRIC + " changed"}, RECORD, [])


def test_old_version_cannot_invoke_reference_mode():
    with pytest.raises(HTTPException):
        build_reference_messages("Guard", {**VERSION, "reference_revision": ""}, RECORD, [])
