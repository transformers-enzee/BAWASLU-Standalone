"""Bounded, authorization-preserving census for Assistant social analytics.

The existing campaignIntelligenceInbox paged path does the SQL eligibility and
jurisdiction checks before pagination. This wrapper does not query any provider,
write records or initiate AI calls. Never report a truncated scan as complete.
"""
from .assistant_orchestration import _social_select, social_evidence, evidence_snapshot

PAGE_SIZE=100
MAX_PAGES=15


def _issue_signal(row):
    """Count accepted live triage signals, never officer-dismissed flags."""
    review=str(row.get("flag_review_status") or "").strip().upper()
    if review=="FLAG_DISMISSED":
        return False
    if review in ("FLAG_CONFIRMED","FURTHER_INVESTIGATION"):
        return True
    # campaignIntelligenceInbox computes is_flagged after checking accepted
    # signal provenance and the latest officer decision; trust that result
    # over raw potential_issues, which may include screened-out suggestions.
    if isinstance(row.get("is_flagged"),bool):
        return row["is_flagged"]
    return bool(row.get("potential_issues"))


def _review_candidate(row):
    # An existing officer flag review takes precedence over model suggestions.
    return _issue_signal(row) and not str(row.get("flag_review_status") or "").strip()


def select_action_evidence(matched_rows, question, limit=20, reserve=6):
    """Keep topical relevance ranking but surface pending review examples.

    Only authorized, query-matched records are eligible. This changes which
    excerpts GPT sees, not population statistics or officer review state.
    """
    from .assistant_officer_action_contract import officer_action_intent
    count=max(0,min(int(limit),20))
    ranked=list(matched_rows or [])
    if not officer_action_intent(question) or not count:
        return ranked[:count]
    pending=[r for r in ranked if _review_candidate(r)]
    pending.sort(key=lambda r:(
        r.get("is_flagged") is True,
        int(str(r.get("id") or "0")) if str(r.get("id") or "").isdigit() else 0
    ),reverse=True)
    priority=pending[:min(count,max(0,int(reserve)))]
    chosen=ranked[:max(0,count-len(priority))]
    used={str(r.get("id")) for r in chosen}
    for r in priority:
        rid=str(r.get("id"))
        if rid not in used:
            chosen.append(r)
            used.add(rid)
    for r in ranked:
        if len(chosen)>=count:break
        rid=str(r.get("id"))
        if rid not in used:
            chosen.append(r)
            used.add(rid)
    return chosen[:count]

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
        page_state=pagination.get("has_more")
        has_more=page_state is True
        if page_state is False:
            complete=True
            break
        if page_state is not True:
            # Missing/inconsistent pagination metadata must never be reported
            # as a completed query-wide scan.
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
    signal_rows=[row for row in matched_rows if _issue_signal(row)]
    pending_rows=[row for row in signal_rows if _review_candidate(row)]
    reviewed_rows=[row for row in signal_rows if not _review_candidate(row)]
    unique_urls={str(r.get("canonical_url") or "").strip().casefold()
                 for r in matched_rows if str(r.get("canonical_url") or "").strip()}
    snapshot.update({
        "potential_issue_signal_post_count":len(signal_rows),
        "unreviewed_issue_signal_post_count":len(pending_rows),
        "reviewed_issue_signal_post_count":len(reviewed_rows),
        "officer_sentiment_override_post_count":sum(
            str(row.get("sentiment_origin") or "").upper()=="OFFICER_CORRECTION"
            for row in matched_rows),
        "unique_source_url_count":len(unique_urls),
        "issue_signal_disclaimer":(
            "Saved potential-issue flags are triage leads, not verified electoral "
            "violations, legal findings, or assigned cases."),
    })
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
