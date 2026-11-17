# v160.7 — Full-answer synthetic QA and cross-module citation completeness

The cross-module readiness check previously marked an answer as source-complete whenever a selected set contained formal Inbox evidence and social listening posts, even if the visible answer cited only one kind. It now requires both an actual displayed authorized INT ID and a displayed SOCIAL ID. The output includes selected and cited counts per kind, absent source-type citations, and explicit source_truth_verified=false. Displaying both references still does not certify the factual comparison.

A pure zero-credit full-answer replay harness runs 12 distinct synthetic scenarios through the actual grounding and quality pipeline: dual citations, one-sided citations, zero citations, invented IDs, duplicate conflicting sentiment, missing source types, mixed legal PDF, unsupported formal BAWASLU confirmation, and mistaken platform-policy attribution. This benchmark intentionally measures *deterministic source-attribution regression behavior* rather than model answer accuracy, human agreement, or legal correctness. It has no DB or network calls, cannot mark client approval and is not a representative dataset.

Next actual acceptance dependency: independently score real, authorized Assistant responses against original evidence and current official legal references; do not extrapolate from these fixtures.
