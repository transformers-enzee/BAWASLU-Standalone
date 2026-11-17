"""Cross-check aggregate counts with the already-selected authorized source set.

Read-only presentation diagnostics, never a claim of data accuracy, source truth,
complete monitoring coverage or a comparison of unlike date populations.
"""
from collections import Counter

_VALID_SENTIMENT=("POSITIVE","NEGATIVE","NEUTRAL","UNCLASSIFIED")

def _normalized_sentiment(value):
    val=str(value or "UNCLASSIFIED").upper()
    return val if val in _VALID_SENTIMENT else "UNCLASSIFIED"

def radar_source_rollup(findings):
    """Return one metric contribution per distinct original saved Inbox source.

    The summary may present the same post in several narrative/concern groups.
    Such presentation repeats must not inflate activity, sentiment, candidate
    or location counts. Keep the first authorized source row, preserving its
    original content and governance metadata unchanged.
    """
    unique={}
    repeat_count=0
    for finding in findings or []:
        for post in finding.get("posts") or []:
            sid=str(post.get("canonical_source_id") or "").strip()
            if not sid:
                continue
            if sid in unique:
                repeat_count+=1
            else:
                unique[sid]=post
    sources=list(unique.values())
    platforms=Counter(str(p.get("platform") or "Unknown") for p in sources)
    sentiments=Counter(_normalized_sentiment(p.get("sentiment")) for p in sources)
    candidates=Counter()
    geo=Counter()
    verified=Counter()
    for post in sources:
        # One candidate or geographic label contributes at most once per
        # source; repeated metadata values are not independent mentions.
        candidates.update({str(v).strip() for v in (post.get("candidate_names") or [])
                           if str(v).strip()})
        geo.update({str(v).strip() for v in (post.get("geographic_mentions_unverified") or [])
                    if str(v).strip()})
        province=str(post.get("verified_incident_province") or "").strip()
        if province:
            verified[province]+=1
    return {
        "posts":sources,
        "platform_counts":platforms,
        "sentiment_counts":sentiments,
        "candidate_mentions":candidates,
        "geo_signal_counts":geo,
        "verified_incident_counts":verified,
        "repeat_occurrences":repeat_count,
    }

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
