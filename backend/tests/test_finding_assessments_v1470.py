"""v147.0 finding-level legal/platform assessment and authorization tests."""
import pytest
from fastapi import HTTPException
from app.finding_assessments import assess_finding, finding_assessments


def post(source, platform, text, campaign="42"):
    return {"canonical_source_id":"social:"+str(source), "result_id":str(source),
            "campaign_id":campaign, "source_url":"https://example.invalid/"+str(source),
            "platform":platform, "message_original":text}


def test_dual_assessment_never_conflates_legal_and_platform_rules(monkeypatch):
    import app.finding_assessments as module
    observed=[]
    def no_paid(db,p,question,limit,semantic):
        observed.append((limit,semantic))
        return [{
            "document_id":91,"page":2,"title":"Officer reviewed SOP",
            "issuer":"BAWASLU","record_id":"DOC-91-P2",
            "source_url":"/api/assistant-knowledge/91/download",
            "source_excerpt":"Review evidence with authorized officers.",
            "review_status":"OFFICER_REVIEWED","document_type":"SOP",
        },{
            "document_id":92,"page":5,"title":"Unreviewed regulation",
            "record_id":"DOC-92-P5",
            "source_url":"/api/assistant-knowledge/92/download",
            "review_status":"UNREVIEWED","document_type":"REGULATION",
        }]
    monkeypatch.setattr(module,"retrieve_knowledge",no_paid)
    row = post(11,"tiktok","I will attack you")
    finding={"id":"topic:11", "title":"Possible election issue", "players":["violations"],"posts":[row,row]}
    result=assess_finding(None,{},finding)
    assert result["source_count_assessed"]==1
    assert result["legal"]["status"]=="PRELIMINARY_REVIEW_RECOMMENDED"
    assert result["legal"]["approved_reference_pages"][0]["document_id"]==91
    assert len(result["legal"]["approved_reference_pages"])==1
    assert result["legal"]["unreviewed_matched_pages"]==1
    assert result["platform_policy"]["potential_review_queue"][0]["status"]=="REVIEW_INDICATED"
    assert result["platform_policy"]["status_counts"]["REVIEW_INDICATED"]==1
    assert result["legal"]["official_legal_verdict"] is False
    assert result["platform_policy"]["platform_violation_confirmed"] is False
    assert result["follow_up"]["created_assignment"] is False
    assert result["paid_provider_called"] is False
    assert observed==[(8,False)]


def test_contextual_news_criticism_is_not_a_confirmed_platform_breach(monkeypatch):
    import app.finding_assessments as module
    monkeypatch.setattr(module,"retrieve_knowledge",lambda *a,**k:[])
    finding={"id":"topic:44","players":["concerns"],"posts":[
        post(5,"instagram","Citizens criticised the BAWASLU service response"),
        post(6,"youtube","News reported an alleged threat by an official"),
    ]}
    result=assess_finding(None,{},finding)
    assert result["legal"]["status"]=="NO_SAVED_POTENTIAL_VIOLATION_FLAG"
    assert result["legal"]["approved_reference_missing"] is True
    assert result["platform_policy"]["potential_review_queue"]==[]
    assert result["platform_policy"]["platform_violation_confirmed"] is False
    assert result["platform_policy"]["status_counts"]["NO_DIRECT_SIGNAL_IDENTIFIED"]==2


def test_authorization_and_unknown_finding_fail_closed(monkeypatch):
    import app.finding_assessments as module
    import app.smart_radar as radar
    monkeypatch.setattr(module,"profile",lambda db,user:{"permissions":{"view_intelligence":False},"status":"Active"})
    with pytest.raises(HTTPException) as exc:
        finding_assessments("secret",object(),None)
    assert exc.value.status_code==403
    monkeypatch.setattr(module,"profile",lambda db,user:{"permissions":{"view_intelligence":True},"status":"Active"})
    monkeypatch.setattr(radar,"access_findings",lambda db,user:[{"id":"visible","posts":[]}])
    with pytest.raises(HTTPException) as exc:
        finding_assessments("secret",object(),None)
    assert exc.value.status_code==404


def test_not_a_paid_model_or_automatic_takedown(monkeypatch):
    import app.finding_assessments as module
    monkeypatch.setattr(module,"retrieve_knowledge",lambda *a,**k:[])
    f={"id":"f","players":["violations"],"posts":[post(8,"reddit","A public complaint")]}
    result=assess_finding(None,{},f)
    assert result["platform_policy"]["status_counts"]["POLICY_NOT_CONFIGURED"]==1
    assert result["legal"]["statutory_articles_verified"] is False
    assert result["follow_up"]["takedown_requested"] is False
