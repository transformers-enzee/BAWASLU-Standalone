# BAWASLU v179.9 — original-wording regression guard

The pilot question uses "what is the situation ... comparing with its neighboring countries". The earlier broad-question regular expression matched compare/comparison but not comparing. This bypassed planning and the answer-coverage audit for the exact question even after improvements in v179.7/v179.8. This release fixes compare/compares/comparing/compared/comparison/comparative and regional comparison cues. "Situation"/"state of"/"kondisi" now indicates current-evidence checks when no earlier historical year is specified.

If the research planner is unavailable for a broad comparison, three generic dimensions continue the search (structures, current outcomes, comparative implications), rather than silently reducing to a one-part query.

Two deterministic regression checks use the exact original phrasing with no planner monkeypatch, confirm multiple fallback dimensions and current-date intent, and cover English/Indonesian comparison variants. All prior cross-topic research, PDF text/link, Word and Excel citation tests continue to run in Docker QA.

Staging-only branch architecture-v2-foundation-20261015; build v179.9. Expected GHCR image: ghcr.io/transformers-enzee/bawaslu-standalone:staging-179.9. No production or Supabase migration changes. Full live answer and PDF QA needs authenticated staging after image save.
