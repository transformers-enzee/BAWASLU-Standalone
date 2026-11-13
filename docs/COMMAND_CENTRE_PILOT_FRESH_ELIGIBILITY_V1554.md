# v155.4: Latest saved-source pilot eligibility reconciliation

The on-demand officer pilot shortlist originates from the authorized but potentially cached Inbox. The actual casework create endpoint revalidates the current campaign/source link, geographical permissions, and latest relevance. This release performs the same read-only `scoped_post` access/relevance validation on the 12 displayed pilot items at request time.

For a latest irrelevant saved assessment, the shortlist disables its create/continue casework link and directs review to the authorized Inbox source. For a source no longer linked or accessible, it disables both links and clears the previously returned case identifier. No assignment is changed or removed. Counts refer exclusively to the displayed preview, not the full saved-source cohort.

The existing create-case authorization, source row lock, jurisdiction checks, and human approval requirements remain intact. Automated isolated SQLite tests cover latest irrelevance, missing campaign evidence, unchanged eligible source, and no case writes. No migration or paid calls.
