# v163.6 — Operational AI Assistant historical-answer safety

Previously, reopening a saved chat could display the one-step action desk for a historical last answer with response_profile ACTION_REQUEST. Saved source cards and AI analysis are not proof that evidence or authorization remains current. The action desk now requires the answer's index to be in reviewableIndexes, populated only for a newly generated answer in the current authenticated page session; opening a saved thread clears that set.

Historical replies receive a concise source-staleness caution and a **Prepare fresh source check** action. The control starts a new conversation and pre-fills the original question in DATA (BAWASLU stored evidence) mode, without carrying over old chat context, saved cards or review state. It makes zero AI calls on click. Officers must explicitly press Send to generate a fresh, access-scoped answer before casework actions become available. Old conversations stay saved and unchanged. Existing casework backend confirmation and source authorization remain authoritative.

Internal administrator QA tooling remains restricted; this is a normal operational officer experience improvement. Build regression verifies the historical action gate, no hidden paid call, isolated fresh question, and sequential release metadata.
