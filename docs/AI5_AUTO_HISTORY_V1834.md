# BAWASLU v183.4 — AI-5 Automatic Chat History (staging)

## Scope and behavior
AI-5 now creates an owner-private saved-chat record automatically when the first completed reply is returned. All subsequent turns append to the same saved conversation and keep their answers, draft revisions, citation IDs and source metadata. The existing saved-chat database and sharing authorization remain unchanged; no Supabase migration is needed.

### Storage and title
- `app.ai5.persistence.auto_append` now performs an owner-scoped create-on-first-answer, and remains idempotent on repeated turn IDs.
- The title comes from the AI-generated **answer title already produced by the research response**. If that title is empty or generic, it falls back to the user's question. There is **no extra model request, model credit or web search** for chat saving.
- Reopening a saved chat after session expiry or Render restart continues through the existing owner-only saved-chat API and restores recent bounded conversational context.
- The 40-chat and 50-answer limits remain in force. On quota, permission, persistence or size errors, the reply remains on screen and the UI must show **Couldn't save / Retry save**. The user is not told the chat was saved unless the server confirms it.
- `POST /saved` is idempotent for the same owner/conversation ID to permit an interrupted auto-save to be retried safely, without changing a renamed title.

### UI
- The old manual **Save chat** action and title-entry prompt are removed.
- Header displays **Auto-save is on**, with **New chat** and **Share** remaining available.
- The first completed answer appears in **Your conversations** automatically.
- Contextual status shows **Saving**, **Saved automatically** or **Couldn't save — Retry**.
- **Retry save** is shown only after failure, either syncing missing turns into an existing saved chat or creating it from the current in-memory replies.
- Rename/delete, recent chats, search, and one-click reopen remain unchanged. Sharing is still manual and recipient-restricted.

### Privacy and limitations
- All auto-saved records are private to their owner. Current permissions are rechecked on reopen, and restricted evidence is not silently restored into model context after a session ends.
- Uploaded file contents are not persisted in saved-chat records. Sharing remains opt-in and unchanged.
- Existing retention constraints, maximum chat count and deletion behavior remain unchanged; no automatic deletion or new retention period is introduced. Production rollout requires retention policy review if an organization-specific schedule applies.
- Server-side persistence is a database operation only, not a paid AI call.

### Offline QA and staged acceptance
- Synthetic SQLite tests: automatic first answer, continuation, duplicate requests, AI-generated title, fallback title, manual retry idempotency, 40-chat quota, private access, changed permission rejection, and actual AI-5 route reply with saved ID.
- Frontend tests: no manual save prompt, explicit auto-save status, automatic first-chat list refresh, retry-only controls, preserved saved-chat navigation and share safeguards.
- Standard backend, frontend, Playwright and Docker QA remain required.
- Live staging UAT after deployment: ask a first question, see automatic entry, sign out/back in, reopen and continue; test draft, rename and manual sharing independently.

Branch: `architecture-v2-foundation-20261015`.
Release: **183.4**.
Expected GHCR image after successful Actions: `ghcr.io/transformers-enzee/bawaslu-standalone:staging-183.4`.
No Render staging or production deployment until the image has passed CI and the user has saved the image configuration.
