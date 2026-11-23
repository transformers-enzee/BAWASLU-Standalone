"""No-credit regression tests for SmartRadar institutional decision intelligence."""
from app.assistant_decision_intelligence import (
    DECISION_SCHEMA, fallback_decision, safe_decision, synthesize_public_decision
)

OFFICIAL="https://dkpp.go.id/berita/pemeriksaan"
NEWS="https://example.org/news/story"

def _candidate(relevance="DIRECT_OVERSIGHT"):
    return {
        "answer":("The relevant official body is reviewing the reported matter. "
                  "BAWASLU should preserve its own contemporaneous oversight records "
                  "before any institutional response. [DKPP](%s)"%OFFICIAL),
        "relevance":relevance,
        "institutional_implication":"Potential scrutiny of election-supervision records, not a confirmed violation.",
        "recommended_decision":"Authorize an internal document-verification review only.",
        "reason":"The cited official record is relevant but not a determination of fault.",
        "legal_review":{
            "domain":"Ethics and election supervision",
            "competent_authority":"DKPP for ethics; BAWASLU for its own supervision records",
            "rule_reference":"A statutory article claimed by an AI model",
            "applicability":"Confirm election type, stage and official document",
            "verification_needed":"Read the official rule and case notice",
            "source_urls":[OFFICIAL]
        },
        "claims":[
            {"claim":"An official hearing was announced","evidence_status":"PRIMARY_SOURCE_REPORTED","source_urls":[OFFICIAL]},
            {"claim":"A second media allegation","evidence_status":"PRIMARY_SOURCE_REPORTED","source_urls":[NEWS]},
            {"claim":"An unsupported invented citation","evidence_status":"PRIMARY_SOURCE_REPORTED","source_urls":["https://invalid.example/fake"]}
        ],
        "actions":[
            {"task":"Preserve and compare 2024 nomination supervision documents",
             "owner_role":"Authorized legal and supervision records officer",
             "evidence_required":"Dated copies, audit trail and original correspondence",
             "expected_output":"A verified source and document inventory",
             "escalation_condition":"Legal review only if corroborated conduct and competence are documented",
             "source_urls":[OFFICIAL,"https://invalid.example/fake"]},
            {"task":"Automatically file a violation report and sanction a candidate",
             "owner_role":"Named official","evidence_required":"News stories",
             "expected_output":"Punishment order",
             "escalation_condition":"Immediately after the news","source_urls":[NEWS]},
        ],
        "missing_evidence":"No verified applicable legal provision or complete file."
    }

def test_claims_are_only_attributed_to_consulted_urls():
    result=safe_decision(_candidate(),[OFFICIAL,NEWS])
    assert result and len(result["officer_decision"]["claims"])==2
    assert result["officer_decision"]["claims"][0]["verified_by_officer"] is False
    assert result["officer_decision"]["claims"][1]["evidence_status"]=="MEDIA_REPORTED"
    assert result["decision_plan"][0]["source_urls"]==[OFFICIAL]
    assert len(result["decision_plan"])==1
    assert result["officer_decision"]["quality"]["legal_applicability_verified"] is False

def test_unconsulted_answer_hyperlink_is_removed():
    c=_candidate()
    c["answer"]+=" [unavailable court decision](https://invalid.example/ruling)"
    assert "https://invalid.example" not in safe_decision(c,[OFFICIAL])["answer"]
    assert "source not consulted" in safe_decision(c,[OFFICIAL])["answer"]

def test_only_a_verification_check_remains_when_no_nexus():
    c=_candidate("NO_ESTABLISHED_NEXUS")
    c["actions"][0]["task"]="Refer the matter immediately to investigators"
    result=safe_decision(c,[OFFICIAL])
    assert result["decision_plan"]==[]
    assert result["officer_decision"]["relevance"]=="NO_ESTABLISHED_NEXUS"

def test_official_reference_missing_requires_verification():
    c=_candidate()
    c["legal_review"]["source_urls"]=[NEWS]
    result=safe_decision(c,[OFFICIAL,NEWS])
    assert result["officer_decision"]["legal_review"]["official_primary_available"] is False
    assert result["officer_decision"]["legal_review"]["rule_reference"].startswith("Official controlling provision")
    assert result["officer_decision"]["quality"]["review_required"] is True

def test_missing_search_or_key_never_generates_a_claim():
    result=synthesize_public_decision("What changed?",None,None,"model","https://api.openai.com/v1")
    assert result["officer_decision"]["claims"]==[]
    assert result["officer_decision"]["status"]=="ACTION_SYNTHESIS_UNAVAILABLE"
    assert result["officer_decision"]["quality"]["automated_actions_executed"] is False

def test_strict_schema_has_no_extra_properties():
    assert DECISION_SCHEMA["additionalProperties"] is False
    assert DECISION_SCHEMA["properties"]["legal_review"]["additionalProperties"] is False
    assert DECISION_SCHEMA["properties"]["actions"]["items"]["additionalProperties"] is False

def test_history_preserves_web_profile_and_review_only_packet():
    from app.assistant_history import clean_messages
    assessment=safe_decision(_candidate(),[OFFICIAL,NEWS])
    msg={"role":"assistant","text":assessment["answer"],"records":[],
         "response_profile":"WEB_RESEARCH",
         "decision_plan":assessment["decision_plan"],
         "officer_decision":assessment["officer_decision"]}
    saved=clean_messages([msg])[0]
    assert saved["response_profile"]=="WEB_RESEARCH"
    assert saved["decision_plan"][0]["required_evidence"]
    assert saved["officer_decision"]["legal_review"]["officer_verification_required"]
    assert saved["officer_decision"]["status"]=="HISTORICAL_PROPOSED_REVIEW_ONLY"
