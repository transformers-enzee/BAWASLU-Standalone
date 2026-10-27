"""Regression checks for exemplar-reference lookup.

The per-post SQL helper intentionally excludes exemplar targets. These tests
ensure the separate text-based helper is used, and it cannot leak the target
into its own few-shot references.
"""
import pytest
from fastapi import HTTPException

from app.smart_radar_qa_references import reference_examples_for_audit_target


class FakeRows:
    def __init__(self, rows):
        self.rows = rows

    def mappings(self):
        return self

    def all(self):
        return self.rows


class FakeDb:
    def __init__(self, rows):
        self.rows = rows
        self.params = None
        self.query = None

    def execute(self, query, params):
        self.query = str(query)
        self.params = params
        return FakeRows(self.rows)


def test_text_lookup_preserves_independence():
    target = {
        "qa_id": "QA-TARGET", "cohort": "exemplar",
        "source_hash": "target-hash", "source_url": "https://target.example/a",
        "message_original": "Example election text for classification",
    }
    valid = {
        "qa_id": "QA-OTHER", "cohort": "exemplar",
        "source_hash": "other-hash", "source_url": "https://other.example/b",
        "gold_category": "Election Operations",
    }
    duplicate = {
        "qa_id": "QA-DUP", "cohort": "exemplar",
        "source_hash": "other-hash2", "source_url": target["source_url"],
        "gold_category": "Allegations / Violations",
    }
    db = FakeDb([
        {"example_qa_id": target["qa_id"], "shahrin_category": "Disputes / Legal",
         "example_excerpt": "target text", "source_url": target["source_url"],
         "similarity": 0.59},
        {"example_qa_id": duplicate["qa_id"], "shahrin_category": duplicate["gold_category"],
         "example_excerpt": "duplicate url text", "source_url": target["source_url"],
         "similarity": 0.47},
        {"example_qa_id": valid["qa_id"], "shahrin_category": valid["gold_category"],
         "example_excerpt": "Other independently verified event",
         "source_url": valid["source_url"], "similarity": 0.31},
    ])
    got = reference_examples_for_audit_target(db, target, [valid, duplicate])
    assert "qa_shahrin_examples_for_text" in db.query
    assert db.params["source_text"] == target["message_original"]
    assert db.params["source_hash"] == target["source_hash"]
    assert [x["qa_id"] for x in got] == ["QA-OTHER"]
    assert got[0]["human_primary_category"] == "Election Operations"


@pytest.mark.parametrize("cohort", ["development", "sealed_holdout"])
def test_non_exemplar_targets_fail_closed(cohort):
    with pytest.raises(HTTPException):
        reference_examples_for_audit_target(
            FakeDb([]), {"cohort": cohort}, [], max_examples=2)
