# Shahrin near-duplicate label-consistency review — 2026-10-27

## Scope

Offline SQL audit of **eligible exemplar posts only** (no sealed holdout and no paid inference). Candidate pairs required distinct source URLs and hashes. Similarity is the existing token Jaccard function, not semantic equivalence.

- 4 exemplar pairs score >=0.50; 2 of these have differing Shahrin labels.
- 3 cross-category pairs score >=0.35.

## Analyst review queue (do not automatically relabel)

| Pair | Similarity | Shahrin labels | Preliminary interpretation |
|---|---:|---|---|
| QA-16189 / QA-18262 | 0.870 | Election Operations / Allegations / Violations | Very similar facts; QA-18262 adds accusatory introductory language. Check whether evaluative framing should control. |
| QA-18262 / QA-20481 | 0.840 | Allegations / Violations / Election Operations | Same factual story; verify framing distinction rather than assuming label mistake. |
| QA-11031 / QA-9530 | 0.355 | Disputes / Legal / Allegations / Violations | Both mention Gibran qualification controversy, but one foregrounds court dispute and the other alleged violations/no-report. Similar topic alone is not a contradiction. |

## Recommendation

Do not correct labels automatically. Ask the human analyst to document the **dominant communicative intent** for the two Bawaslu-allowance contrasts and for the MK-proceedings/violation contrast. Record whether a short opinionated preface outweighs the substantially longer shared factual content.

Keep V11 inference paused until this boundary is clarified. A future retrieval mechanism should group source-story near-duplicates, account for framing changes, and abstain from contradictory labels. The above 3 pairs are *review flags*, not confirmed mistakes.
