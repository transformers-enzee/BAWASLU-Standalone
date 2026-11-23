"""Zero-provider-cost contracts for adaptive SmartRadar research and drafting."""
import pytest
from app.assistant_workflows import infer_workflow, normalize_workflow_request, workflow_system_directive
from app.assistant_web_first import safe_public_question


@pytest.mark.parametrize("question,expected", [
    ("Are there similar cases in other provinces?", "RESEARCH"),
    ("Explain Article 169(r) of the election law.", "RESEARCH"),
    ("Draft an executive memo based on this research.", "STRATEGY_DRAFTING"),
    ("Balas email mengenai pengawasan pemilu.", "STRATEGY_DRAFTING"),
    ("Recommend three tactics and a 90-day plan.", "STRATEGY_DRAFTING"),
    ("Create a strategy with alternatives and trade-offs.", "STRATEGY_DRAFTING"),
])
def test_auto_intent(question,expected):
    assert infer_workflow(question)==expected
    selection={"smartRadar":True,"publicWeb":True,"legalReferences":True,"attachments":True}
    cfg=normalize_workflow_request({"question":question,"workflowMode":"AUTO","sourceSelection":selection})
    assert cfg["workflow"]==expected
    assert cfg["requested_workflow"]=="AUTO"
    assert cfg["sources"]==selection


def test_follow_up_revision_preserves_drafting():
    history=[{"role":"user","text":"Draft a leadership memo"}]
    assert infer_workflow("Make it shorter","",history)=="STRATEGY_DRAFTING"
    assert infer_workflow("How does the law define a violation?","","")=="RESEARCH"


def test_manual_and_explicit_source_choices_respected():
    cfg=normalize_workflow_request({"workflowMode":"RESEARCH","question":"Draft memo",
        "sourceSelection":{"smartRadar":False,"publicWeb":True,"legalReferences":False,"attachments":False}})
    assert cfg["workflow"]=="RESEARCH"
    assert cfg["sources"]["smartRadar"] is False
    assert cfg["sources"]["legalReferences"] is False


def test_draft_requires_human_review_and_public_search_rejects_private_ids():
    directive=workflow_system_directive("STRATEGY_DRAFTING")
    assert "DRAFT ONLY" in directive
    assert "Never send a message" in directive
    assert "review checkpoint" in directive
    assert not safe_public_question("Check SOCIAL-740 against the latest public updates")
    assert safe_public_question("Research public KPU and BAWASLU regulations")
