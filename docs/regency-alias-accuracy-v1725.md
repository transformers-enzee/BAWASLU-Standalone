# v172.5 — Indonesian Kabupaten/Kota locality aliases and ambiguity

Detect supported "Kab." and "Kab " forms, and short follow-up names after
a fully qualified place in the same incident-location clause. The unqualified
name must uniquely map to exactly one official region in the bundled registry.
An unqualified city/regency name by itself is never sufficient evidence.

This fixes a consequential safety defect: a source describing incidents in
"Kabupaten Musi Banyuasin dan Musi Rawas Utara" could previously surface
only one candidate city, allowing an officer to mistakenly confirm one
location as unambiguous. The detector now carries both forward and blocks
single-city confirmation until the evidence is resolved.

A deterministic, synthetic source-phrase benchmark checks explicit names,
abbreviations, ambiguity, multi-province reports and negative publisher/profile
mentions. The benchmark does not establish real-world recall or field accuracy;
those need a representative officer-labeled corpus.
