# BAWASLU v180.3 — AI-5 General Research qualitative regression recovery

## Pilot evidence (user-uploaded PDFs, reviewed 24 November 2026)
Question: "Situasi pelanggaran pemilu Indonesia dibandingkan negara tetangga".

The **second** attachment (4-page baseline) included country-specific, qualitative regional patterns: Indonesia–Philippines risks of abuse of state resources from International IDEA; Indonesia–Philippines–Thailand information operations, buzzers, trolls, and identity narratives from a StratCom regional study; Indonesia administrative, money-politics, ASN and logistics problems from Bawaslu; and Timor-Leste legal structure. Its comparative numerical ranking was explicitly qualified.

The **first** attachment (3-page regression) retained more numerical detail for Indonesia (separate 2019/2024 categories and counts), Gakkumdu court outcomes, and a Timor-Leste EU mission. But its regional section reduced Malaysia, Timor-Leste and Papua New Guinea mostly to "no comparable data"; the Philippines and Thailand regional observational patterns disappeared.

**Important provenance constraint:** The exports do not contain the exact historical web queries, discovered-but-dropped leads, or source text passed to synthesis. This change therefore fixes two demonstrated software risk points, rather than claiming one specific historical API call was recovered. Since v180.2, the authenticated Research Trail records those detailed stages for future reruns. Original numerical and qualitative source claims remain unverified independently here; the regression fixture treats them as text from user-provided PDFs, not as authoritative facts.

## Identified pipeline risks
1. The initial research search and coverage audit prioritized observed counts and only checked ordinary question dimensions, not whether comparative observations and institutional responses from peers were present. An Indonesia-only statistical result could be marked as enough.
2. The model passage selector rewarded numeric/case vocabulary more than qualitative pattern and institutional-response vocabulary, so a regional study's most relevant passage could be overlooked.
3. The final answer completeness audit looked mostly at explicitly requested obligations; it could accept "no comparable numbers" despite readable peer observations in model input.

## Bulk changes
- For comparative observed-outcome questions on **any topic**, open a separate observation-oriented discovery lane. Run an independent qualitative cross-subject coverage audit on readable excerpts. If not covered, search two bounded peer-focused queries covering firsthand observations, specific incidents, comparative case studies, reactions and institutional responses. Missing comparable statistics does not count as missing qualitative evidence.
- Keep original dimension planning, round-robin page selection, strict READ-only evidence eligibility, source isolation, and bounded page limits. No invented URLs or allegations become verified evidence.
- Expand excerpt scoring to retain both concrete figures and observations, including disinformation, resource abuse, investigative examples and responses, with neutral cross-domain terminology.
- In General Research synthesis, explain observed similarities and differences and their consequences with dates/source context. Preserve useful numerical findings with clear event, denominator and reporting period; state incompatible-metric limitations once without suppressing documented comparisons.
- The final scope audit now receives short previews of the **actual eligible public passages** sent to synthesis. A deterministic guard requests a rewrite when the independent qualitative audit says such evidence is covered but the answer cites none of the observation-lane sources.
- Surface qualitative comparison coverage in the Research Trail. Keep detailed searches, read status, supplied excerpts and citation trail available; do not leak saved internal text.
- Retain the existing optional PDF appendix and clickable citations. No changes to data schemas, permissions, or BAWASLU Action mode.

## Tests
- Exact user pilot question, with simulated Indonesia-only numbers in the first result and two observational studies retrieved through targeted follow-up, ensures both types of evidence reach synthesis.
- An unrelated cross-region coastal-storm question repeats the same mechanism with a different domain.
- Deep in-page observational passages survive ranking even when many statistics precede them.
- A stats-only answer triggers a qualitative omission guard; citing relevant observations clears it.
- Independent scope audit receives the factual observational excerpts and flags a quantitative-only comparison.
- Institutional-design-only questions avoid unnecessary observational discovery.
- Full existing AI-5, backend, frontend, Docker and Playwright tests run before staging release.

**Offline fixture tests do not prove a real model's new factual answer.** A final acceptance replay must occur inside authenticated AI-5 with the same source settings used for both PDFs (the PDFs themselves do not export that setting), followed by side-by-side review and citation clicks.

Staging branch: `architecture-v2-foundation-20261015`.
Build: **180.3**.
Expected GHCR tag: `ghcr.io/transformers-enzee/bawaslu-standalone:staging-180.3`.
No Render deploy until the user saves the image and responds "Saved".
