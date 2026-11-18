# v170.4: operator-facing queue triage

The existing campaign Assessment operations read-only panel now renders the v170.3 queue_triage response. Seven disjoint queue states display counts and guidance, pending has its own partition, and independently sampled count drift produces a visible warning. Older API responses degrade gracefully to an unavailable message. No queue state-changing actions, paid provider calls, source text or record IDs are introduced. An npm build-gated static contract validates payload consumption and no action trigger.
