# BAWASLU v154.5: Real-evidence pilot workflow hardening

**Baseline:** The previous connected Supabase verification found saved Social Listening and campaign evidence but no officer-created casework. Live data was not modified for this build.

**Why:** v154.4 allowed an authorized officer to choose an existing saved source but had two practical correctness gaps. A duplicated social post across campaigns could select a flagged version with no usable original URL over an authorized version with a valid source. The direct officer POST /api/casework/cases also did not stop repeated submissions of an already-active identical case, even though the frontend usually spotted an existing case.

**Code changes:**
1. The saved-source shortlist now selects a campaign record with **both text and syntactically valid original HTTP(S) URL first**, then prioritizes grounded saved flags, concerns, narratives and awareness. This is **not legal-severity ranking**. Added counts of authorized unique sources with usable prefill information vs those needing source recovery, across the full authorized cached Inbox window, not just the 12-row preview.
2. The direct case-creation endpoint now rechecks officer permission, saved source relevance and validated receiving scope before returning an existing active **visible** case linked to the same source type, source ID and campaign ID. A Postgres row lock on the initiating user's User row serializes concurrent duplicate clicks from that officer (SQLite regression uses the same code path). Active-case reuse does not write new casework, change assignment ownership, replace notes, call AI, or create an audit event. Closed cases remain immutable and can be followed by a newly authorized assignment. Other officers' hidden cases are not disclosed.
3. The existing Inbox embedded casework form displays a correct bilingual **existing assignment opened** message instead of claiming a new assignment was created.
4. The Command Centre pilot shortlist shows the number of source records that can be opened for review and the number requiring source recovery.

**Automated QA:** The new suite checks strong-vs-usable campaign selection, full-cohort counters, repeated saves, unchanged case notes, source relevance loss, unauthorized locations, role visibility, closed-case reopening, and a complete human-permission-aware five-stage path (receiving-officer acceptance, original-source check, report submission and separate independent approval). At least one test exercises the actual saved-Inbox reader rather than a mocked shortlist. All tests run in isolated SQLite fixtures; no real officer signoff can be concluded from them.

**Not included:** automatic assignment, automatic case approval, legal determination, new paid AI calls, schema migration, production casework writes, or actual formal acceptance. Existing casework evidence and report audit protections remain authoritative.
