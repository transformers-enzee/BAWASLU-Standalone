# BAWASLU v149.8 - Reliable saved-source monitoring

## Problem
The optional Command Centre management report previously skipped a canonical post as soon as it appeared in another finding. This made management's issue-category and topic-filter counts depend on which finding appeared first, even though the post could carry several preliminary signals. The first linked record also won any timestamp, sentiment or platform conflicts without disclosure.

## Solution
- Group **authorized, relevant saved Inbox** posts by canonical source ID before applying topic selection or rolling UTC publication windows.
- Count one post once. Merge applicable potential-violation, public-concern and emerging-narrative flags across its linked findings; explain explicitly that these counts overlap and must **not** be summed.
- Include a topic when **any** of the linked authorized posts or finding titles matches the filter. Reversing finding order does not change issue counts.
- When valid source publication timestamps conflict, count the post under unknown publication time, not in an arbitrary reporting period. Conflicting sentiments become UNCLASSIFIED; conflicting platforms become Unknown. Normalized X/Twitter aliases are recognized as one platform.
- Surface deduplicated link counts, overlap counts and metadata conflicts in the management API response. The report UI and common PDF/Word/Excel template methodology explain these limitations.
- Harden CSV export against leading-whitespace spreadsheet formulas.

## Restrictions
All changes are on the existing staging branch architecture-v2-foundation-20261015. No additional provider crawls, paid AI calls, migrations, Supabase schema changes or new top-level UI areas. Existing officer casework and monitoring populations remain separate. The report remains a draft, never a legal or platform enforcement finding.

## Testing
New backend tests cover multi-finding order reversal, topic eligibility, overlapping signals, timestamp conflicts, conflicting sentiment/platform labels, X aliases and CSV formula safety. Existing monitoring preview and export browser tests check the new warning, in addition to the established full-suite CI checks.
