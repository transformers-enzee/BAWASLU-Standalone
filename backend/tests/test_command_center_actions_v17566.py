"""Zero-credit Command Centre review cards from synthetic scoped evidence."""
from app.command_center_actions import build_action_intelligence, category_domain

def alert(**changes):
    row={"result_id":"894","campaign_id":"21","campaign_name":"Monitoring A",
         "category":"Dugaan Penyadapan / Intersepsi Komunikasi",
         "province":"DKI Jakarta","source_url":"https://example.org/report",
         "evidence_quote":"Reported allegation only","review_status":"AWAITING_REVIEW",
         "signal_provenance":"SAVED_SOURCE_QUOTE"}
    return {**row,**changes}

def test_interception_remains_general_law_without_confirmed_electoral_nexus():
    result=build_action_intelligence([alert()],[],"Nationwide")
    item=result["items"][0]
    assert item["domain"]=="GENERAL_CRIMINAL_LAW"
    assert item["legal_status"]=="NOT_DETERMINED"
    assert item["affected_provinces"]==[]
    assert item["review_geography"]=="DKI Jakarta"
    assert item["incident_location_verified"] is False
    assert item["officer_assigned"] is False
    assert result["generation_mode"]=="DETERMINISTIC_NO_PAID_AI"

def test_officer_flag_confirmed_is_not_a_legal_verdict():
    item=build_action_intelligence([alert(review_status="FLAG_CONFIRMED")],[],"Nationwide")["items"][0]
    assert item["officer_flag_status"]=="FLAG_CONFIRMED"
    assert item["legal_status"]=="NOT_DETERMINED"

def test_regional_scope_is_review_not_auto_assignment():
    item=build_action_intelligence([alert(province="Kalimantan Selatan")],[],"Province")["items"][0]
    assert item["owner_role_suggested"]=="Authorized Provincial / Local Reviewer"
    assert item["affected_provinces"]==[]
    assert item["officer_assigned"] is False

def test_duplicate_social_ids_deduplicated():
    result=build_action_intelligence([alert(),alert(campaign_id="22")],[],"Nationwide")
    assert result["candidate_count"]==1

def test_manual_inbox_category_requires_saved_category_or_pending_status():
    records=[
        {"id":"1","campaign_name":"INT-1","review_status":"Validated as Relevant Intelligence"},
        {"id":"2","campaign_name":"INT-2","review_status":"Pending Review",
         "potential_issue_category":"Judicial ethics","province":"DKI Jakarta"}
    ]
    items=build_action_intelligence([],records,"Nationwide")["items"]
    assert len(items)==1
    assert items[0]["domain"]=="INSTITUTIONAL_ETHICS"
    assert items[0]["affected_provinces"]==[]

def test_missing_source_requires_verification():
    item=build_action_intelligence([alert(source_url="")],[],"Nationwide")["items"][0]
    assert "Obtain and verify" in item["actions"][0]

def test_domain_mapping_is_only_an_unverified_saved_category_hint():
    assert category_domain("")[0]=="UNCLASSIFIED"
    assert category_domain("Surat suara tidak sesuai")[0]=="ELECTORAL_ADMINISTRATION"
    assert category_domain("Generic description")[0]=="SAVED_ISSUE_UNVERIFIED"
