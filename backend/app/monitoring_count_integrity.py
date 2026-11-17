"""Read-only, source-ID reconciliation for operational monitoring summaries.

Do not compare a period-scoped all-captured Command Centre population with
the bounded, relevance-filtered recent Inbox feed. No queries, raw content,
provider calls, writes or legal findings.
"""
def command_period_integrity(captured,assessed,relevant,alerts):
    """Validate logical subset relations within ONE permission-scoped period."""
    c=set(captured);a=set(assessed);r=set(relevant);v=set(alerts)
    violations=[]
    if not a <= c:violations.append("ASSESSED_OUTSIDE_CAPTURED_PERIOD")
    if not r <= a:violations.append("RELEVANT_WITHOUT_ASSESSMENT")
    if not v <= r:violations.append("ALERT_WITHOUT_RELEVANT_SOURCE")
    return {
      "scope":"AUTHORIZED_CAMPAIGN_CAPTURED_PUBLICATION_PERIOD",
      "captured_distinct_posts":len(c),
      "assessed_distinct_posts":len(a & c),
      "relevant_distinct_posts":len(r & c),
      "undismissed_alert_distinct_posts":len(v & c),
      "unassessed_distinct_posts":len(c-a),
      "internal_count_reconciliation_passed":not violations,
      "internal_count_discrepancies":violations,
      "inbox_recent_window_directly_comparable":False,
      "monitoring_posts_are_not_formal_incident_findings":True,
      "different_denominators_must_not_be_subtracted":True,
    }

def inbox_window_integrity(raw_rows,grouped_findings):
    """Compare eligible saved source IDs against grouped source IDs in same feed.

    Source IDs from relevance-filtered rows only; repeated campaign links
    must never inflate platform, sentiment or source totals.
    """
    eligible=set()
    for row in raw_rows or []:
        if not isinstance(row,dict):continue
        if str(row.get("relevance_label") or "").upper() not in ("RELEVANT","HIGHLY_RELEVANT"):
            continue
        rid=str(row.get("id") or "")
        cid=str(row.get("campaign_id") or "")
        if rid.isdigit() and cid.isdigit():eligible.add("social:"+rid)
    grouped=[]
    for f in grouped_findings or []:
        for row in f.get("posts") or []:
            sid=str(row.get("canonical_source_id") or "")
            if sid:grouped.append(sid)
    unique=set(grouped)
    missing=eligible-unique
    unexpected=unique-eligible
    return {
      "scope":"AUTHORIZED_RECENT_INBOX_RELEVANT_ONLY",
      "eligible_distinct_saved_sources":len(eligible),
      "grouped_distinct_saved_sources":len(unique),
      "grouped_source_occurrences":len(grouped),
      "source_duplicate_occurrences":len(grouped)-len(unique),
      "missing_eligible_sources":len(missing),
      "unexpected_grouped_sources":len(unexpected),
      "internal_count_reconciliation_passed":not missing and not unexpected and len(grouped)==len(unique),
      "all_campaign_captured_period_directly_comparable":False,
      "window_is_exhaustive":False,
      "different_denominators_must_not_be_subtracted":True,
    }
