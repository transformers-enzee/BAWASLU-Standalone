# v160.0 — Indonesian legal claim/source wording triage

Expands the existing zero-credit narrow lexical legal-modality checker to detect Indonesian duty, permission and prohibition clauses using a bounded verb vocabulary: wajib, harus, tidak wajib, tidak harus, boleh, diperbolehkan, diizinkan, dilarang, tidak boleh, tidak diperbolehkan and tidak diizinkan. Multiword negative forms precede positive forms so **tidak diperbolehkan** is not accidentally interpreted as permission.

For authorized, displayed citations to REGULATION / SOP / GUIDANCE PDF pages, a single opposite polarity for the same verb triggers the existing PASSAGE_POLARITY P1 officer-review flag. Conflicting clauses within one excerpt remain ambiguous rather than automatically flagged. Cross-language translations, legal applicability, legal currentness, actor and jurisdiction semantics, and case outcomes are NOT certified. Passing a lexical check is not legal approval, and the review priority is not violation severity.

QA adds more than twenty offline positive/negative cases including same-source ambiguity, unrelated verbs, uncited and contextual sources, quoted reporting, and nonlegal questions. No paid AI calls, new DB schema, live records, or human acceptance decisions.
