"""Cross-check aggregate counts with the already-selected authorized source set.

Read-only presentation diagnostics, never a claim of data accuracy, source truth,
complete monitoring coverage or a comparison of unlike date populations.
"""
from collections import Counter

_VALID_SENTIMENT=("POSITIVE","NEGATIVE","NEUTRAL","UNCLASSIFIED")

def _normalized_sentiment(value):
    val=str(value or "UNCLASSIFIED").upper()
    return val if val in _VALID_SENTIMENT else "UNCLASSIFIED"

def radar_metric_integrity(findings,platform_counts,sentiment_counts,source_total):
    """One original source should contribute once to each aggregate dimension."""
    unique={}
    duplicates=0
    for finding in findings or []:
        for post in finding.get("posts") or []:
            sid=str(post.get("canonical_source_id") or "").strip()
            if not sid:continue
            if sid in unique:
                duplicates+=1
                continue
            unique[sid]=post
    expected_platform=Counter(str(row.get("platform") or "Unknown") for row in unique.values())
    expected_sentiment=Counter(_normalized_sentiment(row.get("sentiment")) for row in unique.values())
    actual_platform=Counter({str(k):int(v) for k,v in (platform_counts or {}).items()})
    actual_sentiment=Counter({str(k):int(v) for k,v in (sentiment_counts or {}).items()})
    mismatches=[]
    if duplicates:mismatches.append("SOURCES_REPEATED_ACROSS_FINDINGS")
    if int(source_total)!=len(unique):mismatches.append("SOURCE_TOTAL_DIFFERS_FROM_DISTINCT_IDS")
    if dict(+actual_platform)!=dict(+expected_platform):
        mismatches.append("PLATFORM_COUNTS_DIFFER_FROM_SOURCE_INVENTORY")
    if dict(+actual_sentiment)!=dict(+expected_sentiment):
        mismatches.append("SENTIMENT_COUNTS_DIFFER_FROM_SOURCE_INVENTORY")
    return {
      "scope":"AUTHORIZED_RECENT_INBOX_RELEVANT_ONLY",
      "distinct_source_count":len(unique),
      "duplicate_source_occurrences":duplicates,
      "platform_sum":sum(actual_platform.values()),
      "sentiment_sum":sum(actual_sentiment.values()),
      "internal_metric_reconciliation_passed":not mismatches,
      "internal_metric_discrepancies":mismatches,
      "sentiment_classification_accuracy_verified":False,
      "all_campaign_captured_period_directly_comparable":False,
      "additional_database_queries":0,
    }

def command_metric_integrity(captured_count,platform_counts,day_counts):
    """Daily chart and platform distribution must share captured-post denominator."""
    platform_sum=sum(int(x) for x in (platform_counts or {}).values())
    daily_sum=sum(int(x) for x in (day_counts or {}).values())
    issues=[]
    if platform_sum!=captured_count:issues.append("PLATFORM_TOTAL_DIFFERS_FROM_CAPTURED")
    if daily_sum!=captured_count:issues.append("PUBLICATION_DAY_TOTAL_DIFFERS_FROM_CAPTURED")
    return {
      "scope":"AUTHORIZED_CAPTURED_PUBLICATION_PERIOD",
      "captured_distinct_posts":int(captured_count),
      "platform_sum":platform_sum,
      "publication_day_sum":daily_sum,
      "internal_metric_reconciliation_passed":not issues,
      "internal_metric_discrepancies":issues,
      "source_truth_verified":False,
      "additional_database_queries":0,
    }
