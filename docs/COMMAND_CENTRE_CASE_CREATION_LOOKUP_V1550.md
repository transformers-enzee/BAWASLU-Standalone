# v155.0: Complete duplicate-lookup alignment for real-source officer pilot

The v154.8 pilot preview lookup had eliminated a 250-case cap, but the POST /api/casework/cases path still evaluated up to 50 active assignments for an exact source-and-campaign pair. This release replaces that with a newest-first, SQL permission-scoped single-record lookup and retains a second _visible authorization check. The existing source row lock, relevance recheck, route validation, human confirmation and audit behavior are unchanged.

QA adds isolated tests with 65–70 pre-existing records, cross-officer reuse, avoidance of new audit events, and a bounded SQL selection. No Supabase schema changes or real officer-case writes are needed.
