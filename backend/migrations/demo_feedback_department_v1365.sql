-- Add optional, self-reported team or department; never collect a visitor name or email.
ALTER TABLE public.demo_feedback ADD COLUMN IF NOT EXISTS department VARCHAR(100) NOT NULL DEFAULT '';
