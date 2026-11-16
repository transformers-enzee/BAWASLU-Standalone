# v159.4 — Future-safe acceptance-review release tests

v159.3 backend suite passed 1,031 tests, but the frontend build was blocked by the old v159.2 contract asserting an exact `159.2` build. Both the v159.2 and new v159.3 frontend tests now enforce a minimum supported version and verify frontend/backend build parity instead of pinning an obsolete version. Authorization and evidence-review business logic are unchanged; no live acceptance records or approvals created during development.
