# v100.2 — workflow-first acceptance, no accuracy-tuning work

Purpose: validate saved processing outputs flow into the Intelligence Inbox, finding players and reusable canonical social-source assessment view. These are automated *workflow* gates, not independent correctness labels.

Live baseline checked October 29, 2026:
- 108 linked source posts; 66 distinct posts with an assessment version.
- 26 distinct posts with saved topic labels, 1 with a Public Concern entry following officer correction, 3 with issue signals.
- Public Concern on source 225 is officer-reviewed, not evidence of automated AI discovery.
- The shared lookup uses canonical social source IDs. Smart Radar's separate pilot IDs remain unjoined absent verified lineage.
- #14 AI-label accuracy is intentionally distinct from #7/#10 workflow acceptance.
- No provider calls, costs, or production classification modifications are authorized in this release.

Workflow checks added to CI include Inbox/shared-view equality, saved Public Concern routing to the correct intelligence player, absence of invented narrative/violation entries, and preserving unassessed records as unassessed. Human acceptance still applies where explicitly needed.
