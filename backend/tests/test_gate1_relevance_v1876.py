"""BAWASLU v187.6 - contextual missing-data relevance and readable officer evidence.

All test inputs are synthetic. No connected operational database is queried.
"""
import json
from pathlib import Path
from app.inbox_gate1_review_plan_v1875 import (
    decode, populated, time_context, event_location_mentioned, missing_tasks, review_framework
)

ROOT=Path(__file__).resolve().parents[2]


def f(value="",mode="ORIGINAL"):
    return {"original":value,"effective":value,"mode":mode}


def synthetic_issue(**kwargs):
    return json.dumps([{"category_id":4,"category_name":"Electoral Violation",
                        "signal_type":"REPORTED_INCIDENT",
                        "signal_provenance":"AI_REPORTED_INCIDENT",
                        "evidence_quote":"Allegation described in a fictional source",
                        "explanation":"Not a legal determination",
                        "requires_human_verification":True,**kwargs}])


def test_reported_historical_issue_does_not_create_three_false_missing_tasks():
    data={"potential_issue_categories":f(synthetic_issue(time_context="HISTORICAL")),
          "canonical_url":f("https://example.invalid/fictional"),
          "text_content":f("A fictional historical allegation requiring verification"),
          "candidate_names":f('["Fictional Character"]'),
          "geographic_context":f("[]"),"incident_jurisdiction":f(""),
          "incident_date":f(""),"published_at":f(""),
          "incident_chronology":f(""),"evidence_quality":f("")}
    assert time_context(data)=="HISTORICAL"
    assert event_location_mentioned(data) is False
    assert missing_tasks(data,relevance="RELEVANT",sentiment="NEGATIVE")==[]
    states={x["id"]:x["state"] for x in review_framework(data,[])}
    assert states["jurisdiction"]=="NOT_ESTABLISHED"
    assert states["timeline"]=="CONTEXT_ONLY"
    assert states["verification"]=="NOT_ASSESSED"


def test_account_location_does_not_imply_incident_location():
    data={"potential_issue_categories":f(synthetic_issue(time_context="HISTORICAL")),
          "canonical_url":f("https://example.invalid/fake"),
          "text_content":f("Fictional post"),
          "province":f("Jawa Timur"),"location_basis":f("ACCOUNT_PROFILE"),
          "incident_jurisdiction":f("")}
    assert event_location_mentioned(data) is False
    assert "incident_jurisdiction" not in {x["field"] for x in
                                        missing_tasks(data,relevance="RELEVANT")}


def test_explicit_event_location_context_can_generate_material_review_task():
    data={"potential_issue_categories":f(synthetic_issue(time_context="HISTORICAL")),
          "geographic_context":f(json.dumps([{
              "role":"INCIDENT_LOCATION","place":"Fictional District"}])),
          "canonical_url":f("https://example.invalid/fake"),
          "text_content":f("Fictional incident source"),
          "incident_jurisdiction":f("")}
    tasks=missing_tasks(data,relevance="RELEVANT",sentiment="NEUTRAL")
    task=next(x for x in tasks if x["field"]=="incident_jurisdiction")
    assert task["priority"]=="P1" and task["suggested_value"] is None
    assert task["status"]=="NEEDS_OFFICER_VERIFICATION"
    framework=review_framework(data,tasks)
    assert next(x for x in framework if x["id"]=="jurisdiction")["state"]=="NEEDS_COMPLETION"
    data["incident_jurisdiction"]=f("Fictional District",mode="OFFICER_SUPPLIED")
    assert "incident_jurisdiction" not in {x["field"] for x in missing_tasks(data,relevance="RELEVANT")}


def test_unavailable_does_not_loop_and_missing_real_source_remains_high_attention():
    data={"canonical_url":f("","UNAVAILABLE"),"text_content":f("","UNAVAILABLE"),
          "potential_issue_categories":f(synthetic_issue(time_context="HISTORICAL"))}
    assert missing_tasks(data,relevance="RELEVANT")==[]
    data["canonical_url"]=f("")
    data["text_content"]=f("")
    tasks=missing_tasks(data,relevance="RELEVANT")
    assert {"canonical_url","text_content"} <= {x["field"] for x in tasks}
    assert all(x["priority"]=="P1" for x in tasks)


def test_current_allegation_asks_only_for_relevant_source_timing():
    data={"canonical_url":f("https://example.invalid/source"),
          "text_content":f("A fictional current report"),
          "potential_issue_categories":f(synthetic_issue(time_context="ONGOING")),
          "incident_date":f(""),"published_at":f("")}
    assert {x["field"] for x in missing_tasks(data,relevance="RELEVANT")}=={"published_at"}
    assert not populated("[]")
    assert not populated('{"signals":[]}')
    assert populated('["fictional issue"]')
    assert isinstance(decode(data["potential_issue_categories"]["effective"]),list)


def test_officer_display_summarizes_structured_signals_but_keeps_audit_raw():
    ui=(ROOT/"frontend/src/components/intel/Gate1FullWorkbench.jsx").read_text()
    for snippet in (
        "const humanValue=","const parseSaved=","category_name",
        "Unverified — human check required",
        "gate1-raw-structured-evidence","evidenceExcerpt",
        "Preliminary reported issue", "does not confirm candidate status",
        "groupSummary(group)", "gate1-current-effective-value",
        "type=\"date\"","field==='incident_jurisdiction'",
        "gate1-missing-value", "gate1-contextual-missing-tasks"
    ):
        assert snippet in ui,snippet
    assert "data-testid=\"gate1-raw-structured-evidence\"" in ui
    assert "Original provider / AI value" in ui
    assert "Source data incorrect?" in ui


def test_backend_only_proposes_tasks_and_preserves_gate1_permissions():
    code=(ROOT/"backend/app/inbox_human_full_review_v1868.py").read_text()
    assert '"review_areas":review_framework(review_values,tasks)' in code
    assert '"missing_review_tasks":tasks' in code
    assert "isolated_source(db,campaign,source)" in code
    assert "qa_audit_only" in code
    assert "original_source_preserved" in code
    assert "official_insight_published" in code
