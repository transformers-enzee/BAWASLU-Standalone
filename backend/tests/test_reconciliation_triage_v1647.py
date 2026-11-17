"""Reconciliation distinguishes benign presentation repeat from broken metrics."""
from app.monitoring_metric_reconciliation import radar_metric_integrity
from app.monitoring_count_integrity import inbox_window_integrity

def row(id,**kw):
    p={"canonical_source_id":"social:"+str(id),"platform":"Instagram","sentiment":"NEUTRAL"}
    p.update(kw)
    return p

def raw(id):
    return {"id":str(id),"campaign_id":"1","relevance_label":"RELEVANT"}

def test_repeated_finding_is_not_source_count_failure():
    findings=[{"posts":[row(1)]},{"posts":[row(1)]}]
    m=radar_metric_integrity(findings,{"Instagram":1},{"NEUTRAL":1},1)
    assert m["internal_metric_reconciliation_passed"]
    assert m["reconciliation_state"]=="PRESENTATION_REPEAT_ONLY"
    assert m["presentation_duplicate_occurrences"]==1
    assert m["actionable_metric_discrepancies"]==[]
    assert "SOURCES_REPEATED_ACROSS_FINDINGS" in m["internal_metric_discrepancies"]
    c=inbox_window_integrity([raw(1)],findings)
    assert c["internal_count_reconciliation_passed"]
    assert c["reconciliation_state"]=="PRESENTATION_REPEAT_ONLY"
    assert c["actionable_count_discrepancies"]==[]

def test_conflicting_duplicate_remains_actionable():
    findings=[{"posts":[row(1)]},{"posts":[row(1,sentiment="NEGATIVE")]}]
    m=radar_metric_integrity(findings,{"Instagram":1},{"NEUTRAL":1},1)
    assert not m["internal_metric_reconciliation_passed"]
    assert m["reconciliation_state"]=="METADATA_CONFLICT"
    assert m["actionable_metric_discrepancies"]==["REPEATED_SOURCE_METADATA_CONFLICT"]
    assert "officer overrides" in m["recommended_next_check"]

def test_miscount_always_requires_investigation():
    m=radar_metric_integrity([{"posts":[row(1)]}],{"Instagram":2},{"NEUTRAL":1},2)
    assert not m["internal_metric_reconciliation_passed"]
    assert m["reconciliation_state"]=="METRIC_MISMATCH"
    assert "SOURCE_TOTAL_DIFFERS_FROM_DISTINCT_IDS" in m["actionable_metric_discrepancies"]
    assert "PLATFORM_COUNTS_DIFFER_FROM_SOURCE_INVENTORY" in m["actionable_metric_discrepancies"]

def test_missing_or_unexpected_sources_still_fail():
    empty=inbox_window_integrity([raw(1)],[])
    assert not empty["internal_count_reconciliation_passed"]
    assert empty["actionable_count_discrepancies"]==["MISSING_ELIGIBLE_GROUPED_SOURCES"]
    other=inbox_window_integrity([raw(1)],[{"posts":[row(2)]}])
    assert not other["internal_count_reconciliation_passed"]
    assert set(other["actionable_count_discrepancies"])=={
        "MISSING_ELIGIBLE_GROUPED_SOURCES","UNEXPECTED_GROUPED_SOURCES"}

def test_empty_scopes_are_consistent_without_legal_claim():
    m=radar_metric_integrity([],{}, {},0)
    c=inbox_window_integrity([],[])
    assert m["reconciliation_state"]=="CONSISTENT"
    assert c["reconciliation_state"]=="CONSISTENT"
    assert m["sentiment_classification_accuracy_verified"] is False

def test_unique_matching_source_with_no_repeat():
    findings=[{"posts":[row(7),row(8)]}]
    m=radar_metric_integrity(findings,{"Instagram":2},{"NEUTRAL":2},2)
    c=inbox_window_integrity([raw(7),raw(8)],findings)
    assert m["reconciliation_state"]==c["reconciliation_state"]=="CONSISTENT"
    assert m["internal_metric_reconciliation_passed"]
    assert c["internal_count_reconciliation_passed"]
