ALTER TABLE public.demo_feedback
 ADD COLUMN IF NOT EXISTS network_hash VARCHAR(64) NOT NULL DEFAULT '';
CREATE INDEX IF NOT EXISTS ix_demo_feedback_network_hash ON public.demo_feedback(network_hash);
