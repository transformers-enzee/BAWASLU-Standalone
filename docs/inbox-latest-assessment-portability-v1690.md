# v169.0 — Latest Inbox assessment is deterministic on PostgreSQL and SQLite

The legacy Inbox used SQLAlchemy `distinct(result_id)` combined with descending assessment versions. On PostgreSQL this compiled to DISTINCT ON, but SQLite ignored the DISTINCT ON field and could yield multiple assessment versions. A dictionary comprehension then overwrote the newest record with the oldest, exposing sources that had been revised to IRRELEVANT. The SQL now explicitly restricts the joined assessment to the newest (assessment_version, id) via a correlated scalar subquery, matching the paginated Inbox and inventory semantics. 

Regression tests exercise actual campaignIntelligenceInbox and Command Center finding compilation against versioned relevant/irrelevant evidence. No live evidence is changed; no provider call or credit usage is authorized.
