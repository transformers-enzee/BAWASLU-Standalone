# BAWASLU Intelligence — Standalone v0.1

This is the first standalone migration of `bawaslu-insight-core`, aligned to the shared NK Intelligence architecture used by GovIntel v0.27 while retaining BAWASLU-specific domain semantics.

## What v0.1 establishes

- FastAPI + SQLAlchemy standalone backend with SQLite for local development and PostgreSQL support for deployment.
- Alembic baseline migration.
- Standalone email/password sessions and BAWASLU access grants.
- Server-side geographic ACL: Nationwide, Province, Regency/City.
- First-class BAWASLU tables for intelligence, watchlists, source accounts, actor relationships, triage generations, evidence files, categories, data sources, connectors and audit.
- Existing React/Vite BAWASLU user interface retained, with a compatibility client that routes the former Base44 action contract to the standalone API.
- Social Listening workspace with SocialCrawl provider foundation, filters, saved searches, review queue semantics, deduplication, usage/credit logging, and human-controlled promotion to Intelligence.
- Idempotent-style Base44 JSON migration staging with raw-payload retention and commit mapping.
- GovIntel v0.27 migration/architecture references included under `docs/` and `migration_manifests/` for platform compatibility review.
- The original Base44 entity/function contracts are retained under `legacy_base44_contracts/` for parity validation. They are not the runtime backend.

## Local run

### Backend

```bash
cd backend
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Default local bootstrap account (change immediately outside local development):

- email: `admin@bawaslu.local`
- password: `ChangeMeNow!`

Override both with `BAWASLU_BOOTSTRAP_ADMIN_EMAIL` and `BAWASLU_BOOTSTRAP_ADMIN_PASSWORD`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Vite proxies `/api` and `/uploads` to `http://localhost:8000`.

### Docker

```bash
docker compose up --build
```

## Base44 export migration

Export each Base44 entity as `<Entity>.json`, containing either a JSON array or an object with an `items`, `data`, `records`, or `results` array.

Dry-run/stage:

```bash
cd backend
python -m app.migration_importer /path/to/export
```

Stage and commit:

```bash
python -m app.migration_importer /path/to/export --commit
```

The importer covers all 13 existing BAWASLU entities, including `IssueCategory`, `DataSource`, and `ExternalDataConnector`, which were absent from the earlier GovIntel BAWASLU migration manifest.

## SocialCrawl

Set `SOCIALCRAWL_API_KEY` in the deployment environment. `SOCIALCRAWL_BASE_URL` is configurable. Social listening results remain evidence-discovery records until a human promotes them; promotion still creates UNVERIFIED / Pending Review intelligence. See `docs/SOCIAL_LISTENING_SOCIALCRAWL.md`.

## Source cleaning and language resolution

Public URL retrieval preserves the full retrieved source in provider metadata while using a deterministic cleaned article-body copy for AI triage. Recognized trailing publisher/footer/promotional boilerplate can be removed from the analysis copy without deleting the preserved source evidence.

The same deterministic language resolver is used by public-source retrieval, the optional Suggest language control, and AI Triage. It distinguishes Bahasa Melayu (`ms`), Bahasa Indonesia (`id`) and English (`en`) when the text provides sufficient evidence. A human analyst's explicit language selection always takes precedence.

## Production AI Triage

Set `OPENAI_API_KEY` in the deployment environment to enable production AI triage. `OPENAI_MODEL` defaults to `gpt-6-luna`, and `OPENAI_BASE_URL` defaults to `https://api.openai.com/v1`.

BAWASLU calls the OpenAI Responses API only when an authorized analyst clicks Generate/Regenerate AI Triage. The request uses Structured Outputs constrained to the BAWASLU V3 triage schema and `store: false`. AI output remains suggestion-only and each generated field still requires human Accept / Modify / Reject review before final validation.

The provider call is single-attempt. If the key is absent or the provider request fails, BAWASLU does not retry automatically; it generates the clearly labelled local workflow placeholder instead.

## Intelligence Assistant

The BAWASLU Intelligence Assistant is read-only and uses only intelligence records already accessible to the current user under the server-side geographic ACL. OpenAI synthesis receives compact evidence records containing recorded source excerpts, record status, verification state and human-approved triage values; raw pending/rejected AI triage suggestions are not supplied as approved analysis.

Each answer returns supporting intelligence records for traceability. The OpenAI call runs only when the user submits a question and uses `store: false`. If the provider is unavailable, the Assistant returns a deterministic summary of the matched authorized records. It does not trigger SocialCrawl searches or background provider work.

## v0.1 boundaries

This release is an architecture/parity foundation, not a claim of complete Base44 feature equivalence. The standalone AI triage endpoint uses the configured OpenAI Responses API when available and falls back to the deterministic local placeholder when it is not. Public URL retrieval includes hardened article/social retrieval, source cleaning and language-resolution safeguards. Google OAuth, email OTP delivery, password-reset delivery, signed private object-store URLs, and external provider execution are also not yet wired.

Those are intentionally listed as parity gates for the next version rather than silently removed. See `docs/PARITY_MATRIX.md`.
