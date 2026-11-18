# v167.2 — Superseded lifecycle consistency

The read-only reconciliation preview now separately reports queue jobs already superseded from earlier classifications and those whose **latest** classification has subsequently changed to UNASSESSED or disappeared. These are review flags, not safe evidence for automatic provider replay. The worker continues to require PENDING before a new claim. The interrupted-job lifecycle inventory and campaign Assessment Operations panel now display SUPERSEDED_ASSESSED separately from completed AI jobs.

No live reconciliation is executed, source records and usage history are unchanged, and provider requests remain prohibited by this audit. Synthetic tests exercise human revision after supersession, missing assessments, watchlist/campaign isolation and preservation of terminal queue state.
