# BAWASLU Standalone Parity Matrix

| Capability | Legacy BAWASLU | v0.1 status | Notes |
|---|---|---|---|
| Intelligence create/list/get | Yes | Implemented | Standalone DB/API |
| `INT-YYYY-######` sequence | Yes | Implemented | Database-backed sequence |
| Jurisdiction confirmation | Yes | Implemented | Human-governed |
| Province / Regency-City ACL | Yes | Implemented | Enforced server-side |
| Multi-region data fields | Yes | Implemented | Normalized assignments, server-side Province/Regency ACL enforcement and human confirmation |
| Geographic mismatch review | Yes | Implemented | Fingerprinted mismatch detection, human keep/change decisions, validation blocking, normalized jurisdiction updates and audit |
| Source identity states | Yes | Implemented | Registered/known/unresolved |
| Observed publisher provenance | Yes | Implemented | Kept distinct from registered identity |
| Watchlists | Yes | Implemented | First-class table/API |
| Source accounts | Yes | Implemented | Used for identity matching |
| Actor/entity relationships | Yes | Implemented | First-class registry + intelligence JSON contract retained |
| V3 triage provenance | Yes | Implemented | Validated V3 contract, generation/source/proposal fingerprints, OpenAI/provider-or-fallback provenance and audit |
| Production AI triage | Yes | Implemented | OpenAI Responses API + Structured Outputs under V3 contract when configured; single-attempt safe local fallback; human review remains mandatory |
| Human triage decisions | Yes | Implemented | Backend-enforced Accept/Modify/Reject review, completion state, rejection/modify validation, audit provenance and final-validation gate |
| Human-approved intelligence summary | Yes | Implemented | Server-derived field states distinguish approved/rejected/pending/not-generated; Evidence Type included; source metadata and confirmed context separated from AI-triage approvals; reviewer/timestamp provenance retained |
| Evidence verification | Yes | Implemented | Independent human action |
| Duplicate detection/review | Yes | Implemented | Exact/canonical URL plus headline/content/source/date similarity scoring; human merge/keep-separate decision retained |
| Evidence attachments | Yes | Implemented local | Object storage/signed URL pending |
| Audit events | Yes | Implemented | First-class audit table |
| User/access administration | Yes | Implemented | Standalone account + access grant |
| Issue categories | Yes | Implemented | Included in importer |
| Data sources | Yes | Implemented | Included in importer |
| External connector registry | Yes | Implemented schema/import | Provider execution pending |
| Public URL retrieval | Yes | Implemented | Hardened public HTML retrieval with SSRF controls, metadata/JSON-LD extraction, preserved raw retrieval, deterministic boilerplate cleaning and human-editable intake |
| Source language resolution | New requirement | Implemented | Shared Malay/Indonesian/English detector used by retrieval, optional suggestion and AI Triage; analyst override remains authoritative |
| Intelligence Assistant | Yes | Implemented | OpenAI-grounded read-only synthesis over current-user-authorized records only; explicit publication/collection/validation date semantics; Bahasa Indonesia analytical output; human-approved triage separated from source evidence; supporting-record traceability and deterministic safe fallback |
| Google OAuth | Yes | Pending | Email/password available |
| OTP/password reset delivery | Yes | Pending | Requires delivery provider |
| Base44 data migration | N/A | Implemented importer foundation | Requires real export reconciliation |

| Social listening search | New requirement | Implemented foundation | SocialCrawl Universal Search adapter |
| Social listening filters | New requirement | Implemented | Provider-native + stable BAWASLU filter contract |
| Saved monitoring searches | New requirement | Implemented | Manual run in v0.1; scheduler later |
| Provider usage / credits | New requirement | Implemented | Live config-based credit estimate, balance-after-search projection, pre-search confirmation, repeat-search warning and recent usage audit |
| Social result review queue | New requirement | Implemented | Persistent no-credit review queue with state counts/filters, human review actions and Intelligence promotion |
| Promote social result to Intelligence | New requirement | Implemented | Creates UNVERIFIED/Pending Review record |
