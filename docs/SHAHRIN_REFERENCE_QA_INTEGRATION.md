# Shahrin reference-based QA adapter

This change adds a **no-inference prompt preparation module** for the separate BAWASLU QA pilot. It does not modify the live QA prompt editor or its assessment runner, and does not call OpenAI or consume model credits.

## Purpose

- Read original source text, saved V9 rubric, and trusted Shahrin exemplar payload from the private `pilot_smart_radar` schema.
- Exclude target labels and raw curated labels from model input.
- Reject wrong rubric SHA-256, target mismatch, duplicate categories, unsafe exemplar similarities, and malformed references.
- Keep post QA IDs outside model messages; use them only for cache and audit.
- Produce a deterministic cache key and an unambiguous variant `qa-prompt-tune-v9+shahrin-ref-v1`.
- Preserve zero-example fallback rather than supplying weak matches.

## Server-side API

`GET /api/qa/shahrin-reference-preview/{qa_id}`

Disabled by default. Requires an authenticated user with **Administration** access and `BAWASLU_QA_REFERENCE_PREVIEW_ENABLED=true`. No model call occurs, even when enabled. Preview returns messages for internal QA debugging; do not expose to general users.

The private Supabase schema is not directly available through the browser. This endpoint uses only the authenticated backend's SQL connection. If the pilot schema is missing, it fails closed with a service-unavailable error rather than running model inference.

## Next integration step

The **live QA assessment runner shown in screenshots is not in the connected GitHub repository**. Its owner must use `app.qa_shahrin_reference.prepare_qa_request` (or equivalent logic) before the model call. Validate credit budget, require a manual, maximum-three-post confirmation, never auto-retry, and store predictions under the distinct variant rather than overwriting V9. The existing QA UI will not automatically change from merging this PR.

## Tests

Run from `backend/`:

```bash
python -m pytest -q tests/test_qa_shahrin_reference.py
```

Unit tests cover leakage, hash consistency, source/schema limits, cache determinism, empty-reference fallback, target mismatches and disabled-by-default endpoint. Tests do not access a model provider.

Database reference index currently holds 72 examples, 66 eligible, 6 quarantined, as separately verified against the pilot schema.