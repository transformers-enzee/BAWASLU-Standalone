# Shahrin category-boundary evidence: three hard cases

Development-only analysis, 2026-10-27. These are **interpretive hypotheses**, not validated Shahrin instructions. Sealed holdout not inspected. No model inference or changes to original human labels.

## QA-10649 — Election Operations vs Allegations / Violations
- **Shahrin:** Election Operations; **AI:** Allegations / Violations.
- Source is a very short, hostile reference to hundreds of TPS workers reportedly dying and to KPU/BAWASLU as "TERMUL TERSTRUKTUR". The strong evaluative tone naturally resembles an allegation.
- Counterevidence: QA-76751 is also Shahrin-labelled Operations despite an accusatory account about TPS deaths; QA-19690 is Allegations for a more explicit claim that KPU and Bawaslu "sudah curang".
- **Working hypothesis:** Shahrin sometimes assigns institutional/TPS conditions to Operations when no *specific verifiable electoral wrongdoing* is stated, despite a hostile tone. The model needs to distinguish institutional condemnation from an explicit misconduct proposition.
- **Confidence:** low. Do not hard-code an exception by post ID, author, or phrase.

## QA-11375 — Allegations / Violations vs Disputes / Legal
- **Shahrin:** Allegations / Violations; **AI:** Disputes / Legal.
- Source is structured as an MK/PHPU hearing report emphasizing legal standing, deadlines, and documentation, with a mention of Silon access limitations and the absence of identified violations.
- QA-11031 shares substantial hearing facts but is labelled Legal. QA-9530 emphasizes absence of reported violations and is labelled Allegations. This suggests a framing boundary, but not a reliably recoverable universal rule.
- **Working hypothesis:** Evidence about alleged procedural/verification failure can take precedence over the courtroom setting in selected reports. Yet legal-content dominance remains substantial and the human rationale is unknown.
- **Confidence:** low. Flag as *not identifiable from nearby labels alone*. Do not bias every MK post toward Allegations.

## QA-14268 — Citizen Reports / Public Concerns vs Participatory Oversight
- **Shahrin:** Citizen Reports / Public Concerns; **AI:** Participatory Oversight.
- Source urges inclusive electoral understanding and participation, particularly for disabled and older voters. It does not describe a concrete organized supervision action.
- QA-21899 (similar inclusive language) is also Citizen Reports. QA-24284/QA-2753 describe actual partnerships to train or involve youth in participatory supervision and are Participatory Oversight.
- **Working hypothesis:** An inclusion/access appeal or general aspiration goes to Citizen concerns; an *actual program, training, organized monitoring or structured supervision event* goes to Participatory Oversight.
- **Confidence:** moderate within development; requires independent validation.

## What not to do
- Do not automatically flip the human labels, mark awaiting analyst signoff as confirmed, or invent Shahrin explanations.
- Do not use held-out target gold labels in retrieval at inference time.
- Do not spend inference credits solely to test a hypothesis that was reverse-engineered from 13 development examples.
- Do not interpret 'flagged for human review' as 'excluded from development scoring': the paid tuning runner still enumerates development-cohort candidates; only separate exemplar eligibility filtering blocks reference use.

## Next experiment design
1. Use immutable v11 as the historical comparison point and maintain the paid-v2 gate.
2. Add *category-independent evidence features* only after verifying that they improve decisions on development examples in a blind procedure; avoid special-casing these three IDs.
3. For the first **authorized** paid AI batch, score 1 development post, inspect returned exact source quote and its classifier rationale, stop if malformed or ungrounded.
4. Keep the final holdout sealed, and ask Shahrin later about irreducible contradictions.
