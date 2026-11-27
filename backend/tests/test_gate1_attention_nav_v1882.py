"""BAWASLU v188.2: attention-only Gate 1 queue and unified AI-5 navigation.

Synthetic, read-only tests: no connected Supabase or provider calls.
"""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app import inbox_human_queue as queue
from app.inbox_gate1_attention_v1882 import attention_reasons, _sampled_exclusion

ROOT=Path(__file__).resolve().parents[2]


def source(id=123,text="Saved election-related post",url="https://example.invalid/source"):
    return SimpleNamespace(id=id,text_content=text,canonical_url=url)


def record(action="CHECK_RELEVANT_EVIDENCE",relevance="RELEVANT",conf="0.93"):
    return {"action":action,"relevance":relevance,"relevance_confidence":conf}


def test_unreviewed_but_sufficient_relevant_source_is_not_attention_task():
    state={"information_review_status":"NEEDS_REVIEW"}
    reasons=attention_reasons(record(),state,source(),SimpleNamespace(),9)
    assert reasons == []
    assert attention_reasons(record(),{"information_review_status":"OFFICER_VERIFIED"},
                              source(),None,9)==[]


def test_real_uncertainty_and_material_evidence_gaps_get_readable_reasons():
    assert "UNASSESSED" in {r["code"] for r in attention_reasons(
        record("VERIFY_UNASSESSED","UNASSESSED",""),{},source(),None,9)}
    assert "UNCERTAIN" in {r["code"] for r in attention_reasons(
        record("REVIEW_UNCERTAIN","UNCERTAIN",""),{},source(),None,9)}
    assert "UNKNOWN_LABEL" in {r["code"] for r in attention_reasons(
        record("REVIEW_UNKNOWN_LABEL","MYSTERY",""),{},source(),None,9)}
    assert "MISSING_PRIMARY_EVIDENCE" in {r["code"] for r in attention_reasons(
        record(),{},source(text="",url=""),None,9)}
    assert "MISSING_PRIMARY_EVIDENCE" not in {r["code"] for r in attention_reasons(
        record(),{},source(text="Saved text",url=""),None,9)}


def test_revalidation_hold_and_low_confidence_are_not_overlooked():
    assert "REVALIDATION_REQUIRED" in {r["code"] for r in attention_reasons(
        record(),{"information_review_status":"REVALIDATION_REQUIRED"},source(),None,9)}
    assert "HELD_FOR_VERIFICATION" in {r["code"] for r in attention_reasons(
        record(),{"information_review_status":"HELD"},source(),None,9)}
    assert "LOW_RELEVANCE_CONFIDENCE" in {r["code"] for r in attention_reasons(
        record(conf="0.42"),{},source(),None,9)}
    assert "LOW_CONFIDENCE_EXCLUSION" in {r["code"] for r in attention_reasons(
        record("SPOT_CHECK_EXCLUDED","IRRELEVANT","65%"),{},source(),None,9)}


def test_excluded_safety_sample_is_stable_and_not_all_excluded_items():
    sampled=[i for i in range(1,151) if _sampled_exclusion(9,i)]
    assert 1 <= len(sampled) <= 15
    picked=sampled[0]
    skipped=next(i for i in range(1,151) if i not in sampled)
    flags=attention_reasons(record("SPOT_CHECK_EXCLUDED","IRRELEVANT","0.95"),
                            {},source(id=picked),None,9)
    assert flags and flags[0]["code"]=="EXCLUDED_QUALITY_SAMPLE"
    assert flags[0]["kind"]=="SAMPLE"
    assert attention_reasons(record("SPOT_CHECK_EXCLUDED","IRRELEVANT","0.95"),
                             {},source(id=skipped),None,9)==[]


def test_paginated_focus_filters_only_exceptions_preserving_all_view_and_scope():
    links=[SimpleNamespace(id=i,result_id=i) for i in range(6,0,-1)]
    db=MagicMock()
    db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value=links
    previous=queue._classified_batch
    def classify(database,officer,campaign,rows):
        return {r.result_id:{
            "result_id":str(r.result_id),"category":"relevant",
            "action":"CHECK_RELEVANT_EVIDENCE",
            "information_review_status":"NEEDS_REVIEW",
            "requires_human_attention":r.result_id in (2,5),
            "attention_reasons":[{"code":"UNCERTAIN","label":"Review uncertainty"}]
                if r.result_id in (2,5) else []
        } for r in rows}
    queue._classified_batch=classify
    try:
        attention=queue.paginated_review_queue(db,{},9,focus="attention")
        assert [x["result_id"] for x in attention["items"]]==["5","2"]
        assert attention["queue_name"]=="NEEDS_ATTENTION"
        assert attention["filter_focus"]=="attention"
        entire=queue.paginated_review_queue(db,{},9,focus="all")
        assert [x["result_id"] for x in entire["items"]]==["6","5","4","3","2","1"]
        assert entire["queue_name"]=="ALL_INFORMATION"
        with pytest.raises(HTTPException) as bad:
            queue.paginated_review_queue(db,{},9,focus="not-supported")
        assert bad.value.status_code==422
        db.commit.assert_not_called()
    finally:
        queue._classified_batch=previous


def test_frontend_sends_focus_and_preserves_keyset_security_contract():
    ui=(ROOT/"frontend/src/components/intel/InboxHumanReview.jsx").read_text()
    client=(ROOT/"frontend/src/api/base44Client.js").read_text()
    backend=(ROOT/"backend/app/inbox_human_queue.py").read_text()
    router=(ROOT/"backend/app/inbox_human_gate.py").read_text()
    for string in ("gate1-focus-attention","gate1-focus-all","Needs Attention",
                   "All Information","gate1-advanced-filters",
                   "focus:activeFocus","activeFocus!==currentFocus.current",
                   "item.attention_reasons"):
        assert string in ui,string
    assert "focus='all'" in client and "review_status:reviewStatus,focus" in client
    assert 'focus:str="all"' in router
    assert "attention_reasons(label, state, sources[sid], assessment, campaign_id)" in backend
    assert "CampaignEvidence.match_method != \"WATCHLIST_ACCOUNT\"" in backend
    assert "_result_in_scope(db, officer, sources[sid])" in backend
    assert '"count_is_page_only": True' in backend
    assert "MAX_SCAN_PER_REQUEST" in backend
    assert "db.commit(" not in backend


def test_unified_navigation_only_advertises_one_ai5_entry_and_keeps_permissions():
    nav=(ROOT/"frontend/src/components/intel/AccessNavigation.jsx").read_text()
    routes=(ROOT/"frontend/src/App.jsx").read_text()
    assert nav.count("'AI-5 Assistant'")==1
    assert "leadership?'/management/ai-5':'/ai-5'" in nav
    assert "leadership?'/management':'/'" in nav
    assert "['National Administrator','National Leadership','Provincial Administrator']" in nav
    assert "access?.permissions?.[key]===true" in nav
    assert "data-testid=\"unified-workspace-navigation\"" in nav
    for obsolete in ("Management AI Assistant","AI Assistant V2","AI-4 · AI Assistant","management-workspace-navigation",
                     "operations-workspace-navigation","future_modules"):
        assert obsolete not in nav,obsolete
    assert '<Route path="/management/ai-5"' in routes
    assert '<Route path="/ai-5"' in routes
    # Preserve old saved/deep links until a separate tested route retirement.
    assert '<Route path="/ai-4"' in routes
    assert '<Route path="/management/assistant"' in routes
