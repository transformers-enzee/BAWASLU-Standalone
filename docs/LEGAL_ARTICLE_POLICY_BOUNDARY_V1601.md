# v160.1 — Claim-local citations and election-law/platform-policy separation

The existing sentence-local article-number safeguard could accept a standalone DOC citation on the immediately following line as locally attributed, without checking whether that cited PDF excerpt actually contained the mentioned article. The audit now applies the same article-number presence check to both inline citations and exactly adjacent standalone citation lines. It never borrows from later narrative paragraphs, unrelated source cards or unselected pages.

A separate conservative legal-question signal flags definitive claims that a named social platform breached community guidelines or platform policy when the claim cites an authorized election-law regulation, SOP or guidance PDF. The legal PDF does not verify the platform provider's latest rules, scope or actual moderation outcome. The signal enters the existing human legal review summary as PLATFORM_POLICY_BOUNDARY at P2 triage priority (not offence severity). Uncertain claims, reported speech, missing/legal-ineligible citations are not treated as definitive rulings.

Synthetic QA covers article cross-page mismatch, paragraph-level attribution, English and Indonesian platform verdicts, hedged claims and source authorization. No provider calls, database modifications, or actual human legal validation are performed.
