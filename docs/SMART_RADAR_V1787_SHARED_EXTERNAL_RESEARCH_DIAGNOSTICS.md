# SmartRadar v178.7 — Troubleshooting external knowledge in both AI assistants

## Root causes in source
Both assistant UIs now default to WEB_ONLY, but both rely on
`assistant_orchestration.research_public_web` for OpenAI web discovery.
It used to return `None` for every provider/network/incomplete/no-citation
failure, without preserving the reason. No source URL is admitted unless the
provider actually ran a web search and returned attributable HTTPS links.

A second gate, `assistant_live_web.verify_public_pages`, requires safe HTTPS,
verified public DNS and public connection peer, no redirect, and enough HTML
article text. A completed search may therefore still result in no READ pages.
Existing offline CI uses mocked HTTP/search responses; a passing build does
not certify that the deployment can retrieve external news.

The existing Intelligence Assistant also retains a historical record-only
path when older clients omit source controls, plus special DATA/PDF/case
response profiles. The separate AI Assistant uses its own endpoint, but
depends on the same web search provider and page-verification gate.

## What changed
- Preserve `None` on failure (no unverified source promotion), but pass an
  optional status-only `diagnostics` dictionary for both assistants.
- Distinguish search disabled, missing API key, private-query rejection,
  provider HTTP errors, incomplete output, no actual search call, no
  attributable URLs, no output text, timeout, network and invalid response.
- Expose the final search status in both API Research Trail results.
- Support `OPENAI_WEB_SEARCH_MODEL` as an opt-in dedicated web-search
  model override, preserving existing `OPENAI_MODEL` for synthesis.
- Increase bounded search response output to 2400 tokens to reduce
  incompleteness without adding another paid call.
- Add mocked regression tests for provider rejection, truncation, missing
  search action, disabled config and model override.
- No personal content, credentials, raw provider errors or search question
  text are logged in diagnostics. No database or external action changes.

## Live verification still needed
Deploy an approved image to staging (NOT production), authenticate as a
permissioned user, select **Web only** in each assistant and ask a public
question whose sources can be independently checked. Inspect the status:

- `SEARCH_DISABLED_BY_CONFIGURATION`: review web-search feature flag
- `PROVIDER_KEY_UNAVAILABLE`: check credential configuration without exposing key
- `PROVIDER_HTTP_400/403`: inspect tool/model compatibility or entitlement
- `PROVIDER_HTTP_429`: inspect provider rate and credit limits
- `PROVIDER_INCOMPLETE_...`: inspect output budget/model configuration
- `PROVIDER_SEARCH_TOOL_NOT_EXECUTED`: inspect response/tool orchestration
- `PROVIDER_NO_ATTRIBUTABLE_URLS`: no verifiable discovery sources
- `NO_READABLE_PUBLIC_PAGES`: inspect per-page status, safe redirects,
  blocked sites, non-HTML pages or parsability
- `READ_SOURCES_AVAILABLE`: source retrieval succeeded, check quality and
  relevance of source-backed answer separately

Do not infer broad public/social trends from bounded saved posts, do not
represent model general knowledge as verified current events, and do not
treat a successfully retrieved article as an officer-verified legal fact.

## Deployment
This commit changes Git source only. A separately published Docker staging
image and approved deployment are required for live verification.
