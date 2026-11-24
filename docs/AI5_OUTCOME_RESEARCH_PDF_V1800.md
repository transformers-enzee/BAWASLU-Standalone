# BAWASLU AI-5 General Research — v180.0 evidence-led research and PDF

## Source artifact: 24 November 2026 pilot PDF
The four-page supplied PDF is titled *Situasi pelanggaran pemilu Indonesia dibandingkan negara tetangga*. It contains eight distinct HTTPS citation targets. The first pages explain Indonesia's administrative oversight, a qualitative Indonesia–Philippines state-resource comparison, regional digital information operations and Timor-Leste's electoral legislation. The discussion groups several countries as insufficiently documented. On page 3, Bawaslu figures for 2024 elections and Pilkada appear only inside "Open questions and evidence limits", not as explained findings in the main analysis. Page 4 contains only a stranded Research Trail continuation and review footer. No historical query list, discarded lead list, full read-page excerpts or exact model input was embedded in the PDF. Those cannot be reconstructed from the export alone.

## Root-cause chain
1. Research planning recognized comparisons but did not require the kind of evidence the question sought. A "situation" or "what happened" question could be answered largely with rules and institutional design.
2. The public reader fetches bounded page excerpts. Before this release synthesis passed only the first 2,800 characters of each retrieved page, even where documented events and counts appeared later in its readable excerpt.
3. The page budget was effectively fixed for narrow and wide questions; source-discovery leads dropped by page selection were not retained in the trace.
4. Final synthesis sometimes summarized risks and caveats, while figures embedded in the evidence or open questions never appeared as substantive, denominated main findings. An answer completeness audit existed but was not deterministic about those caveat-only figures.
5. The PDF always appended Research Trail text, creating the almost empty fourth page.

## Bulk v180.0 improvements
- Generic question-evidence classifier distinguishes OBSERVED_OUTCOMES, INSTITUTIONAL_DESIGN, MIXED and GENERAL. Searches and coverage checks seek actual observed events and outcomes for the first class, and laws/process details for the second. Historical evidence is not silently treated as current performance.
- Scope-scaled bounded candidate budget, up to 30 selected page reads. An initial evidence audit triggers targeted, outcome-oriented follow-up for every meaningful partial/missing dimension. Never count unreadable snippets as evidence.
- Preserve per-search attempted queries, public discovered lead URLs, selection/read status, read failures and omissions due to page caps. Authenticated Research Trail includes actual public passage previews and character counts from model input, plus sent/cited/unreferenced source IDs.
- Select meaningful passage windows from across each available bounded read-page excerpt rather than always sending its introduction. Source packets remain fixed in size and original text only; no generated fake citations.
- Add a conservative guard for concrete numerically sourced findings that appear only in open questions. Rewrite synthesis without unnecessary new web search when the evidence was already retrieved. If an independent audit finds substantive missing answer dimensions, perform a bounded public rescue search followed by one full answer revision.
- Main answer prompt prioritizes findings, dates, examples and correctly labeled counts; distinguishes complaints, findings, sanctions and cases. A requested qualitative comparison is provided even when incompatible denominators prevent ranking. Place material limits where they matter, without repetitious caveat blocks. General Research stays topic-neutral; Use for BAWASLU stays separate.
- PDF default retains main answer, headings, tables, caveats, clickable citation titles/dates and source list WITHOUT a Research Trail appendix. Users may enable "Research Trail appendix (PDF)" per answer. The appendix starts on a new page and groups each query's page selection and each evidence snippet, limiting orphaned audit lines.

## Regression matrix
- Original Indonesian pilot question (event and outcome emphasis across neighbors).
- Unrelated broad coastal storms question (observed impacts on schools, clinics and roads).
- A process/how-it-works control and a mixed question.
- Outcome evidence deep in the retrieved page excerpt, and page selection/trail integrity.
- Numeric results buried in open questions trigger rewrite but not redundant search.
- PDF main and optional appendix text/links, and avoidance of an almost-empty audit-only final page.
- Existing v179.5 through v179.9 AI-5 and wider backend/frontend regression suites continue to run.

All synthetic fixtures test pipelines, not real election findings. A live authenticated AI-5 staging answer plus PDF review remains required for final answer-quality acceptance; no production or Supabase data changes are authorized.

Staging branch: architecture-v2-foundation-20261015.
Build: 180.0.
Expected tag once GitHub Actions publishes: `ghcr.io/transformers-enzee/bawaslu-standalone:staging-180.0`.
The user must save the Render staging image and reply "Saved" for deployment.
