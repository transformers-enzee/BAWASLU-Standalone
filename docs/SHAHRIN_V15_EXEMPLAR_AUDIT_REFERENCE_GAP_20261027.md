# Larger-sample Shahrin QA audit: no-reference bug and controlled correction

Date: 2026-10-27. Source: `pilot_smart_radar.qa_ai_assessments`, `qa_shahrin_exemplars`, `qa_source_posts`, and definitions of private SQL functions. No paid API calls for this investigation. **Do not interpret these exemplar audits as independent accuracy.**

## Paired comparison (same first 30 eligible exemplar targets)

- V14 historical audit: **17/30 = 56.7%**.
- V15 historical audit: **19/30 = 63.3%**.
- V15 versus V14: **3 fixes, 1 regression**, net +2 matching posts.
- Total historical V14 audit: **28/45 = 62.2%**.
- Total historical V15 audit: **19/30 = 63.3%**.
- V15 first 15: 10/15 = 66.7%; not a substantial breakthrough.
- Model on both audit runs: `gpt-5.6-luna` (not necessarily the cheaper model previously assumed).
- V15's 3 fixes: QA-25261 (PDPB -> Operations), QA-3379 (Participatory -> Operations), QA-62746 (Participatory -> Operations).
- V15's regression: QA-5463 (Allegations -> Operations), where the text alleges Bawaslu is susceptible to bribes.

## Root cause: both historical audits had zero few-shot references

All **45/45** V14 historical exemplar-audit posts and **30/30** V15 exemplar-audit posts have `qa_reference_ids=[]`. This was a **real instrumentation error** rather than merely a conservative reference quality threshold.

The audit runner called `reference_examples_for_record`, which invokes the private SQL `qa_shahrin_examples_for_post`. That SQL explicitly restricts its targets to cohort `development` or `sealed_holdout`, and returns **nothing** for cohort `exemplar`. Casting the Python target dict to `development` does not alter its SQL cohort. Therefore, the audit unintentionally ran a **zero-reference ablation**, not the same reference-enabled protocol as the normal V14 development testing.

A no-credit probe across the 55 fixed, SHA256-sorted eligible exemplar targets using the existing `qa_shahrin_examples_for_text` instead found:
- 16 targets with no qualifying lexical reference;
- 14 with one candidate;
- 25 with two candidates.

These are pre-validation candidate counts: later independent-source/eligibility checks may reduce the number actually sent to the model. They are **not** AI agreement scores.

## Corrected V16 protocol

- V16 contains exactly **the same immutable classification instructions as V15** (database hash and equality checked).
- Unlike the historical V14/V15 exemplar audits, V16 uses a dedicated *text-based* reference lookup on the exemplar source, with strict cohort checks, eligible exemplars, different QA ID/source hash/source URL, matched human-category metadata, and at most two diverse references.
- Preserves the fixed 55-post audit target ordering, the ordinary 13-post score, and historical V14/V15 assessment records.
- Stores V16 results under the separate `qa-exemplar-audit-v16` key, with reference IDs/count/fingerprint and `qa_audit_protocol=exemplar_text_lookup_v16`.
- Do **not** continue buying historical V14/V15 exemplar batches: their reference configurations are not comparable to normal V14 tuning.
- Do **not** assume V16 will beat 63.3% until it is evaluated. Start with one controlled capped batch and examine actual reference count alongside paired categories.

## Remaining limits

This is an **in-sample** exercise: the exemplar labels informed the Shahrin calibration design. Self-reference and identical source exclusion reduce leakage but do not make the cohort a truly unseen test. Historical human labels remain unchanged. The designated sealed holdout is not used by the new audit.
