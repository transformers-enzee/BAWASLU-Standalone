"""v148.8: zero-credit authorized evaluation sampling and exact-ID retrieval."""
import json
from fastapi import HTTPException, Response
import pytest

from app.assistant_eval_sampling import (
    build_evaluation_question_plan,evaluation_questions,_http_url
)
from app.assistant_orchestration import _social_select
from app.models import User
from test_management_briefings_v1468 import dataset


def source(num,platform="X",published="2026-11-11T13:00:00+07:00",
           campaign="11",region=False,verified=False,link=True):
    return {
        "canonical_source_id":f"social:{num}","result_id":str(num),
        "campaign_id":str(campaign),"platform":platform,
        "source_url":f"https://example.invalid/posts/{num}" if link else "",
        "message_original":"PRIVATE_RAW_MESSAGE_SHOULD_NOT_APPEAR",
        "published_at_raw":published,
        "geographic_mentions_unverified":["Riau"] if region else [],
        "verified_incident_province":"Riau" if verified else "",
        "candidate_names":["Subject"],"sentiment":"NEGATIVE"
    }

def findings(count=32):
    groups=[]
    kinds=("source_review","discussion","narrative_candidate","source_awareness")
    for num in range(1,count+1):
        kind=kinds[(num-1)%len(kinds)]
        groups.append({"kind":kind,"title":"Saved source",
         "players":{"source_review":["violations"],"discussion":["concerns"]}.get(kind,[]),
         "posts":[source(num,platform=("X","Instagram","TikTok")[num%3],
                          region=(num%6==0))]})
    return groups


def test_balanced_real_evidence_sample_deduplicated_and_bounded():
    plan=build_evaluation_question_plan(findings(35),24)
    assert plan["prepared_questions"]==24
    assert plan["shortfall"]==0
    assert plan["target_questions"]==24
    assert len(plan["questions"])==24
    ids=[x["source_record_id"] for x in plan["questions"]]
    assert len(set(ids))==24
    assert set(x["platform"] for x in plan["questions"])>={"X","Instagram"}
    assert set(x["category"] for x in plan["questions"])>={
        "POTENTIAL_VIOLATION_SIGNAL","PUBLIC_CONCERN",
        "PLATFORM_POLICY_COMPARISON"}
    assert plan["paid_ai_calls"]==0
    assert plan["database_writes"]==0
    assert plan["new_social_crawls"]==0
    assert plan["real_model_answers_generated"] is False
    assert plan["statistically_representative"] is False
    assert plan["window_completeness_verified"] is False
    assert plan["negative_control"]["excluded_from_real_source_count"]
    assert plan["negative_control"]["source_record_id"]=="SOCIAL-0"
    assert "PRIVATE_RAW_MESSAGE_SHOULD_NOT_APPEAR" not in json.dumps(plan)
    assert all(len(x["question"])<1000 for x in plan["questions"])
    assert all("["+x["source_record_id"]+"]" in x["question"]
               for x in plan["questions"])


def test_shortfall_and_missing_categories_are_honest():
    a=build_evaluation_question_plan([{
        "kind":"source_review","posts":[source(14)]
    }],24)
    assert a["prepared_questions"]==1
    assert a["shortfall"]==23
    assert "PUBLIC_CONCERN" in a["missing_categories"]
    assert a["category_available_sources"]["GENERAL_SOURCE_REVIEW"]==1
    assert len(a["questions"])==1
    assert a["questions"][0]["category"]=="POTENTIAL_VIOLATION_SIGNAL"
    assert a["missing_review_tracks"]==[
        "OFFICER_REVIEWED_LEGAL_PDF_QUESTIONS_NOT_SAMPLED",
        "INDEPENDENT_FORMAL_RECORD_MATCH_NOT_VERIFIED"]


def test_duplicate_campaign_link_is_counted_once_preferring_flagged_review():
    a=build_evaluation_question_plan([
        {"kind":"discussion","posts":[source(16,campaign="5")]},
        {"kind":"source_review","posts":[source(16,campaign="6")]}
    ],24)
    assert a["observed_eligible_unique_sources"]==1
    assert a["prepared_questions"]==1
    assert a["questions"][0]["category"]=="POTENTIAL_VIOLATION_SIGNAL"
    assert a["skipped_source_links"]["duplicate_cross_campaign_link"]==1


def test_invalid_or_unavailable_original_sources_not_included():
    a=build_evaluation_question_plan([
        {"kind":"source_review","posts":[source(1,link=False),
          {**source(2),"canonical_source_id":"social:999"},
          {**source(3),"source_url":"javascript:alert(1)"},
          {**source(4),"source_url":"https://user:pass@example.invalid/post/4"},
          source(5)]}
    ],24)
    assert a["prepared_questions"]==1
    assert a["questions"][0]["source_record_id"]=="SOCIAL-5"
    assert a["skipped_source_links"]["missing_or_unsafe_original_url"]==3
    assert a["skipped_source_links"]["invalid_source_id"]==1
    assert _http_url("https://user:secret@example.invalid")==""
    assert _http_url("https://example.invalid/path")=="https://example.invalid/path"


def test_exact_authorized_social_source_does_not_drift_or_recover_unauthorized():
    rows=[
      {"id":"15","relevance_label":"RELEVANT","text_content":"Riau subject A",
       "published_at":"2026-11-11T09:00:00Z","campaign_id":5},
      {"id":"17","relevance_label":"RELEVANT","text_content":"Gibran statement",
       "published_at":"2026-11-12T09:00:00Z","campaign_id":5},
      {"id":"88","relevance_label":"IRRELEVANT","text_content":"Gibran another post"},
    ]
    result,count=_social_select(rows,
       "Summarize source [SOCIAL-15] even if the description says Gibran",limit=20)
    assert count==1 and [x["id"] for x in result]==["15"]
    result,count=_social_select(rows,
       "Summarize inaccessible source [SOCIAL-999999] from Gibran",limit=20)
    assert (result,count)==([],0)
    result,count=_social_select(rows,"Review [SOCIAL-88]",limit=20)
    assert (result,count)==([],0)
    result,count=_social_select(rows,"Compare [SOCIAL-15] and [SOCIAL-17]",limit=20)
    assert count==2 and {x["id"] for x in result}=={"15","17"}


def test_endpoint_denies_unpermitted_and_never_creates_data(monkeypatch):
    from app import assistant_eval_sampling,inbox_radar
    db=dataset()
    try:
        monkeypatch.setattr(inbox_radar,"live_inbox_findings",
            lambda connection,p:(findings(4),{}))
        viewer=db.get(User,2)
        monkeypatch.setattr(assistant_eval_sampling,"profile",lambda conn,user:{
            "status":"Active","permissions":{"view_intelligence":True},
            "province":"Riau"})
        response=Response()
        data=evaluation_questions(response,target=24,user=viewer,db=db)
        assert data["prepared_questions"]==4
        assert response.headers["Cache-Control"]=="private, no-store"
        assert response.headers["X-Evaluation-Generation"]=="NONE"
        monkeypatch.setattr(assistant_eval_sampling,"profile",lambda conn,user:{
            "status":"Active","permissions":{"view_intelligence":False}})
        with pytest.raises(HTTPException) as exc:
            evaluation_questions(Response(),target=24,user=viewer,db=db)
        assert exc.value.status_code==403
    finally:
        db.close()


@pytest.mark.parametrize("target",[0,31,-1,100])
def test_invalid_sampling_target_fails_closed(target):
    with pytest.raises(ValueError):
        build_evaluation_question_plan(findings(3),target)
