# BAWASLU v181.1 — AI-5 Saved Chats discoverability final frontend QA fix

v181.0 redesigned Saved Chats visibility and ease of use. The isolated frontend pipeline reported a compatibility failure in the existing Save/Share UI contract: it expected the phrase `Share chat`, but the revised visible action had been shortened to `Share`.

v181.1 retains the clearer visible button `Share`, while setting its accessible name to `Share chat`. This is useful for screen readers and makes existing user flows discoverable without reintroducing crowded toolbar labels. No backend or database changes.

Retained UI changes: permanent **Your conversations** section with recent saved chats, search and view-all, active-chat marker, primary New chat / Save chat actions, clear automatic-save and unsaved statuses, contextual save prompt by the composer, smaller Shared links control, and no stale Saved Chats counter.

Backend and frontend checks, Docker build and full Playwright QA must pass before publishing the verified GHCR image. Render staging and production remain unchanged. Target image after GitHub success: `ghcr.io/transformers-enzee/bawaslu-standalone:staging-181.1`.
