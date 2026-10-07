# Base44 → Standalone Migration Notes

## Reused concepts

| Base44 concept | Standalone equivalent |
|---|---|
| MediaItem | Evidence |
| DataReview | ReviewDecision + `review_state` exception routing |
| MediaSource | MediaSource + MediaMetricVersion |
| classifyItems | AI gateway + deterministic `review_engine` |
| story_relation fields | RelationshipDecision + planned StoryCluster memberships |
| analyst findings | Finding + FindingEvidence |
| AuditLog | AuditLog |

## Deliberately not carried forward

- `@base44/sdk`, Base44 auth/hosting/functions.
- Fragmented final-state logic across `classification_status`, `review_status`, `verification_status`, and `human_decision`.
- QA/stage fixture screens that are not required for the operational KPM workflow.

Those files remain available in the original Base44 export as historical reference but are not runtime dependencies of Standalone v0.1.

## Authoritative review state

`Evidence.review_state` is the one operational state used by Evidence Desk, Command Centre, benchmark export, and client export. `ReviewDecision` preserves the decision history so the final state does not erase AI/human provenance.
