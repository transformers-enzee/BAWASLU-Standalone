"""v148.9: exact-ID evaluations must not retrieve substitute evidence."""
import pytest

from app.assistant_orchestration import (
    _social_select, exact_social_source_ids, exact_social_selection_complete
)
from app.assistant_eval_sampling import _http_url
from app.models import User
from test_management_briefings_v1468 import dataset


def source(id, relevant="RELEVANT"):
    return {
        "id":str(id), "relevance_label":relevant,
        "text_content":"An unverified saved source needing officer review",
        "campaign_id":5, "published_at":"2026-11-11T10:00:00Z"
    }


def test_exact_source_comparison_requires_all_authorized_posts():
    rows=[source(13),source(15),source(17,"IRRELEVANT")]
    assert exact_social_source_ids("Compare [SOCIAL-13] and [SOCIAL-15]")=={"13","15"}
    chosen,count=_social_select(rows,"Compare [SOCIAL-13] and [SOCIAL-15]",limit=20)
    assert {r["id"] for r in chosen}=={"13","15"} and count==2
    assert exact_social_selection_complete("Compare [SOCIAL-13] and [SOCIAL-15]",chosen)
    for question in ("Compare [SOCIAL-13] and [SOCIAL-99]",
                     "Compare [SOCIAL-13] and [SOCIAL-17]",
                     "Using saved source [SOCIAL-0] only"):
        assert _social_select(rows,question,limit=20)==([],0)
        assert not exact_social_selection_complete(question,[source(13)])


def test_source_limit_never_silently_drops_named_ids():
    rows=[source(i) for i in range(1,25)]
    question="Compare "+" ".join(f"[SOCIAL-{i}]" for i in range(1,23))
    assert _social_select(rows,question,limit=20)==([],0)
    assert not exact_social_selection_complete(question,rows[:20],limit=20)


@pytest.mark.parametrize("url",[
    "https://example.invalid/posts/3\njavascript:alert(1)",
    "https://example.invalid/post/3 bad",
    "https://example.invalid\\@attacker.invalid/post/3",
    "https://user:password@example.invalid/3",
    "javascript:alert(1)",
])
def test_question_sampler_rejects_unsafe_original_links(url):
    assert _http_url(url)==""


def test_source_negative_control_does_not_substitute_formal_evidence(monkeypatch):
    """Other authorized formal records must not satisfy an exact missing post."""
    from app import main,domain,campaigns,assistant_knowledge,intelligence_assistant
    db=dataset()
    try:
        user=db.get(User,2)
        monkeypatch.setattr(main,"profile",lambda *_:{
            "status":"Active","permissions":{"view_intelligence":True},
            "province":"Riau"})
        monkeypatch.setattr(domain,"list_intelligence",lambda *_:[object()])
        monkeypatch.setattr(intelligence_assistant,"select_assistant_records",
            lambda *_args,**_kwargs:[object()])
        monkeypatch.setattr(intelligence_assistant,"assistant_evidence_record",
            lambda *_:{"record_id":"INT-999","record_type":"INTELLIGENCE"})
        monkeypatch.setattr(assistant_knowledge,"authorized_reference_catalog",
            lambda *_:[])
        monkeypatch.setattr(assistant_knowledge,"retrieve_chat_knowledge",
            lambda *_args,**_kwargs:[])
        monkeypatch.setattr(campaigns,"campaign_action",
            lambda *_args,**_kwargs:{"findings":[]})
        def prohibit_paid(*_args,**_kwargs):
            raise AssertionError("No paid model may answer a missing exact source")
        monkeypatch.setattr(intelligence_assistant,"generate_general_openai_answer",
            prohibit_paid)
        out=main.intelligence_assistant({
            "question":"For saved [SOCIAL-0] only, report whether evidence exists.",
            "analysisMode":"DATA","responseDepth":"DEEP",
        },user=user,db=db)
        assert out["provider"]["fallback_code"]=="no_matching_evidence"
        assert out["records"]==[]
        assert out["grounding"]["selected_count"]==0
        assert out["grounding"]["scope"]=="AUTHORIZED_EVIDENCE_NO_MATCH"
    finally:
        db.close()
