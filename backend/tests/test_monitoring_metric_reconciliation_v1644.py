"""Aggregate dashboards should be internally coherent without extra reads."""
from app.monitoring_metric_reconciliation import (
    radar_metric_integrity,command_metric_integrity)

def sample(id,platform="Instagram",sentiment="NEGATIVE"):
    return {"canonical_source_id":"social:"+str(id),
            "platform":platform,"sentiment":sentiment}

def test_radar_aggregate_counts_agree_with_unique_source_ids():
    findings=[{"posts":[sample(1),sample(2,"X","NEUTRAL")]}]
    got=radar_metric_integrity(findings,{"Instagram":1,"X":1},
                              {"NEGATIVE":1,"NEUTRAL":1},2)
    assert got["distinct_source_count"]==2
    assert got["internal_metric_reconciliation_passed"] is True
    assert got["additional_database_queries"]==0

def test_radar_miscounted_platform_and_sentiment_are_detected():
    findings=[{"posts":[sample(1),sample(2,"X","NEUTRAL")]}]
    got=radar_metric_integrity(findings,{"Instagram":2},
                              {"NEGATIVE":2},2)
    assert not got["internal_metric_reconciliation_passed"]
    assert "PLATFORM_COUNTS_DIFFER_FROM_SOURCE_INVENTORY" in got["internal_metric_discrepancies"]
    assert "SENTIMENT_COUNTS_DIFFER_FROM_SOURCE_INVENTORY" in got["internal_metric_discrepancies"]

def test_same_source_in_two_findings_is_not_independent_activity():
    f=[{"posts":[sample(1)]},{"posts":[sample(1)]}]
    result=radar_metric_integrity(f,{"Instagram":2},{"NEGATIVE":2},2)
    assert result["distinct_source_count"]==1
    assert result["duplicate_source_occurrences"]==1
    assert "SOURCES_REPEATED_ACROSS_FINDINGS" in result["internal_metric_discrepancies"]
    assert "SOURCE_TOTAL_DIFFERS_FROM_DISTINCT_IDS" in result["internal_metric_discrepancies"]

def test_unclassified_source_sentiment_is_normalized_without_claiming_accuracy():
    f=[{"posts":[sample(1,"TikTok","UNKNOWN")]}]
    result=radar_metric_integrity(f,{"TikTok":1},{"UNCLASSIFIED":1},1)
    assert result["internal_metric_reconciliation_passed"]
    assert result["sentiment_classification_accuracy_verified"] is False

def test_command_platform_and_day_counts_reconcile():
    good=command_metric_integrity(3,{"Instagram":2,"X":1},
                                  {"2026-11-17":2,"2026-11-16":1})
    assert good["internal_metric_reconciliation_passed"]
    assert good["platform_sum"]==good["publication_day_sum"]==3

def test_command_day_or_platform_discrepancy_is_explicit():
    bad=command_metric_integrity(2,{"Instagram":1},
                                 {"2026-11-17":3})
    assert set(bad["internal_metric_discrepancies"])=={
        "PLATFORM_TOTAL_DIFFERS_FROM_CAPTURED",
        "PUBLICATION_DAY_TOTAL_DIFFERS_FROM_CAPTURED"}
    assert not bad["internal_metric_reconciliation_passed"]

def test_empty_scopes_are_coherent_but_not_truth_verified():
    radar=radar_metric_integrity([],{}, {},0)
    command=command_metric_integrity(0,{}, {})
    assert radar["internal_metric_reconciliation_passed"]
    assert command["internal_metric_reconciliation_passed"]
    assert command["source_truth_verified"] is False
