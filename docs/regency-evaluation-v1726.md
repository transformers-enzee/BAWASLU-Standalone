# v172.6 — Reproducible location evaluation and false-positive safeguards

- Exclude generic mentions of elections or routine location references from
  incident-location cues unless a more specific incident/report cue exists.
- Do not treat "tidak ada dugaan", "tidak ditemukan insiden" or other
  explicit incident negations as affirmative location evidence.
- Add a reusable zero-credit, pure evaluation function accepting explicit
  human-labeled text and official regency codes. It reports exact-set match,
  precision, recall, F1 and false-positive / false-negative counts.
- Include 10 curated labeled source-phrase cases and additional negative
  and ambiguous tests in CI.

**Important limitation:** A 10/10 synthetic fixture result is a regression
benchmark, not real-world geographic accuracy. A representative officer-labeled
BAWASLU corpus and field evaluation remain required before claiming high
real-world precision. No production data was reclassified or changed.
