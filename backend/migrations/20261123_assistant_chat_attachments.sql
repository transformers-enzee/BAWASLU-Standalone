-- BAWASLU v175.84. Apply ONLY to staging Supabase after DBA approval.
-- Private chat attachments, not shared cases. Roll back: DROP TABLE assistant_chat_attachments;
-- Original upload bytes are discarded after malware scan; only bounded source
-- snippets and minimal metadata are retained. Ownership is enforced in API.
CREATE TABLE IF NOT EXISTS assistant_chat_attachments (
    id VARCHAR(36) PRIMARY KEY,
    thread_id VARCHAR(36) NOT NULL REFERENCES assistant_threads(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind VARCHAR(10) NOT NULL CHECK (kind IN ('DOCUMENT','LINK')),
    title VARCHAR(260) NOT NULL,
    url VARCHAR(1900) NOT NULL DEFAULT '',
    source_digest VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'READY',
    extracted_text TEXT NOT NULL,
    sections_json TEXT NOT NULL DEFAULT '[]',
    access_scope_json TEXT NOT NULL,
    retrieved_at TIMESTAMP WITHOUT TIME ZONE,
    created_at TIMESTAMP WITHOUT TIME ZONE
);
CREATE INDEX IF NOT EXISTS ix_assistant_chat_attachments_thread_id ON assistant_chat_attachments(thread_id);
CREATE INDEX IF NOT EXISTS ix_assistant_chat_attachments_user_id ON assistant_chat_attachments(user_id);
-- API database principal should have only necessary CRUD; do not give anonymous users table access.

-- Feedback is tied to a saved assistant response. It stores a hash, rating
-- and optional reviewer note; not the original response or private sources.
CREATE TABLE IF NOT EXISTS assistant_response_feedback (
    id VARCHAR(36) PRIMARY KEY,
    thread_id VARCHAR(36) NOT NULL REFERENCES assistant_threads(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    message_index INTEGER NOT NULL,
    rating VARCHAR(20) NOT NULL CHECK (rating IN ('HELPFUL','NEEDS_IMPROVEMENT')),
    note TEXT NOT NULL DEFAULT '',
    answer_sha256 VARCHAR(64) NOT NULL,
    updated_at TIMESTAMP WITHOUT TIME ZONE
);
CREATE INDEX IF NOT EXISTS ix_assistant_response_feedback_thread_id ON assistant_response_feedback(thread_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_assistant_response_feedback_owner_message
    ON assistant_response_feedback(thread_id,user_id,message_index);
