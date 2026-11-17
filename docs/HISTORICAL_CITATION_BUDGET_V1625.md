# BAWASLU v162.5 — separate historical audit citation budget from live answer budget

A read-only aggregate query over saved Assistant history on 17 November 2026
found 49 historical replies; 9 have more than 12 unique bracketed source IDs,
and one has 19. The ordinary response grounding function intentionally removes
references after 12 distinct citations, and had been reused by the saved reply
audit. Consequently, even when a historical reply's source IDs were reauthorized
under v162.4, the auditor could discard references 13–19 and report a misleading
overflow warning. This is a diagnostic mismatch, not evidence of factual error.

The grounding function now takes an optional bounded citation_limit parameter:
12 by default, retaining the normal Assistant policy, and at most 20 in the
explicit read-only mixed-source audit. The same current-access checks and
full-source-scope failure policy apply. Citations absent from current authorized
evidence are still removed, not certified. Audit responses identify both limits
and never expose original answer text, question text or source excerpts.
Historical replay itself is bounded at 20 IDs; PDF page lookup retains a
separate 12-page cap. No new AI calls or database writes; no model accuracy
claim or legal determination is implied. The regression suite checks 13, 16,
19 and 20 citation examples, unavailable references, the preserved default
12 limit, and the combined historical card/citation case.
