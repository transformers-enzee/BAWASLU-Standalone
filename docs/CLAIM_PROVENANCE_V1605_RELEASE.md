# v160.5 — source-type triage release correction

The v160.4 backend suite found two legacy expectations that omitted policy citation review whenever the prompt was not expressly legal. This is inconsistent with the new intended safeguard, since a platform-policy answer may still cite an electoral-law PDF as supposed provider-rule authority. Both tests now require the review signal regardless of question phrasing, without claiming a platform violation.

The formal-decision/social-only provenance signal is also distinguished from a legal question: when the user merely requests social monitoring, a misleading BAWASLU confirmation claim cited solely to social posts is flagged for **formal-source verification**, not automatically a missing legal-PDF issue. Actual legal questions still require eligible legal references. All conclusions require human checking. No model credits, Supabase data writes or client acceptance actions.
