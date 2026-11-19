# v173.1 — Jurisdiction review bulk performance and direct officer queue

Three integrated functional tracks:
1. Single-pass batch reading for province and city decisions shared by Inbox,
   Social Listening/Watchlist saved views, and jurisdiction readiness. The
   status renderer is shared by the one-source and multi-source endpoints
   to preserve stale/rejected/confirmed/conflicted decision semantics.
2. Campaign-level read-only jurisdiction review queue can be opened without
   selecting an existing post drawer. Source leads open authorized saved
   evidence, and older evidence windows remain navigable. An onClick bug
   passing a synthetic event as a cursor was corrected.
3. Rejected decisions no longer reappear as open review leads. A five-test
   regression suite compares single/bulk statuses, query counts, multi-campaign
   separation, and cross-module equality.

No new permissions, paid provider calls, schema migrations, or changes to
persisted officer decisions. Geography remains officer-confirmed source
context; decision coverage is not a real-world accuracy metric.
