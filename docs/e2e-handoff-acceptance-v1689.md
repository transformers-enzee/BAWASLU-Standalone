# v168.9 — Functional handoff acceptance: source relevance, radar and case reporting

The national-administrator cross-module acceptance inventory now reports **saved Inbox candidate links** based on newest (assessment_version, ID) relevance, excluding WATCHLIST_ACCOUNT links and preliminary PRISM_PENDING_OPENAI assessments. The underlying intelligence_items table remains separately counted; its population is not a proxy for the campaign evidence feed. HIGHLY_RELEVANT now counts as a valid latest relevance classification, consistent with real Inbox eligibility.

Isolated integration tests call the actual campaignIntelligenceInbox path against saved source and assessment versions, feed the resulting rows through the real Command Center finding compiler, and test a later human relevance change suppresses obsolete evidence. A separate actual management briefing test verifies that submitted officer reports are not counted as approved and no legal outcome is inferred.

All tests use in-memory SQLite and synthetic people/sources. No paid AI, actual Supabase writes or formal client signoff. Authenticated staging UI behavior and human acceptance still require separate validation.
