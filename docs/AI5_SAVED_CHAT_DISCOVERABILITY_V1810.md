# BAWASLU v181.0 — AI-5 Saved Chats usability refinement

## Problem confirmed from the staging screenshot
The saved-chat list was tucked behind a small Saved Chats header button among four equal-weight controls. The screenshot appeared to show "Saved Chats (0)" despite a visible saved item. Users needed additional clicks to find their conversations and the text "Saved chat" did not clearly distinguish the current chat's status from navigation.

## Improved UI
- "Your conversations" is **always visible** immediately below AI-5's header, with the three most recent saved conversations and one-click reopen.
- The current conversation is indicated as "Current chat" alongside its saved title. Rename and delete actions remain alongside each item, with labelled accessible buttons.
- "View all chats" expands the list and offers a search field for larger libraries. "Show recent" collapses it. A loading state, empty-state explanation and retry control appear when needed.
- Header prioritizes **New chat**, **Save chat** (or **Saved** / **Retry save**), and a secondary **Share** action. Shared links live under the conversation navigator instead of competing as a fourth primary action.
- A contextual notice beside the composer reminds the user when the current chat is unsaved and exposes a second **Save this chat** action. Saved chats show "Saved conversation · New replies are saved automatically". Server save errors remain visible and can be retried.
- Removed the old Saved Chats numeric badge, which could be misleading while asynchronous data loaded. The history panel is rendered from one authoritative savedChats state, and refreshes when expanding or reopening.
- Preserves the existing owner-only API, 12-hour behavior for unsaved chats, per-turn auto persistence for saved chats, recipient-only read-only share links, citations, and permission checks. This change does not touch migrations or Supabase records.

## QA plan
- New `frontend/scripts/test-ai5-saved-chats-ux-v1810.mjs` validates persistent saved navigation, recent chat display, all-chat search, clear save indicators, labelled actions and no stale counter.
- Existing saved/share security contract test still runs.
- Existing AI-5 routes, frontend compilation, deterministic backend regression and Playwright suite must pass in GitHub.
- A screenshot and in-browser UAT on Render staging must confirm discoverability, reopen, search, rename, delete, auto-save and mobile responsiveness after the image is deployed.

Branch: `architecture-v2-foundation-20261015`. Version: `181.0`. Candidate image after successful publication: `ghcr.io/transformers-enzee/bawaslu-standalone:staging-181.0`.
Production is untouched. Manual Render image-save handoff is retained.
