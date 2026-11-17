"""Distinct post reconciliation vs recent Inbox window (not equal populations)."""
from app.monitoring_count_integrity import command_period_integrity,inbox_window_integrity
from app.inbox_radar import compile_inbox_findings

def row(post_id,campaign="1",relevance="RELEVANT"):
    return {"id":str(post_id),"campaign_id":str(campaign),
        "relevance_label":relevance,"text_content":"Captured oversight post",
        "canonical_url":"https://example.invalid/"+str(post_id),
        "published_at":"2026-11-17T08:00:00Z","platform":"Instagram",
        "sentiment":"NEUTRAL","topic_labels":["Electoral Operations"]}

def test_command_period_counts_dedupe_sources_and_align_subsets():
    result=command_period_integrity([1,1,2,3],[1,1,2],[1,1],[1,1])
    assert result["captured_distinct_posts"]==3
    assert result["assessed_distinct_posts"]==2
    assert result["relevant_distinct_posts"]==1
    assert result["undismissed_alert_distinct_posts"]==1
    assert result["unassessed_distinct_posts"]==1
    assert result["internal_count_reconciliation_passed"] is True
    assert result["inbox_recent_window_directly_comparable"] is False

def test_command_period_invariants_show_actual_discrepancy_not_fake_zero():
    result=command_period_integrity([1],[1,2],[2],[2,3])
    assert result["internal_count_reconciliation_passed"] is False
    assert "ASSESSED_OUTSIDE_CAPTURED_PERIOD" in result["internal_count_discrepancies"]
    assert "ALERT_WITHOUT_RELEVANT_SOURCE" in result["internal_count_discrepancies"]
    assert result["relevant_distinct_posts"]==0

def test_inbox_groups_unique_source_shared_across_campaigns():
    rows=[row(5,"1"),row(5,"2"),row(6,"2"),row(7,"2","IRRELEVANT")]
    grouped=compile_inbox_findings(rows)
    result=inbox_window_integrity(rows,grouped)
    assert result["eligible_distinct_saved_sources"]==2
    assert result["grouped_distinct_saved_sources"]==2
    assert result["grouped_source_occurrences"]==2
    assert result["source_duplicate_occurrences"]==0
    assert result["internal_count_reconciliation_passed"] is True
    assert result["window_is_exhaustive"] is False

def test_inbox_integrity_flags_duplicate_or_missing_groups():
    rows=[row(5)]
    source={"canonical_source_id":"social:5"}
    findings=[{"posts":[source,dict(source)]}]
    result=inbox_window_integrity(rows,findings)
    assert result["internal_count_reconciliation_passed"]
    assert result["source_duplicate_occurrences"]==1
    assert result["reconciliation_state"]=="PRESENTATION_REPEAT_ONLY"
    assert result["actionable_count_discrepancies"]==[]
    missing=inbox_window_integrity(rows,[])
    assert missing["missing_eligible_sources"]==1
    assert not missing["internal_count_reconciliation_passed"]

def test_inbox_unexpected_source_is_not_silently_counted():
    result=inbox_window_integrity([row(5)],[{"posts":[{"canonical_source_id":"social:9"}]}])
    assert result["unexpected_grouped_sources"]==1
    assert result["missing_eligible_sources"]==1
    assert result["internal_count_reconciliation_passed"] is False

def test_empty_scopes_still_make_denominators_clear():
    assert command_period_integrity([],[],[],[])["internal_count_reconciliation_passed"]
    empty=inbox_window_integrity([],[])
    assert empty["internal_count_reconciliation_passed"]
    assert not empty["all_campaign_captured_period_directly_comparable"]
