-- Execute only in the BAWASLU STAGING database.
-- Raw pilot posts are already stored in pilot_smart_radar.source_posts.
CREATE TABLE IF NOT EXISTS pilot_smart_radar.finding_states (
 finding_id text PRIMARY KEY,
 status text NOT NULL DEFAULT 'awareness'
   CHECK(status IN ('awareness','pending','investigating','monitoring','closed','escalated')),
 first_reviewed_at timestamptz,
 next_followup date,
 updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS pilot_smart_radar.review_events (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 finding_id text NOT NULL REFERENCES pilot_smart_radar.finding_states(finding_id),
 action text NOT NULL,
 note text NOT NULL DEFAULT '',
 actor_id text NOT NULL,
 next_followup date,
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS radar_review_events_finding_idx
 ON pilot_smart_radar.review_events(finding_id,created_at DESC);
ALTER TABLE pilot_smart_radar.finding_states ENABLE ROW LEVEL SECURITY;
ALTER TABLE pilot_smart_radar.review_events ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON pilot_smart_radar.finding_states,pilot_smart_radar.review_events FROM PUBLIC,anon,authenticated;
REVOKE ALL ON SEQUENCE pilot_smart_radar.review_events_id_seq FROM PUBLIC,anon,authenticated;
-- Only the trusted backend database connection accesses these tables;
-- frontend browser access through Supabase anon/authenticated is forbidden.
