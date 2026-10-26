# Shahrin V11 regression: paired evidence (2026-10-27)

**Scope:** 6 identical development posts already assessed on both versions. No sealed holdout inspection. No extra paid inference. This is a diagnostic, not independent test accuracy.

| QA ID | V10 category | V10 references | V11 category | V11 references | Shahrin |
|---|---|---|---|---|---|
| QA-10146 | Allegations / Violations | QA-16189, QA-18262 | Election Operations | none | Allegations / Violations |
| QA-10211 | Disputes / Legal | QA-25296 | Disputes / Legal | none | Disputes / Legal |
| QA-10444 | Disputes / Legal | QA-9530, QA-11031, QA-3348 | Disputes / Legal | none | Disputes / Legal |
| QA-10649 | Allegations / Violations | none | Allegations / Violations | none | Election Operations |
| QA-11375 | Disputes / Legal | QA-11031, QA-9530, QA-3348 | Disputes / Legal | QA-11031, QA-7499 | Allegations / Violations |
| QA-12269 | Election Operations | none | Election Operations | none | Election Operations |

**Observed score:** V10 4/6 (66.7%), V11 3/6 (50.0%). One prediction changed and it was a regression. V11 dropped all references on QA-10146. This is correlation, not proof that reference suppression alone caused the change (the model is nondeterministic and prompt/context may also differ).

**Root cause of reference loss:** V2 selector filters candidates to lexical Jaccard [0.18, 0.65), requires highest >=0.25, and abstains when top opposite categories are within 0.08. It only returns exemplars from one category and excludes weak/conflicting comparisons. V10 allowed two differently labelled examples QA-16189 and QA-18262: these depict similar subject matter with different author framing. Removing this contrast potentially removed the only useful disambiguation signal in QA-10146.

**Supported conclusion:** V2 retrieval has not improved Shahrin agreement in this paired development subset; keep V10 as observed baseline. The next approach should distinguish category-relevant author framing from neutral event subject, and evaluate the contrast-pair retrieval decision offline before another paid batch.

**Do not:** auto-correct the 105 unsigned human labels, force answers for development QA IDs, inspect sealed holdout or present development agreement as independent accuracy. Future paid tests can remain authorized but should target a newly saved controlled experiment, not repeat V11 unchanged.
