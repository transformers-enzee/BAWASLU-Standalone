# v167.4 — Latest-completion consistency without fabricating billing lineage

A completion record's historical provider usage may correspond to an earlier saved assessment version; subsequent officer updates or sentiment changes can append newer assessment versions. An audit that looks only at the latest version would misclassify some historical successful AI activity.

This batch introduces a read-only **latest completion classification** diagnostic: completed job with no latest assessment, completed job with an invalid latest relevance label, and the subset that still has a historically verified usage-backed classification. The existing valid historical usage metrics stay untouched. The Assessment Operations panel surfaces the new issue with an explicit review instruction. No classification, usage, budget or job state is edited; missing usage records are not automatically reconstructed.

Regression tests cover valid historical usage followed by UNASSESSED, normal revision to a valid classification, missing assessments, campaign isolation, and zero AI calls.
