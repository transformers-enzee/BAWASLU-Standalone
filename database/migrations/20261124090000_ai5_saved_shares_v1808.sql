-- BAWASLU AI-5 v180.8: durable owner-private chat and read-only share snapshots.
-- Additive only. No changes to existing officer records or legacy assistant_threads.
-- SmartRadar uses application-issued SessionToken auth (integer users.id), NOT
-- Supabase Auth JWTs. The public Data API must have no grants on these tables.
-- All owner/recipient checks run in the authenticated FastAPI service.
BEGIN;

CREATE TABLE IF NOT EXISTS public.ai5_saved_chats (
    id varchar(36) PRIMARY KEY,
    owner_user_id integer NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    conversation_id varchar(36) NOT NULL,
    title varchar(160) NOT NULL,
    turns_json text NOT NULL DEFAULT '[]',
    draft_revisions_json text NOT NULL DEFAULT '{}',
    scope_fingerprint text NOT NULL DEFAULT '',
    created_at timestamp without time zone NOT NULL DEFAULT (now() AT TIME ZONE 'UTC'),
    updated_at timestamp without time zone NOT NULL DEFAULT (now() AT TIME ZONE 'UTC'),
    CONSTRAINT uq_ai5_saved_owner_conversation UNIQUE(owner_user_id, conversation_id)
);

CREATE INDEX IF NOT EXISTS ix_ai5_saved_chats_owner_user_id
    ON public.ai5_saved_chats(owner_user_id);
CREATE INDEX IF NOT EXISTS ix_ai5_saved_chats_owner_updated
    ON public.ai5_saved_chats(owner_user_id,updated_at DESC);

CREATE TABLE IF NOT EXISTS public.ai5_shared_snapshots (
    id varchar(36) PRIMARY KEY,
    sender_user_id integer NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    conversation_id varchar(36) NOT NULL,
    token_digest varchar(64) NOT NULL UNIQUE,
    scope varchar(18) NOT NULL CHECK (scope IN ('ANSWER','CONVERSATION')),
    snapshot_json text NOT NULL,
    recipient_user_ids_json text NOT NULL,
    expires_at timestamp without time zone NOT NULL,
    revoked_at timestamp without time zone NULL,
    created_at timestamp without time zone NOT NULL DEFAULT (now() AT TIME ZONE 'UTC')
);

CREATE INDEX IF NOT EXISTS ix_ai5_shared_snapshots_sender_user_id
    ON public.ai5_shared_snapshots(sender_user_id);
CREATE INDEX IF NOT EXISTS ix_ai5_shared_snapshots_sender_created
    ON public.ai5_shared_snapshots(sender_user_id,created_at DESC);
CREATE INDEX IF NOT EXISTS ix_ai5_shared_snapshots_expires_at
    ON public.ai5_shared_snapshots(expires_at);

ALTER TABLE public.ai5_saved_chats ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ai5_shared_snapshots ENABLE ROW LEVEL SECURITY;

-- Zero direct browser/Data API access. There is no JWT-to-SmartRadar-user
-- mapping; permissive auth.uid() policies would be an authorization error.
REVOKE ALL ON TABLE public.ai5_saved_chats FROM PUBLIC, anon, authenticated;
REVOKE ALL ON TABLE public.ai5_shared_snapshots FROM PUBLIC, anon, authenticated;

COMMENT ON TABLE public.ai5_saved_chats IS
'SmartRadar AI-5 opt-in saved conversations. App-only authenticated owner API; 40-chat cap and manual deletion consistent with assistant_threads.';
COMMENT ON TABLE public.ai5_shared_snapshots IS
'Frozen read-only public-research AI-5 shares; recipient allowlists, expiry and immediate revoke enforced by FastAPI. No direct Data API access.';

COMMIT;
