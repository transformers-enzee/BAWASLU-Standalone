"""v187.5 BAWASLU Gate 1 selective review, missing values and officer safety."""
from pathlib import Path

from app.inbox_gate1_review_plan_v1875 import AREAS, missing_tasks, review_framework, populated
from app.inbox_human_full_review_v1868 import (
    ASSESSMENT_FIELDS, COMPLETABLE_FIELDS, FIELDS, SENSITIVE,
)

ROOT=Path(__file__).resolve().parents[2]


def field(value="",mode="ORIGINAL"):
    return {"original":value,"effective":value,"mode":mode}


def test_eight_areas_prioritize_bawaslu_governance_without_allegation_by_default():
    assert len(AREAS)==8
    assert [a["id"] for a in AREAS[:3]]==["violation","actors","jurisdiction"]
    assert all(a["priority"]=="P1" for a in AREAS[:3])
    assert all(a["priority"]=="P2" for a in AREAS[3:])
    assert {"incident_jurisdiction","incident_chronology","review_priority"} <= ASSESSMENT_FIELDS
    assert {"incident_jurisdiction","incident_chronology"} <= SENSITIVE
    assert all(x in FIELDS for a in AREAS for x in a["fields"] if x not in ("relevance","sentiment"))


def test_candidate_or_location_not_mandatory_for_general_commentary():
    fields={"canonical_url":field("https://example.invalid/post"),
            "text_content":field("Public discussion about election policy"),
            "potential_issue_categories":field("[]"),
            "candidate_names":field(""),"incident_jurisdiction":field(""),
            "published_at":field(""),"engagement_likes":field(""),
            "transcript":field("")}
    assert missing_tasks(fields,relevance="RELEVANT",sentiment="NEUTRAL")==[]
    assert len(review_framework(fields))==8


def test_allegation_requires_contextual_fields_and_never_guesses_a_value():
    fields={"canonical_url":field("https://example.invalid/issue"),
            "text_content":field("Fictional allegation of money distribution"),
            "potential_issue_categories":field('["money_politics"]'),
            "incident_jurisdiction":field(""),
            "incident_date":field(""),
            "published_at":field(""),
            "evidence_quality":field("")}
    tasks=missing_tasks(fields,relevance="RELEVANT",sentiment="NEUTRAL")
    assert {"incident_jurisdiction","incident_chronology","published_at","evidence_quality"} <= {x["field"] for x in tasks}
    assert all(x["suggested_value"] is None for x in tasks)
    assert all(x["status"]=="NEEDS_OFFICER_VERIFICATION" for x in tasks)
    assert not {"candidate_names","engagement_shares","transcript"} & {x["field"] for x in tasks}


def test_unavailable_field_does_not_create_repeat_work():
    fields={"canonical_url":field("","UNAVAILABLE"),
            "text_content":field("Existing saved source content"),
            "potential_issue_categories":field("[]")}
    assert missing_tasks(fields,relevance="RELEVANT",sentiment="NEUTRAL")==[]
    assert not populated("[]")
    assert not populated('{"signals": []}')
    assert populated('["money_politics"]')
    assert "canonical_url" in COMPLETABLE_FIELDS
    assert not {"engagement_likes","engagement_shares","transcript"} & COMPLETABLE_FIELDS


def test_officer_ui_has_field_level_completion_not_missing_post_intake():
    source=(ROOT/"frontend/src/components/intel/Gate1FullWorkbench.jsx").read_text()
    assert source.count("idLabel:")==8
    for token in ("Complete Missing Data","gate1-contextual-missing-tasks",
                  "gate1-missing-existing-record","gate1-complete-missing-field",
                  "gate1-no-material-missing","Save missing value","Looks Correct"):
        assert token in source
    assert "Add Missing Post" not in source
    assert "Link to the missing post" not in source
    assert "base44.inboxHumanReview.addManualIntake(" not in source
    assert "gate1-internal-qa-tools" in (ROOT/"frontend/src/components/intel/InboxHumanReview.jsx").read_text()
    assert "!realQaSelected&&<div data-testid=\"gate1-internal-qa-tools\"" in (ROOT/"frontend/src/components/intel/InboxHumanReview.jsx").read_text()
    backend=(ROOT/"backend/app/inbox_human_full_review_v1868.py").read_text()
    assert '"missing_review_tasks":tasks' in backend
    assert 'entry.mode not in ("SUPPLEMENTED","UNAVAILABLE")' in backend
    assert 'entry.mode=="UNAVAILABLE"' in backend
    assert '"official_insight_published":False' in backend
