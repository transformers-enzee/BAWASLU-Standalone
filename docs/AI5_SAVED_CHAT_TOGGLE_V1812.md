# BAWASLU v181.2 — AI-5 Saved Chats view-all refinement

## User-visible fix
The staging screenshot showed the same two saved conversations before and after clicking "View all chats". The control was redundant because the default list already showed up to three conversations.

- For 0–3 saved chats, show all saved chats directly and omit View all chats / Show recent entirely.
- For 4+ saved chats, show the three most recent and offer a single "View all chats (N)" control with the real library size. In expanded view, show all saved chats, reveal search, and provide "Show recent" to collapse.
- Remove the duplicate "See all N saved chats" shortcut.
- Retain owner-private rename/delete, one-click opening, and existing backend logic.
- Strengthen the active chat border and add `aria-current` plus a visible "Current" marker, without exposing saved-chat contents to other users.
- Prevent a stale expanded search state from hiding chats when the library shrinks back to three.
- Preserve empty/loading/error states; hide View all while loading or if the chat list has failed to load.

## Tests
The shared `src/lib/ai5SavedChats.js` pure helper supports executable Node regression cases for 0,1,2,3,4,5,12 and 40 chats, view expansion and collapse, case-insensitive search, and shrink-to-three behavior. The existing saved/share UI contract and the broader frontend/backend/Playwright suites run unchanged.

Build: **181.2**. Staging branch: `architecture-v2-foundation-20261015`.
No Supabase migration, permission change or officer record mutation. Deployment requires saving the verified GHCR `staging-181.2` image in Render and replying "Saved"; the current staging image stays unchanged until that action.
