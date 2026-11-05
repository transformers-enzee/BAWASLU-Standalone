ALTER TABLE public.demo_feedback DROP CONSTRAINT IF EXISTS demo_feedback_message_check;
ALTER TABLE public.demo_feedback ADD CONSTRAINT demo_feedback_message_check
 CHECK (char_length(message) BETWEEN 0 AND 1500 AND (rating IS NOT NULL OR char_length(btrim(message)) > 0));
