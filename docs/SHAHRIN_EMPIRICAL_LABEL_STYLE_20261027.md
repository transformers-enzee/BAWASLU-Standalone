# Reconstructing Shahrin's decision style from existing labels
Date: 2026-10-27 — evidence-only, no AI paid inference.

## Corpus and safeguards
- 105 matching human-labelled posts exist overall; this study reviewed the 72 exemplar label inventory (66 eligible; 6 previously quarantined), plus the 13 development post excerpts previously examined.
- **No sealed-holdout labels used.** This is an *interpretive hypothesis*, not independently validated accuracy.
- Shahrin labels are reference labels; never automatically rewrite them or use target labels to select live references.

## What can be inferred (not guaranteed)
1. **Classify the specific post, not the general news story.** Neutral Bawaslu staff allowance reports QA-16189 and QA-20481 are *Election Operations*; QA-18262 adds a hostile/accusatory preface to substantially the same report and is *Allegations / Violations*. QA-10146 (development) begins with 'KONSPIRASI' and is also *Allegations / Violations*. Thus framing sometimes changes the primary category.
2. **Court matter foregrounding often favors Disputes / Legal**, including procedural arguments, MK hearings, legal challenges, and evidentiary questions (exemplars QA-11031, QA-11156, QA-11924, QA-12147; development QA-10444 and QA-10211). **Exceptions matter:** QA-9530 and development QA-11375 are *Allegations / Violations* despite discussing nearby events. QA-3348 is *Citizen Reports / Public Concerns*. Do not make 'mentions MK => Legal' a universal rule.
3. **Explicit direct misconduct claims often favor Allegations / Violations** (QA-19690, QA-5284, QA-6166, QA-8525). But QA-7954 and QA-9511 contain strong accusations within legal-hearing narratives and are labelled *Disputes / Legal*. Thus 'any accusation => Allegations' also fails.
4. **Formal electoral work/administration** often favors *Election Operations*: procedures, Bimtek, TPS operations, institutional logistics and official activities (QA-18936, QA-21420, QA-2656, QA-3371). However development QA-10649 (short complaint about TPS workers' deaths and institutional capture) is labelled Operations; lexical accusation-only logic would miss it.
5. **Practical involvement in oversight programs** often favors *Participatory Oversight* (QA-1809, QA-24284, QA-2753, QA-5046; development QA-17924 and QA-1408).
6. **Citizen access, broad concerns and participation messaging** can be *Citizen Reports / Public Concerns* (QA-38359, QA-68377, QA-72997; development QA-14268 and QA-21899). Wording like 'pengawasan partisipatif' appears in both citizen concerns and participation categories, so keyword matching is unreliable.
7. **Information quality / claims about hoaxes** occur as *Digital Risks / Information* (QA-67844), but this category is extremely sparse in eligible exemplars (2). Development QA-50952 (social conversation analytics about a legal dispute) is Digital Risks despite the legal subject.
8. **Voter Register / PDPB** has zero eligible exemplar examples. Development QA-22450 is labelled PDPB although its visible text primarily discusses digital-space coordination; this is a high-priority human-review boundary. Do not invent a robust rule from zero references.

## Why 100% Shahrin agreement is not yet empirically supported
- Shahrin decisions can be context-sensitive, counterintuitive, or inconsistent across similar posts.
- The seven label classes are imbalanced: among eligible exemplars, *Disputes / Legal* is heavily represented, while Digital and Participatory are sparse, and PDPB has none.
- Our nearest-reference baseline is 4/13 on the development cohort. A seven-feature discourse matcher was 2/13.
- These are nearest-exemplar *category agreement* figures, not end-to-end AI predictions. Tuning to the 13 posts can overfit.

## Suggested implementation sequence
1. **No model calls yet.** Track an explicit explanation for every uncertain exemplar/target contrast; record competing labels, post framing, dominant act, and limits of inference.
2. Before a new prompt version, draft category boundary guidelines with *positive and negative* evidence (e.g. 'court mentioned but dominant claim is misconduct'; 'oversight slogan vs actual activity'). Keep these **hypotheses**, not immutable ground truth.
3. Add human review flags for zero-exemplar categories, nearby conflicting examples, short ambiguous statements, and exceptionally strong competing labels.
4. Evaluate candidate category rules on development cases without peeking at holdout, count abstentions and mismatches, and compare against existing baseline. Do not call the paid model until there is credible evidence of improvement.
5. Ask Shahrin later for rulings on genuinely irreducible conflicts. No interview is required to progress on steps 1–4.

## High-priority follow-up questions for eventual human adjudication
- QA-11375 vs QA-11031: why does similar PHPU hearing reporting receive Allegations vs Legal?
- QA-10649 vs QA-19690 / QA-76751: why is an accusatory TPS-related statement Operations?
- QA-14268 vs QA-24284 / QA-38359: what distinguishes inclusive public-concern language from active oversight?
- QA-22450: why PDPB when the visible post is about digital-space coordination?
