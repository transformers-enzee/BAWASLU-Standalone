# v172.1 — Cross-post place mention leads for incident jurisdiction review

A selected Inbox source's explicit Kabupaten/Kota candidates now include a bounded,
read-only inventory of other posts in the same authorized campaign which mention
the same place in incident context. Only IDs, platforms and place names are shown;
no new cross-jurisdiction data exposure, provider calls or background crawling.

**Matching the same locality does not establish the same incident,
corroboration, source independence or a verified jurisdiction.** Source text
duplicates are skipped, candidate matches are capped per locality, and the
query scans at most 200 other campaign evidence links. This is for officer
triage only, not for automatic province or city confirmation.

The next persistent Kabupaten/Kota review stage requires a governed
database schema and audit workflow; no city decision is written in this build.
