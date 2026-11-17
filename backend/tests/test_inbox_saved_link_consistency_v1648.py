"""Source-level cross-campaign assessment disagreements in bounded authorized Inbox."""
from app.monitoring_metric_reconciliation import inbox_saved_link_consistency

def row(source,campaign,sentiment="NEGATIVE",version=1,relevance="RELEVANT"):
    return {"id":str(source),"campaign_id":str(campaign),
            "sentiment":sentiment,"assessment_version":version,
            "relevance_label":relevance}

def test_real_staging_shape_conflict_not_masked_by_group_dedup():
    # Mirrors the observed aggregate shape, not actual post IDs/content.
    x=inbox_saved_link_consistency([
        row(10,1,"NEGATIVE"),row(10,2,"NEUTRAL"),
        row(11,1,"POSITIVE")])
    assert x["examined_relevant_links"]==3
    assert x["distinct_relevant_sources"]==2
    assert x["multi_campaign_sources"]==1
    assert x["cross_campaign_sentiment_conflict_sources"]==1
    assert x["reconciliation_state"]=="REVIEW_SAVED_SENTIMENT_DISAGREEMENT"
    assert x["additional_database_queries"]==0
    assert x["source_ids_or_text_exposed"] is False

def test_same_source_same_sentiment_is_not_a_conflict():
    x=inbox_saved_link_consistency([row(7,1),row(7,2),row(8,2)])
    assert x["multi_campaign_sources"]==1
    assert x["cross_campaign_sentiment_conflict_sources"]==0
    assert x["reconciliation_state"]=="NO_CONFLICT_IN_SELECTED_FEED"

def test_duplicate_assessment_history_in_same_campaign_not_cross_campaign():
    x=inbox_saved_link_consistency([
        row(7,1,"NEGATIVE",1),row(7,1,"POSITIVE",3),
        row(7,2,"POSITIVE",2)])
    assert x["multi_campaign_sources"]==1
    assert x["cross_campaign_sentiment_conflict_sources"]==0

def test_latest_version_compared_without_rewriting_older_saved_records():
    original=[row(7,1,"NEGATIVE",1),row(7,1,"NEUTRAL",3),
              row(7,2,"NEGATIVE",2)]
    copy=[dict(x) for x in original]
    x=inbox_saved_link_consistency(original)
    assert x["cross_campaign_sentiment_conflict_sources"]==1
    assert original==copy

def test_unassessed_or_irrelevant_links_are_not_misrepresented_as_covered():
    x=inbox_saved_link_consistency([
      row(1,1,"NEGATIVE"),row(1,2,"POSITIVE",relevance="IRRELEVANT"),
      {"id":"2","campaign_id":"3","sentiment":None,"relevance_label":""}])
    assert x["examined_relevant_links"]==1
    assert x["cross_campaign_sentiment_conflict_sources"]==0
    assert x["all_campaign_assessments_examined"] is False
    assert x["unassessed_links_covered"] is False

def test_invalid_source_ids_are_excluded_and_no_sensitive_values_returned():
    x=inbox_saved_link_consistency([
        {"id":"text","campaign_id":"1","relevance_label":"RELEVANT",
         "sentiment":"NEGATIVE","text_content":"PRIVATE"},
        row(2,1,"UNKNOWN"),row(2,2,"UNCLASSIFIED")])
    assert x["examined_relevant_links"]==2
    assert x["cross_campaign_sentiment_conflict_sources"]==0
    output=str(x)
    assert "PRIVATE" not in output
    assert "'id'" not in output
    assert "source_ids_or_text_exposed" in x

def test_empty_source_list_is_bounded_not_a_global_clean_bill():
    x=inbox_saved_link_consistency([])
    assert x["reconciliation_state"]=="NO_CONFLICT_IN_SELECTED_FEED"
    assert x["distinct_relevant_sources"]==0
    assert x["all_campaign_assessments_examined"] is False
