"""Synthetic AI Assessment QA v183.6: no provider usage, migrations or DB writes."""
import pytest
from fastapi import HTTPException

from app import intelligence_assessment_qa as qa
from app.intelligence_contract import FIELD_GROUPS, INSIGHT_VARIABLES


def test_catalog_coverage_and_synthetic_status():
    catalog=qa.catalog_payload()
    assert len(catalog["field_groups"])==10
    assert len(catalog["insight_variables"])==15
    assert len(catalog["cases"])==8
    assert all(c["source_id"].startswith("SYNTH-") for c in catalog["cases"])
    assert all(c["reference_status"]=="ILLUSTRATIVE_NOT_OFFICER_GOLD" for c in catalog["cases"])
    assert not catalog["paid_model_called"]
    assert not catalog["real_ai_connected"]
    assert not catalog["persistent_writes"]
    assert {k for group in FIELD_GROUPS.values() for k in group}>=set(
        k for c in qa.CASES for k in c["expected"]
    )
    assert len(INSIGHT_VARIABLES)==15


@pytest.mark.parametrize("case",qa.CASES,ids=lambda c:c["id"])
def test_each_synthetic_reference_scores_full_match(case):
    result=qa.evaluate(case["id"],dict(case["expected"]))
    assert result["matched_fields"]==len(case["expected"])
    assert result["agreement"]==1
    assert result["coverage"]==1
    assert result["mismatched_fields"]==0
    assert result["paid_model_called"] is False
    assert result["persistent_writes"] is False


@pytest.mark.parametrize("case",qa.CASES[:7],ids=lambda c:c["id"])
def test_planted_errors_are_detected(case):
    result=qa.evaluate(case["id"],dict(case["sample_predictions"]))
    assert result["mismatched_fields"]>=1
    assert result["agreement"]<1


def test_omissions_are_not_credited_as_agreement():
    result=qa.evaluate("unknown-location",{"event_location":"unknown"})
    assert result["matched_fields"]==1
    assert result["missing_fields"]==3
    assert result["coverage"]==0.25


def test_bogus_fields_and_nested_payloads_rejected():
    with pytest.raises(HTTPException) as x:
        qa.evaluate("money-politics",{"injected_unknown":"foo"})
    assert x.value.status_code==422
    with pytest.raises(HTTPException):
        qa.evaluate("money-politics",{"violation_type":{"nested":"malicious"}})
    with pytest.raises(HTTPException):
        qa.evaluate("money-politics",{"violation_type":"X"*301})
    with pytest.raises(HTTPException):
        qa.evaluate("unknown-case",{})


def test_override_is_approved_only_and_never_persisted():
    result=qa.evaluate("approved-override",qa.LOOKUP["approved-override"]["expected"])
    assert result["override_preview"]=={
        "ai_value":"money_politics",
        "approved_effective_value":"other_regulatory_issue",
        "unapproved_effective_value":"money_politics",
        "persisted":False, "officer_record_modified":False,
    }


def test_permissions_are_enforced_even_with_enabled_flag(monkeypatch):
    monkeypatch.setenv("BAWASLU_ASSESSMENT_QA_ENABLED","1")
    user=object()
    authorized={"role":"National Administrator","geographic_scope":"Nationwide",
                "status":"Active","permissions":{"administration":True}}
    monkeypatch.setattr(qa,"profile",lambda db,u:authorized)
    assert qa.require_national_admin(None,user)["role"]=="National Administrator"
    for downgrade in (
        {"status":"Inactive"},
        {"role":"Provincial Administrator"},
        {"geographic_scope":"Province"},
        {"permissions":{"administration":False}},
    ):
        monkeypatch.setattr(qa,"profile",lambda db,u,down=downgrade:{**authorized,**down})
        with pytest.raises(HTTPException) as exc:
            qa.require_national_admin(None,user)
        assert exc.value.status_code==403


def test_disabled_environment_cannot_expose_catalog(monkeypatch):
    monkeypatch.delenv("BAWASLU_ASSESSMENT_QA_ENABLED",raising=False)
    monkeypatch.setattr(qa,"profile",lambda db,u:{
        "role":"National Administrator","geographic_scope":"Nationwide",
        "status":"Active","permissions":{"administration":True},
    })
    with pytest.raises(HTTPException) as exc:
        qa.catalog(user=object(),db=None)
    assert exc.value.status_code==404
