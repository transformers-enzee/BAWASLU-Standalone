"""Repeated source disagreements and normalized cloud count regressions."""
from app.monitoring_metric_reconciliation import (
    radar_source_conflicts, radar_source_rollup, radar_metric_integrity,
    keyword_cloud_source_counts,
)

def source(id,**extra):
    row=dict(canonical_source_id="social:"+str(id),platform="Instagram",
        sentiment="NEGATIVE",candidate_names=["Gibran"],
        geographic_mentions_unverified=["Riau"],
        verified_incident_province="")
    row.update(extra)
    return row

def test_identical_repeat_does_not_claim_metadata_conflict():
    post=source(1)
    findings=[{"posts":[post]},{"posts":[dict(post)]}]
    check=radar_source_conflicts(findings)
    assert check["conflicting_distinct_sources"]==0
    assert check["conflicting_fields"]=={}
    assert not check["metadata_conflicts_detected"]
    rollup=radar_source_rollup(findings)
    result=radar_metric_integrity(findings,rollup["platform_counts"],rollup["sentiment_counts"],1)
    assert "REPEATED_SOURCE_METADATA_CONFLICT" not in result["internal_metric_discrepancies"]
    assert "SOURCES_REPEATED_ACROSS_FINDINGS" in result["internal_metric_discrepancies"]

def test_conflicting_saved_versions_flagged_without_double_counting():
    base=source(7)
    changed=source(7,sentiment="NEUTRAL",platform="TikTok",
                   verified_incident_province="Riau",
                   candidate_names=["Anies"],
                   geographic_mentions_unverified=["Jawa Barat"])
    findings=[{"posts":[base]},{"posts":[changed]}]
    conflicts=radar_source_conflicts(findings)
    assert conflicts["conflicting_distinct_sources"]==1
    assert conflicts["conflicting_fields"]=={
       "platform":1,"sentiment":1,"verified_incident_province":1,
       "candidate_names":1,"geographic_mentions_unverified":1,
    }
    assert conflicts["no_source_text_or_identifiers_exposed"]
    aggregate=radar_source_rollup(findings)
    assert aggregate["platform_counts"]=={"Instagram":1}
    assert aggregate["sentiment_counts"]=={"NEGATIVE":1}
    assert len(aggregate["posts"])==1
    check=radar_metric_integrity(findings,aggregate["platform_counts"],
                                aggregate["sentiment_counts"],1)
    assert not check["internal_metric_reconciliation_passed"]
    assert "REPEATED_SOURCE_METADATA_CONFLICT" in check["internal_metric_discrepancies"]
    assert check["repeated_source_metadata"]["conflicting_distinct_sources"]==1

def test_case_insensitive_candidate_and_geography_labels_are_equivalent():
    first=source(5,candidate_names=["Gibran"],geographic_mentions_unverified=["Riau"])
    second=source(5,candidate_names=["GIBRAN"],geographic_mentions_unverified=["riau"])
    assert radar_source_conflicts([{"posts":[first,second]}])["conflicting_fields"]=={}

def test_conflicting_post_count_not_occurrence_count():
    one=source(2)
    two=source(2,sentiment="POSITIVE")
    result=radar_source_conflicts([{"posts":[one,two,two]}])
    assert result["conflicting_distinct_sources"]==1
    assert result["conflicting_fields"]=={"sentiment":1}

def test_keyword_cloud_deduplicates_same_id_and_keyword_across_campaigns():
    records=[
      {"id":"7","campaign_id":"1","text_content":"Pemilu in Riau"},
      {"id":"7","campaign_id":"2","text_content":"pemilu discussed"},
      {"id":"8","campaign_id":"2","text_content":"Another PEMILU discussion"},
    ]
    result=keyword_cloud_source_counts(records,{1:["Pemilu"],2:["pemilu"]})
    assert result=={"Pemilu":2}
    assert sum(result.values())==2

def test_keyword_cloud_no_substrings_or_unscoped_rows():
    rows=[{"id":"1","campaign_id":"3","text_content":"Keriau"},
          {"id":"2","campaign_id":"3","text_content":"Riau monitoring"},
          {"id":"wrong","campaign_id":"3","text_content":"Riau"}]
    assert keyword_cloud_source_counts(rows,{3:["Riau"]})=={"Riau":1}

def test_keyword_cloud_does_not_mutate_source_rows():
    rows=[{"id":"1","campaign_id":"1","text_content":"Riau"}]
    before=[dict(x) for x in rows]
    keyword_cloud_source_counts(rows,{1:["Riau","riau"]})
    assert rows==before
