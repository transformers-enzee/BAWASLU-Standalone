"""No-credit scoped social analytics regression for >20 posts."""
from app.assistant_social_population import collect_social_population,PAGE_SIZE,MAX_PAGES
from app.assistant_orchestration import _social_select

def rows(count=104):
    sentiments=("NEUTRAL","NEGATIVE","POSITIVE")
    return [
      {"id":i+1,"relevance_label":"RELEVANT",
       "text_content":"Gibran pendidikan dokumen pemilu berita "+str(i+1),
       "platform":"X" if i%2 else "Facebook",
       "sentiment":sentiments[i%3],"published_at":"2026-11-10",
       "topic_labels":["pendidikan"],"engagement_total":i}
      for i in range(count)
    ]

def paged(rows_in,seen=None,broken=False):
    ordered=list(reversed(rows_in))
    calls=seen if seen is not None else []
    def action(db,profile,op,data):
        assert db=="fake-db" and profile=={"geographic_scope":"Nationwide"}
        assert op=="campaignIntelligenceInbox" and data["paged"] is True
        assert data["page_size"]==PAGE_SIZE
        calls.append(data.copy())
        cursor=data.get("cursor")
        initial=0 if cursor is None else next((i+1 for i,x in enumerate(ordered)
                              if x["id"]==int(cursor)),len(ordered))
        page=ordered[initial:initial+PAGE_SIZE]
        has_more=initial+PAGE_SIZE<len(ordered)
        return {"findings":page,"pagination":{
           "has_more":has_more,
           "next_cursor":str(page[-1]["id"]) if has_more and page and not broken else None}}
    return action

def test_104_posts_are_counted_beyond_20_AI_evidence():
    data=rows(104)
    result=collect_social_population("fake-db",{"geographic_scope":"Nationwide"},
             "Gibran pendidikan",paged(data))
    snapshot=result["snapshot"]
    assert snapshot["social_posts"]==104
    assert snapshot["analysis_post_count"]==20
    assert snapshot["statistics_post_count"]==104
    assert sum(snapshot["sentiment_counts"].values())==104
    assert snapshot["population_complete"] is True
    assert len(result["matched_rows"])==104

def test_relevance_is_question_specific_and_deduplicated():
    data=rows(40)
    for x in data[10:]:
        x["text_content"]="No relevant topic; unrelated subject"
    result=collect_social_population("fake-db",{"geographic_scope":"Nationwide"},
             "Gibran pendidikan",paged(data))
    assert result["snapshot"]["social_posts"]==10
    assert result["snapshot"]["population_complete"] is True

def test_explicit_post_id_is_not_replaced_with_other_sources():
    result=collect_social_population("fake-db",{"geographic_scope":"Nationwide"},
             "SOCIAL-6",paged(rows(30)))
    assert [str(x["id"]) for x in result["matched_rows"]]==["6"]
    assert result["snapshot"]["social_posts"]==1

def test_capped_scan_is_flagged_partial_not_full_population():
    result=collect_social_population("fake-db",{"geographic_scope":"Nationwide"},
             "Gibran pendidikan",paged(rows(400)),max_pages=2)
    assert result["snapshot"]["social_posts"]==200
    assert result["snapshot"]["population_complete"] is False
    assert result["snapshot"]["statistics_scope"]=="MATCHED_RECORDS_IN_INCOMPLETE_PAGED_SCAN"
    assert "partial" in result["snapshot"]["notice"].lower()

def test_missing_cursor_cannot_claim_exhaustive_coverage():
    result=collect_social_population("fake-db",{"geographic_scope":"Nationwide"},
             "Gibran pendidikan",paged(rows(150),broken=True))
    assert result["snapshot"]["population_complete"] is False
    assert result["snapshot"]["social_posts"]==100

def test_page_limit_is_bounded():
    assert PAGE_SIZE==100 and MAX_PAGES<=20

def test_no_paid_model_calls_or_mutations_in_population_scan():
    from pathlib import Path
    import app.assistant_social_population as module
    source=Path(module.__file__).read_text()
    for forbidden in ("OpenAI(", "requests.post(", "db.commit(", "execute_prism("):
        assert forbidden not in source
