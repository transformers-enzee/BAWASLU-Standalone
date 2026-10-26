# V12 complete development assessment: mismatch triage

Date: 2026-10-27. Source: saved V12 result JSON and original development posts in Supabase. **10/13** primary categories match Shahrin. This is iteratively tuned development agreement, **not independent accuracy**. No holdout read or additional AI calls.

## QA-11375 — Disputes / Legal predicted, Allegations / Violations labeled
Original begins with "MK Periksa Perkara PHPU" and predominantly describes MK jurisdiction, legal standing, filing deadline, testimony, and RPH. It mentions unverified accusations about Gibran's eligibility and Bawaslu's inability to access Silon records. The prediction of Legal is defensible by the documented rubric, whereas the analyst label may weight a procedural allegation. Similar exemplars disagree: QA-11031 Legal and QA-9530 Allegations. **Analyst adjudication needed before treating this as a model-only mistake.**

V12 saved `evidence_quote=""`, `evidence_validation="needs_source_review"`. The stored quote is **empty**, not a fabricated quotation. The validator correctly withheld verification; the system should prompt the model to cite a short exact source phrase on future prompt versions. Do not rewrite an old prediction or auto-verify it.

## QA-1408 — Election Operations predicted, Participatory Oversight labeled
Original says Bawaslu staff attended KPU Kota Mataram "pendampingan" so pupils gain firsthand democratic experience *as voters*. It does not explicitly mention citizens supervising the election, training to monitor violations or structured participatory oversight. The classifier chose Operations. Shahrin's Participatory label might use a broader concept of civic engagement. This is a **category-definition gap**, not clearly a retrieval error: V12 used only QA-24070 as reference. Shahrin must clarify whether general school democracy education qualifies as Participatory Oversight.

## QA-22450 — Digital Risks / Information predicted, Voter Register / PDPB labeled
Original discusses Bawaslu Palopo collaborating with Diskominfo to preserve online information integrity, prevent hoaxes and monitor digital space. It does **not** mention voter register, DPT/DPS, PDPB, coklit or voter roll maintenance. V12's Digital Risks category is strongly supported by the original text and exact verified quote. No eligible PDPB exemplar exists in the frozen reference pool. **Highest-priority analyst label clarification**, and do not force the AI to invent a voter-register connection.

## Decision and next steps
- Keep immutable V12 as the best observed development version (10/13), with three unresolved disagreements.
- Do not make rule changes targeted to these development IDs or automatically change any analyst labels.
- Request human review for QA-22450 first, QA-1408 second, QA-11375 third. Human review is **required to resolve target definitions**, but not required to keep evaluating existing development results.
- Before the next paid run, strengthen evidence-quote compliance in a **new** prompt version, if desired. This is source-grounding robustness, not proven category-accuracy improvement.
- A further paid round on the same 13 development labels cannot establish generalization. Keep the sealed holdout sealed until an agreed final evaluation protocol exists.
