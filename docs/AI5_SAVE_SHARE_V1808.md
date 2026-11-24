# BAWASLU AI-5 v180.8 — Save chat and recipient-only Share

## Scope
- **Save chat** in AI-5 header, **Saved Chats** navigation, and owner-only name/open/continue/rename/delete.
- Durable records in `ai5_saved_chats` (Supabase Postgres), independent of 12-hour `ai4.attachments` cache or Render restarts. Server creates saved data from authoritative turns, not user-submitted assistant text; after opt-in, new turns are appended automatically.
- Previous manually edited draft text can be saved on initial opt-in, or updated thereafter. Original answers, titles, source metadata and inline citation IDs remain in snapshots. Limit: 40 saved chats, 50 answers per chat and 1.8 MB per chat, consistent with bounded existing assistant-history storage.
- Reopening validates current active SmartRadar intelligence permission. Restricted material additionally requires the same access fingerprint. Attachment file bytes and extracted text are **never** copied to saved chats; attachment-based answers remain displayable but their expired evidence must be reattached before citation-backed revision or export. Restored internal evidence cannot silently become fresh factual model input.
- **Share chat** header and **Share** beside each answer. Choose one answer or conversation-so-far, colleague emails, optional Research Trail, and expiry (1/7/30 days). Server previews exactly the frozen selected content and validates recipients and access. A preview digest prevents unnoticed changes before publication.
- Conservative first-release boundary: only WEB_ONLY answers without any uploaded or internal evidence can be shared. A mixed/private or attached answer is explicitly blocked and sender can narrow selection. Both recipient allowlist and current permissions are rechecked at every link opening.
- Link opens authenticated read-only route `/ai-5?share=<opaque-token>` and is not tied to the original session. Later edits/messages do not change copies. Copy, email draft and WhatsApp draft buttons never send automatically. Link is revocable at any time and expires independently. Revoke, delete chat, or observed expiry destroys shared snapshot data (minimal metadata retained for audit).
- Sharing does not expose any attachment bytes, source private excerpts, full internal Research Trail, or the original editable chat. Links are 122-bit UUID4 tokens, stored as SHA-256 digests. Sender can copy again from Shared Links.

## Data access
Two new additive tables: `public.ai5_saved_chats`, `public.ai5_shared_snapshots`. Both enable RLS and revoke direct `anon`/`authenticated`/PUBLIC grants. SmartRadar uses its own server-issued bearer sessions and integer `users.id`, **not** Supabase Auth JWTs, so an `auth.uid()` policy would be incorrect. The privileged backend Postgres connection performs explicit owner, recipient, active AccessGrant, and source checks. No frontend secret is embedded.

Migration: `database/migrations/20261124090000_ai5_saved_shares_v1808.sql`. This migration must be applied explicitly before deploying the new image; staging has `BAWASLU_STARTUP_READ_ONLY` set, so auto-DDL is intentionally disabled. The migration is additive and does not touch existing officer casework or assistant threads.

## Acceptance
- Save with draft edits, clear the in-process cache (simulate app restart/12-hour expiry), reopen and continue; re-open again and verify new server turn persisted.
- Owner-only rename, draft update and delete; another user gets 404.
- Share only one answer; recipient can open exactly that answer independently, not the rest. Unselected and later material are absent.
- Unlisted colleague gets 403; inactive recipient is denied; unauthenticated requests require existing SmartRadar sign-in.
- Share preview flags restricted sources/unknown recipients. Narrowing to a safe public answer succeeds.
- Revoked or expired link returns 404 and frozen content is wiped. Deleting saved chat revokes its shares.
- Frontend navigation/recipient preview/Email/WhatsApp and PDF source links retain existing AI-5 behavior.
- Full backend, frontend, Playwright and Docker QA must pass. Manual cross-account staging acceptance still required.

Release branch: `architecture-v2-foundation-20261015`.
Build: `180.8`.
GHCR tag after successful workflow: `ghcr.io/transformers-enzee/bawaslu-standalone:staging-180.8`.
No automatic Render deployment. User must save the image and reply **Saved**.
