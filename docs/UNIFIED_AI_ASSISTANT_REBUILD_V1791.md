# SmartRadar v179.1 — Unified AI Assistant rebuild

## Decision and scope

The former **normal AI Assistant** (v178.x) is retired from the primary
\`/ai-assistant\` routes and its API mount. Its old retrieval, prompting and
synthesis implementation is NOT called by the rebuilt route. A fresh
\`app.unified_ai\` backend and \`UnifiedAIAssistant.jsx\` frontend serve the
normal assistant in both workspaces:

- Operations: \`/ai-assistant\` defaults to **Operational**. Lead with what
  the officer should do first; show original permitted source excerpts,
  gaps, possible applicable rules, competent authority, reviewer role,
  proposed milestones and decision/escalation gates.
- Management: \`/management/ai-assistant\` defaults to **Management**,
  available only to an authorised national/provincial leadership role.
  Lead with executive conclusion, evidence-proportionate attention,
  new developments, institutional and geographic implications,
  options, confidence and what leadership should watch.

The Management homepage and fixed, permission-scoped executive brief are
preserved and linked to the rebuilt assistant.

**Navigation exposes one AI Assistant per workspace.** Historical
\`/assistant\`, \`/management/assistant\`, and independent
\`/ai-assistant-v2-new\` direct URLs and APIs are not deleted until
migration/QA is approved; they are hidden from primary navigation and not
used by the rebuilt assistant. Do not delete their storage, active cases or
tests as part of a first deployment.

## One flexible conversation, three linked workflows

1. Research and analysis: source-linked findings; original attributable
   public pages, scoped saved records and optional reference passages;
   allegation, source review, inference and legal-currentness distinctions.
2. Strategy and action planning: proportionate options, benefits and
   trade-offs; conditional recommendations; proposed roles, evidence,
   milestones and review/escalation gates.
3. Drafting and revision: draft memos, leadership briefs and email replies,
   follow-up shortening/audience conversion; editable textarea and copy;
   no sending, legal determination, approval or automatic assignment.

The user can ask any question or explicitly select a workflow. Optional
perspectives are **Auto, Executive, Operational, Research**; they change
emphasis, not authorization or workspace structure.

## Public sources: approved live web search

- The only public research integration used by the new assistant is
  OpenAI Responses \`web_search\`, using the existing configured
  \`OPENAI_API_KEY\`. \`OPENAI_WEB_SEARCH_MODEL\` may optionally specify
  the search model; otherwise \`OPENAI_MODEL\` is used.
- For a question about current developments, last N days/weeks or
  a scheduled/developing story, a fresh bilingual search request is
  followed by an explicit **second newest-update/correction/postponement
  lookup**. Only the current privacy-screened public question goes to the
  search provider; no saved-source passages, user identity or conversation
  history are forwarded as web search context.
- Provider citations are discovery leads. Candidate sources must be
  opened, fetched and extracted from HTTPS pages. DNS is restricted to
  global IPs, connections pin validated addresses with TLS SNI, and
  redirects are revalidated per hop. Readable HTML/PDF is bounded by
  response size and timeout. A blocked or JS-only site remains snippet-only
  or inaccessible; it cannot substantiate current facts.
- Source rows show original title, publication/update date, access status,
  source type, retrieval time, possible duplicates, and a clickable URL.
  Newest substantiated official corrections should override older
  schedules in the answer, with the conflict explained.
- This is **web and publicly indexed social discovery**, NOT a direct
  complete social platform firehose or representative sentiment survey.

Three strict modes:

| Selection | Public retrieval | Saved BAWASLU | Stored PDF refs |
|---|---|---|---|
| Web only (default) | Yes | **No** | **No** |
| Web + SmartRadar | Yes, first | Yes, scoped | Yes, scoped |
| SmartRadar only | No | Yes, scoped | Yes, scoped |

Web-only still authenticates the officer to determine their permissible
workspace; it never opens the saved record collector for research, even
if public search fails or the user asks for an action plan. Changing
source mode in the browser clears conversation context.

## Evidence policy and date handling

- The answer model receives only successfully read pages and explicitly
  selected, permission-scoped saved observations as case-specific factual
  evidence. Snippets/inaccessible sources appear in Research Trail but
  have no claim eligibility.
- All generated source IDs are checked against the server's actual
  eligible source list. Unsupported IDs and URLs are removed. Findings
  without an eligible citation are labelled analytical inference or
  excluded if source-free. A linked claim is **not** certified true.
- Saved Social Listening is always an unverified attributed allegation.
  Human relevance review does not establish legal guilt or document
  authenticity. Saved PDF references are not certified current law.
  Simulated/sample PDFs are excluded from current legal evidence.
- Duplicate canonical URLs and sufficiently similar text are marked
  rather than counted as independent cases. Incident geography is
  unknown unless confirmed. Internal counts must not become national
  social trends without complete comparable denominators.
- "Past 2 weeks" on 24 November 2026 is **11–24 November 2026** for
  inclusive 14-calendar-day bounds in Indonesia. Sources outside an
  explicit period remain visible but cannot substantiate a claim
  *within* that period.
- Apply evidence standards equally across candidates and parties,
  minimise personal information, and never automatically file,
  enforce, send or assign an officer.

## First controlled review: Bryan and Grace

**A human review has not yet been performed.** The following is a script
for Bryan and Grace to complete, not fictional sign-off or synthetic
individual feedback.

### Bryan — Operational officer
1. Use a non-production role with permission-scoped Operations access.
2. Select **SmartRadar only** and ask:
   *"Examine SOCIAL-740 and SOCIAL-1160 as unverified posts. What
   original evidence should the officer check, where can it be found,
   which reviewer should handle it, and what verified legal nexus
   would justify escalation?"*
3. Confirm both records, if within scope, are marked **saved, unverified**
   and not evidence of a legal violation by themselves.
4. Inspect original URLs/excerpts, duplicates, publication versus
   incident date, missing location, possible law and competent authority.
5. Check that a proposed action has a responsible **role**, evidence
   needed, milestone, review point and a conditional escalation gate;
   there must be no actual assignment.

### Grace — Management leader
1. Use an authorised management role and Management homepage.
2. Select **SmartRadar only** and ask:
   *"Based only on SOCIAL-740 and SOCIAL-1160 as explicitly unverified
   observations, what can BAWASLU leadership conclude, when should
   escalation be considered, and is any management decision warranted?"*
3. Confirm an evidence-proportionate attention level, confidence,
   geographic and institutional limits, policy options, review points,
   and a clear distinction between suggested and approved actions.
4. Verify no unsupported nationwide political trend or accusation
   was inferred from two posts.

**If either saved ID is unavailable to that user**, the assistant must
disclose an access/data gap, not manufacture the missing record.
Neither reviewer should claim the posts are independently verified.

### Both reviewers — unrelated question
Each must bring **one different, redacted question** from a BAWASLU
workflow. For each question:
1. Start in **Web only**, confirm no saved record was consulted.
2. Ask for recent official/public coverage, check publication dates
   and whether the quoted newest correction was actually read.
3. Check citations against the opened original pages and note gaps.
4. Request alternative strategies and an action plan (owner, milestone,
   review point), or a leadership memo/email.
5. Request a revision to the draft and verify original caveats remain.
6. Score *Did this answer help you decide or act in your assigned role?*
   and document any unsupported claim or missing next step.

### Review capture sheet

| Reviewer | Assigned role/workspace | Redacted question ID | Sources read / snippet only | Citation accurate? | Recommendation actionable? | Helped decide or act? | Notes |
|---|---|---|---|---|---|---|---|
| Bryan | Operational | TBD | TBD | Pending | Pending | Pending | Human UAT required |
| Grace | Management | TBD | TBD | Pending | Pending | Pending | Human UAT required |

Do not insert unredacted private questions into public search.

## Automated acceptance

- \`backend/tests/test_unified_ai_v1791.py\` tests role restrictions,
  geography labels, Indonesia date windows, private-ID safeguards,
  strict Web-only isolation **including provider failures**, public-first
  mixed mode, snippet exclusion, newer official source prioritisation,
  duplicate saved reports, proposed actions and draft revision.
- \`frontend/e2e/ai-assistant-v2.spec.js\` is repurposed as a controlled
  browser walkthrough for the **new** assistant: mode navigation,
  public-source citations/status, newest correction, action plans,
  role-based Management response and draft follow-up.
- All deterministic fixtures are SIMULATED and do **not** claim a
  current real news article was read or that Bryan/Grace reviewed it.
- Full acceptance still requires an authenticated staging run with
  the configured live provider and human reviewer sign-off.

## Next and later

**Next:** cross-case/geographic/time-period/legal-impact comparisons
with auditable denominators, stronger time-series records, strategic
scenario analysis, management decision proposal register and outcomes.

**Later:** approved operational assignment orchestration, persistent
action status updates, document/email sending after human approval.

No production deployment and no state-changing institutional action
is part of the current rebuild commit.
