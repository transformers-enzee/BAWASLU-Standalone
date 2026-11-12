# v149.9 - BAWASLU Finding Legal & Platform Assessment Source Reconciliation

## Problem
One social post may appear in several authorized campaign links with different original URL metadata. The assessment previously deduplicated on (source ID, URL), so it could count and screen the same post more than once. A separate linked excerpt might contain a material platform-policy review cue that a first-record-only approach misses.

## Implementation
- Group already permission-scoped original posts by canonical source ID, falling back to saved result ID and then URL.
- One canonical source counts once. Evaluate each saved text variant for potential social-media platform policy review cues; when direct and quoted/reporting variants conflict, require contextual officer review.
- Present counts of conflicting excerpt text, original URLs and platform labels. These are unresolved source discrepancies, not verified violations.
- Do not offer invalid or non-HTTP(S) original source URLs as evidence links in the review queue.
- Preserve independently reviewed PDF knowledge retrieval and the separate legal-vs-platform assessments. Neither statutory currentness nor a legal or provider enforcement verdict is established.

## Verification
Backend automated tests include cross-campaign duplicated source links, text-variant disagreements, quotation context, unsafe URL metadata and read-only behavior. No paid model calls, extra crawler work, new database tables or officer actions. Staging only; human legal PDF review and formal acceptance remain pending.
