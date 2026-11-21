"""Bounded, authorization-preserving census for Assistant social analytics.

The existing campaignIntelligenceInbox paged path does the SQL eligibility and
jurisdiction checks before pagination. This wrapper does not query any provider,
write records or initiate AI calls. Never report a truncated scan as complete.
"""
from .assistant_orchestration import _social_select, social_evidence, evidence_snapshot

PAGE_SIZE=100
MAX_PAGES=15

def collect_social_population(db, profile, question, campaign_action,
                              max_pages=MAX_PAGES):
    pages=max(1,min(int(max_pages),MAX_PAGES))
    cursor=None
    all_rows={}
    seen_cursors=set()
    has_more=False
    complete=False
    fetched=0
    for _ in range(pages):
        args={"paged":True,"page_size":PAGE_SIZE}
        if cursor is not None:
            args["cursor"]=cursor
        result=campaign_action(db,profile,"campaignIntelligenceInbox",args)
        rows=result.get("findings") or []
        pagination=result.get("pagination") or {}
        for row in rows:
            rid=str(row.get("id") or "")
            if rid.isdigit() and rid not in all_rows:
                all_rows[rid]=row
        fetched+=len(rows)
        has_more=pagination.get("has_more") is True
        if not has_more:
            complete=True
            break
        next_cursor=str(pagination.get("next_cursor") or "")
        if not next_cursor.isdigit() or next_cursor in seen_cursors:
            # Incomplete on a missing/repeated cursor. Never mark as exhaustive.
            break
        seen_cursors.add(next_cursor)
        cursor=next_cursor
    # Filter in precisely the same way as the AI relevance selector, but
    # without a 20-post cut. Deduplicated source IDs define the denominator.
    matched_rows,matched_count=_social_select(
        list(all_rows.values()),question,limit=max(1,len(all_rows)))
    snapshot=evidence_snapshot([social_evidence(x) for x in matched_rows])
    snapshot.update({
        "basis":"PERMISSION_SCOPED_QUERY_MATCHED_SCAN",
        "population_complete":complete,
        "statistics_post_count":len(matched_rows),
        "analysis_post_count":min(20,len(matched_rows)),
        "matched_pool_count":matched_count,
        "scanned_unique_post_count":len(all_rows),
        "scanned_link_count":fetched,
        "page_size":PAGE_SIZE,
        "pages_limit":pages,
        "statistics_scope":("ALL_MATCHED_AUTHORIZED_RECORDS_IN_PAGED_SCAN"
                            if complete else "MATCHED_RECORDS_IN_INCOMPLETE_PAGED_SCAN"),
        "notice":(
            "Counts cover all matching accessible, eligible saved records in "
            "the completed paged scan; not all online conversation or people."
            if complete else
            "Only matching accessible records scanned so far are counted. "
            "The safety page limit was reached or pagination stopped; "
            "counts are partial, not the whole available dataset."
        ),
    })
    return {
        "matched_rows":matched_rows,
        "matched_count":matched_count,
        "snapshot":snapshot,
        "complete":complete,
        "scanned_count":len(all_rows),
    }
