# v108.9 Command Centre: source-of-truth completeness

All five intelligence players, candidate mention counts, topic distributions,
conversation activity, saved sentiment and saved geographic references are
derived from the same permission-scoped latest Intelligence Inbox assessments.
The Priority Candidate Watchlist is deliberately an **exception**: its officer-
managed profiles and priorities come from the separately permission-filtered
Watchlist registry, while any displayed post mention counts come from Inbox.
Officer priority is not AI risk or proof of wrongdoing.

The frontend mapping now preserves per-finding `sentiment_counts`,
`geo_signal_counts`, and `verified_incident_counts`.
Sentiment distinguishes POSITIVE, NEUTRAL, NEGATIVE and UNCLASSIFIED,
and shows classified coverage without equating missing labels to neutral.
Original source details retain saved sentiment and geographic labels.

The geography panel distinguishes provisional *saved location references*
from incident jurisdictions confirmed by a human officer against an
unchanged source. No province is inferred from author profile, candidate
constituency or monitoring assignment. Absence of confirmed geography means
'not yet verified', not no geographic discussion.

Source-level UI drill-down for sentiment and geographic references reuses
the existing authorized evidence-detail endpoint, with no paid inference.
Backend and frontend regression tests enforce these contracts.
