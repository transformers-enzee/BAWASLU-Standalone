# v173.0 — Repair an outdated frontend contract after off-page review navigation

v172.9 introduced authorized off-page Inbox navigation and replaced the old
"Inspect on visible Inbox page" button with "Inspect source in Inbox".
The v172.8 legacy static contract still asserted the old label, which caused
Playwright QA to stop even though the backend test stage had passed.

This release updates that contract to require the new label and direct
campaign-scoped saved Inbox lookup, adds an explicit migration regression,
and preserves all v172.9 functionality. It makes no database or officer-record
changes and performs no paid AI or SocialCrawl work.
