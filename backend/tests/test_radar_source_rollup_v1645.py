"""Operational Radar aggregate counts use unique saved source posts."""
from app.monitoring_metric_reconciliation import radar_source_rollup,radar_metric_integrity

def source(id,platform="Instagram",sentiment="NEGATIVE",**changes):
    row={
        "canonical_source_id":"social:"+str(id),
        "platform":platform,
        "sentiment":sentiment,
        "candidate_names":["Gibran"],
        "geographic_mentions_unverified":["Riau"],
        "verified_incident_province":"",
        "source_url":"https://example.invalid/"+str(id),
    }
    row.update(changes)
    return row

def test_source_in_multiple_findings_contributes_once_to_every_metric():
    a=source(1,candidate_names=["Gibran","Gibran"],geographic_mentions_unverified=["Riau","Riau"])
    b=source(2,"TikTok","NEUTRAL",candidate_names=["Anies"],geographic_mentions_unverified=["Jawa Barat"],verified_incident_province="Jawa Barat")
    grouped=[{"posts":[a,b]},{"posts":[dict(a)]}]
    result=radar_source_rollup(grouped)
    assert len(result["posts"])==2
    assert result["repeat_occurrences"]==1
    assert result["platform_counts"]=={"Instagram":1,"TikTok":1}
    assert result["sentiment_counts"]=={"NEGATIVE":1,"NEUTRAL":1}
    assert result["candidate_mentions"]=={"Gibran":1,"Anies":1}
    assert result["geo_signal_counts"]=={"Riau":1,"Jawa Barat":1}
    assert result["verified_incident_counts"]=={"Jawa Barat":1}
    check=radar_metric_integrity(grouped,result["platform_counts"],result["sentiment_counts"],len(result["posts"]))
    assert "SOURCES_REPEATED_ACROSS_FINDINGS" in check["internal_metric_discrepancies"]
    assert "SOURCE_TOTAL_DIFFERS_FROM_DISTINCT_IDS" not in check["internal_metric_discrepancies"]
    assert "PLATFORM_COUNTS_DIFFER_FROM_SOURCE_INVENTORY" not in check["internal_metric_discrepancies"]

def test_unknown_sentiment_is_unclassified_not_neutral():
    result=radar_source_rollup([{"posts":[source(1,sentiment="UNKNOWN")]}])
    assert result["sentiment_counts"]=={"UNCLASSIFIED":1}

def test_empty_group_and_missing_id_do_not_create_sources():
    result=radar_source_rollup([{"posts":[source(1),{"platform":"X","sentiment":"POSITIVE"}]}, {"posts":[]}])
    assert len(result["posts"])==1 and result["platform_counts"]=={"Instagram":1}

def test_distinct_source_same_actor_counts_two_sources_not_persons():
    result=radar_source_rollup([{"posts":[source(1),source(2)]}])
    assert result["candidate_mentions"]["Gibran"]==2
    assert len(result["posts"])==2

def test_verification_status_is_not_derived_from_mentioned_geography():
    result=radar_source_rollup([{"posts":[source(1,geographic_mentions_unverified=["Riau"])]}])
    assert result["geo_signal_counts"]["Riau"]==1
    assert result["verified_incident_counts"]=={}

def test_rollup_does_not_modify_original_findings():
    a=source(5); findings=[{"posts":[a]}]
    before=dict(a)
    radar_source_rollup(findings)
    assert findings[0]["posts"][0]==before

def test_keyword_cloud_dedup_contract_uses_original_ids_and_casefold():
    from pathlib import Path
    module=Path(__file__).resolve().parents[1]/"app"/"smart_radar.py"
    code=module.read_text()
    assert "counted_keywords=set()" in code
    assert "pair=(sid,word.casefold())" in code
    assert "if pair in counted_keywords:continue" in code
