# BAWASLU v178.1 — Live Public-Web Search and Read-State Evidence

## Provider and page-reading policy

The approved existing provider is OpenAI Responses API `web_search` (not
Google or an additional service). The search request is configured with
`tool_choice=required` and includes `web_search_call.action.sources`.
It prompts Indonesian and English discovery queries and, for current events
or scheduled proceedings, explicitly asks for the latest updates,
corrections and postponements. The search action/query audit is recorded.
A request for a freshness check is not a guarantee that the page could be read.

Search hits alone DO NOT count as read pages. Backend `assistant_live_web`
opens candidate search URLs with bounded HTML streaming, DNS/public-peer
checks, disabled HTTP redirects and system proxies, content/size/time limits.
The parser extracts page title, primary article paragraphs and published/
updated dates where present.

Each source is classified:
- `READ` — retrieved and parsed sufficient article text; eligible for
  source-grounded current claims and clickable inline citations.
- `SNIPPET_ONLY` — no readable page, but an actual provider snippet exists;
  shown as a lead, not full-page proof.
- `INACCESSIBLE` — no readable page and no attributable snippet.
  Redirects, login blockers and unsupported PDFs are not labeled read.

Publication dates are not inferred from retrieval time. The model receives
READ pages sorted newest first with an explicit instruction to prefer newer
official notices and avoid asserting an event occurred merely because it
was scheduled. Source conflicts remain reviewable.

## Source choice

Both assistant UIs expose:
1. **Web only** — live public retrieval; no internal SmartRadar, PDF library,
   attachments, chat-history evidence or old private draft is supplied to
   answer generation.
2. **Web + SmartRadar** — public-first retrieval and permission-scoped saved
   records; claims must distinguish public and internal sources.
3. **SmartRadar only** — no external public web lookup.

Advanced custom selection remains available for backward-compatible
workflows, with explicit flags. Server-side source presets override stale
checkbox flags and are authorization-preserving. Public web search receives
only the checked, privacy-filtered question, never private evidence.

If public search is disabled, fails, or yields no readable pages, the answer
discloses the gap **before** any saved-record discussion. No fabricated
current fact is substituted for missing web evidence.

## Main answer and research trail

The main response leads with the conclusion and 2–3 useful points, including
BAWASLU relevance and an appropriate next check. The independent assistant
renders read-page citations next to claims and links with page titles.
The expandable Research Trail reports each page's read state, title,
publication/updated dates, retrieval time, links, and search queries.
Legal reference warnings, limitations, charts and validation lists stay
available without bloating the main response.

## Acceptance tests

No-network tests in `backend/tests/test_assistant_live_web_v1781.py`
exercise the actual independent /chat handler with **Web only**, while
injecting mock approved-search output and deterministic page HTTP responses:
- No saved retrieval even if client sends conflicting internal source flags.
- Web search precedes page read and model response.
- Two conflict sources: newer READ official notice is first in model context,
  cited as `[WEB-1]`; older notice remains in Research Trail.
- Search-snippet-only or inaccessible sources never become READ evidence.
- Private network peers, unsafe addresses and redirects are excluded.
- Saved-only never searches; mixed mode clearly discloses failed live search.
- Web-only generation does not ingest old saved conversation text/drafts.

`frontend/scripts/test-assistant-live-web-v1781.mjs` verifies both interfaces,
source-mode controls, inline citations, and source provenance display.

### Required live-provider acceptance (after deployment)

This is **separate** from mocked CI and MUST NOT be marked completed from
source tests alone:

1. In Render staging, open the new **AI Assistant**, choose **Web only**.
2. Ask a *current* question such as: "What is the latest official BAWASLU or
   DKPP announcement this week, and what should an officer verify next?"
3. Confirm public search was actually invoked, source types contain only
   `PUBLIC_WEB`, and at least one source is labeled `Read` with a title,
   publication date when available, and a working citation.
4. For two authoritative notices with conflicting schedules, confirm the
   newest **substantiated READ update** is used; earlier notices are not
   silently described as current.
5. Trigger or simulate an inaccessible site and verify `Snippet only` or
   `Inaccessible` appears; unread pages cannot support definitive claims.
6. Repeat in **Web + SmartRadar** and **SmartRadar only** to verify privacy
   and proper public-vs-saved attribution. If search fails, the answer must
   disclose the gap before discussing saved records.

Credentials and the authenticated officer UI are required for live acceptance.
Do not claim it passed from GitHub Actions alone.

## Deployment and data integrity

Release v178.1, staging branch only. No SQL migrations, account or saved
records changes, case assignments, external messages or formal findings.
Both backend and Dockerfile must use the same release version. The team
updates Render's existing-image source after the full CI pass.
