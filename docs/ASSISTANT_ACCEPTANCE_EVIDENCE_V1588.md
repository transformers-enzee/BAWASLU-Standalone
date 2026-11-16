# v158.8 — acceptance evidence register

The administrator-only read-only `GET /api/assistant-evaluation/acceptance-evidence.csv?target=24` exports an action-oriented CSV register of missing independent acceptance evidence. The exported columns are track, status, responsible role, required evidence, required review, and readiness note.

The register is generated from the v158.7 readiness endpoint under the same authorization and permission-scoped Inbox sampling rules. It never includes original posts, questions, generated answers, human names, source URLs, legal determinations or casework. CSV values are protected against formula-prefix interpretation. It is not a signed document and does not store or change any acceptance state.

The human review, legal document version/currentness, Pemilu/Pemilihan applicability, missing-source negative-control and client signoff tracks remain pending. A shortfall row is included when eligible samples are insufficient. Developers should not mark any outstanding acceptance track DONE based on successful automated or synthetic tests alone.
