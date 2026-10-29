# Batch 1: one-release acceptance matrix (v101)

Scope #6 incident jurisdiction, #8 exact duplicates, #9 recurring narratives, #11 Needs Attention.

This release exposes four independent production acceptance states on the existing read-only `campaignAcceptanceSnapshot` action, together with precise blockers. Reuses saved findings, grouping proposals, officer review records, and source-scope validation. No fake officer approvals, no AI/crawl provider requests.

- #6 source incident location can be previewed; positive verification requires independent officer review and a matching source fingerprint.
- #8 exact duplicates are identified by matching normalized source text, with provisional save and human acceptance separate; 155/205 was an earlier pending source pair.
- #9 narratives require multiple independently attributed, time-consistent sources. No narrative claim when assessment backlog is incomplete.
- #11 saved issue evidence and explicit officer follow-up may create a provisional attention candidate, but not a proven legal outcome or officer approval.

The matrix is engineering acceptance observability; it does NOT imply the four outstanding checklist items are all DONE. The pre-existing 8/15 engineering ledger must only change with actual acceptance evidence. The temporary officer topic/Public Concern correction UI stays visible.
