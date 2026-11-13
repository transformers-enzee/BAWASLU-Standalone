# v154.9: Pilot existing-case presentation guard

Read-only officer pilot intake now selects the highest visible active case ID for each exact source-and-campaign pair regardless of upstream ordering, ignores CLOSED status with case/whitespace variants, and normalizes SOCIAL source type for matching. Added regressions for reversed input order, closed-case variants, and cross-campaign isolation. Authorization, evidence retrieval, human confirmation and case creation remain unchanged. No migration or live casework writes.
