# v164.5 — Smart Radar source-level aggregation

Smart Radar originally assembled its top-level activity, sentiment, candidate and geographic totals by iterating topic findings. Those findings are presentation groupings and may repeat the same saved social source. The displayed dashboard claims a unique-post denominator, so the correct unit is the original authorized social source ID rather than grouped finding occurrences.

The dashboard now derives its platform, sentiment, candidate mention and geography counters from one in-memory authorized-source rollup, deduplicated by `canonical_source_id`. Each source contributes at most once per candidate and location label. Unknown sentiment remains UNCLASSIFIED; a mere geographic mention is not a confirmed incident location. Source URL and findings remain intact. The pre-existing metric-integrity diagnostics still flag duplicate source presentation, but no longer allow it to inflate displayed aggregate counts.

The main keyword cloud now counts a normalized (original source ID, keyword) only once across authorized campaigns. This avoids double-counting when the same social post is linked to multiple campaigns using the same main keyword. No additional database query, model call, record mutation or new QA interface.

Automated tests cover repeated posts across findings, sentiment coverage, actor and geography counting, unverified locations, no content mutation and keyword deduplication. Source-level consistency does not establish factual correctness of sentiment or entity classification.
