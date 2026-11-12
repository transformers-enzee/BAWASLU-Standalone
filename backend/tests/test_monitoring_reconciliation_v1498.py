"""v149.8 reporting reconciliation: union all authorized source links."""
from datetime import datetime, timedelta
from app.management_reporting import monitoring_snapshot_from_findings, _safe_csv_cell

NOW=datetime(2026,11,12,12,0,0)
START=NOW-timedelta(days=7)

def post(id,text="Public oversight inquiry",published="2026-11-11T10:00:00Z",
         sentiment="NEGATIVE",platform="X"):
    return {"canonical_source_id":f"social:{id}","message_original":text,
            "published_at_raw":published,"sentiment":sentiment,"platform":platform}

def finding(kind,posts,title,players):
    return {"kind":kind,"posts":posts,"title":title,"players":players}

def test_union_all_signal_categories_and_topic_matches_in_any_link_order():
    p=post(41,text="Unrelated original message")
    reviews=[
        finding("discussion",[p],"Public conversation",["concerns"]),
        finding("source_review",[dict(p)],"Suspected Riau counting irregularity",["violations"]),
        finding("narrative_candidate",[dict(p)],"Recurring election rumors",["narratives"])]
    for items in (reviews,list(reversed(reviews))):
        result=monitoring_snapshot_from_findings(items,START,NOW,"counting")
        assert result["unique_relevant_sources_in_recent_inbox"]==1
        assert result["published_in_period"]==1
        assert result["flagged_potential_violation_posts"]==1
        assert result["public_concern_posts"]==1
        assert result["emerging_narrative_posts"]==1
        assert result["signal_overlapping_sources_in_period"]==1
        assert result["deduplicated_source_links_removed"]==2
        assert result["sentiment_counts"]=={"NEGATIVE":1}
        assert result["platform_counts"]=={"X":1}
        assert result["legal_violations_confirmed"] is False
        assert result["paid_provider_called"] is False

def test_conflicting_valid_publication_dates_count_as_unknown_regardless_of_order():
    p=post(42,published="2026-11-11T10:00:00Z")
    q=post(42,published="2026-10-01T10:00:00Z")
    for rows in ([p,q],[q,p]):
        result=monitoring_snapshot_from_findings(
            [finding("source_review",rows,"Date conflict",["violations"])],START,NOW)
        assert result["published_in_period"]==0
        assert result["publication_date_unknown"]==1
        assert result["source_publication_time_conflicts"]==1
        assert result["flagged_potential_violation_posts"]==0

def test_conflicting_platform_sentiment_and_x_alias_are_explicit():
    a=post(43,sentiment="NEGATIVE",platform="TikTok")
    b=post(43,sentiment="POSITIVE",platform="Facebook")
    for rows in ([a,b],[b,a]):
        result=monitoring_snapshot_from_findings(
            [finding("discussion",rows,"Public conversation",["concerns"])],START,NOW)
        assert result["published_in_period"]==1
        assert result["source_sentiment_conflicts"]==1
        assert result["source_platform_conflicts"]==1
        assert result["sentiment_counts"]=={"UNCLASSIFIED":1}
        assert result["platform_counts"]=={"Unknown":1}
        assert result["public_concern_posts"]==1
    x=monitoring_snapshot_from_findings(
        [finding("discussion",[post(44,platform="twitter-ai-search"),
                               post(44,platform="X")],"Public",["concerns"])],START,NOW)
    assert x["source_platform_conflicts"]==0
    assert x["platform_counts"]=={"X":1}

def test_unknown_date_never_inflates_source_signal_counts():
    a=post(45,published="2026-11-11")
    x=monitoring_snapshot_from_findings([
        finding("source_review",[a],"Potential issue",["violations"]),
        finding("discussion",[dict(a)],"Public concern",["concerns"])],START,NOW)
    assert x["publication_date_unknown"]==1
    assert x["published_in_period"]==0
    assert x["flagged_potential_violation_posts"]==0
    assert x["public_concern_posts"]==0

def test_csv_escapes_whitespace_prefixed_formula_cells():
    for s in ["=SUM(1,2)"," =SUM(1,2)","\t+cmd","\n@HYPERLINK()"," -42"]:
        assert _safe_csv_cell(s).startswith("'")
    assert _safe_csv_cell("Ordinary report title")=="Ordinary report title"
