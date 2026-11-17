"""v164.2 operational social evidence relevance and retrieval boundaries."""
from datetime import date,timedelta
from app.assistant_orchestration import _social_select
from app.assistant_evidence_relevance import social_source_term_score

def post(i,body,**kwargs):
    row={"id":str(i),"text_content":body,"relevance_label":"RELEVANT",
         "campaign_name":"BAWASLU Riau monitoring",
         "author_name":"","topic_labels":[],"candidate_signals":[],
         "published_at":(date.today()-timedelta(days=4)).isoformat()}
    row.update(kwargs)
    return row

def test_recent_metadata_only_post_cannot_outrank_older_direct_evidence():
    rows=[
      post(1,"Statement from Riau about local election procedures",
           published_at=(date.today()-timedelta(days=200)).isoformat()),
      post(2,"Completely unrelated generic statement",
           topic_labels=["Riau"],published_at=date.today().isoformat())
    ]
    chosen,count=_social_select(rows,"Riau",limit=2)
    assert count==2
    assert [r["id"] for r in chosen]==["1","2"]

def test_campaign_label_alone_is_not_topical_match():
    # Both posts are within the authorized campaign, but that campaign label
    # cannot make unrelated contents answer a specific location question.
    rows=[post(1,"Discussion about a cooking competition"),
          post(2,"Field report from Riau")]
    chosen,count=_social_select(rows,"Riau",limit=20)
    assert count==1 and [r["id"] for r in chosen]==["2"]

def test_substring_and_irrelevant_source_do_not_match():
    rows=[post(1,"Keriau does not identify the province"),
          post(2,"Riau evidence",relevance_label="IRRELEVANT"),
          post(3,"Riau evidence",relevance_label="RELEVANT")]
    chosen,count=_social_select(rows,"Riau")
    assert count==1 and [r["id"] for r in chosen]==["3"]

def test_candidate_signal_is_secondary_but_selectable():
    rows=[post(1,"Monitoring narrative with no person mentioned",
               candidate_signals=[{"name":"Gibran"}])]
    chosen,count=_social_select(rows,"Gibran")
    assert count==1 and chosen[0]["id"]=="1"
    assert social_source_term_score(["gibran"],"Gibran mentioned")>\
           social_source_term_score(["gibran"],"Generic narrative",actors=[{"name":"Gibran"}])

def test_hyphenated_geography_and_uppercase_terms():
    score_a=social_source_term_score(["jawa","timur"],"Jawa-Timur",[])
    score_b=social_source_term_score(["jawa","timur"],"Jawa Timur",[])
    assert score_a==score_b>0

def test_dedupe_source_across_campaigns_and_keep_strongest_version():
    rows=[post(7,"Riau concerns",campaign_name="Campaign 1"),
          post(7,"Unrelated post",campaign_name="Campaign 2",
               topic_labels=["Riau"])]
    chosen,count=_social_select(rows,"Riau")
    assert count==1 and chosen[0]["text_content"]=="Riau concerns"

def test_broad_question_retains_bounded_nonrepresentative_sample():
    rows=[post(1,"Electoral dispute"),post(2,"Routine oversight news"),
          post(3,"Off-topic promotional post",relevance_label="IRRELEVANT")]
    chosen,count=_social_select(rows,"What are the main emerging narratives?")
    assert count==2 and {x["id"] for x in chosen}=={"1","2"}

def test_named_id_selection_preserves_existing_strict_authorization():
    rows=[post(13,"Source mentioned"),post(15,"Source mentioned")]
    chosen,count=_social_select(rows,"Compare [SOCIAL-13] to [SOCIAL-15]",limit=20)
    assert count==2 and {x["id"] for x in chosen}=={"13","15"}
    assert _social_select(rows,"Compare [SOCIAL-13] to [SOCIAL-99]",limit=20)==([],0)
