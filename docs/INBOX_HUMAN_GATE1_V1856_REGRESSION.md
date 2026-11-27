# BAWASLU v185.6 — Human Gate 1 legacy regression link contract

v185.5 introduced the officer-facing /inbox?gate1=1 review lane and updated
Administrator Human Review Status deep links to include gate1=1. The full CI
gate had 3,005 passing tests and one failing stale expectation asserting that
the administrator page continued to link into the relevant-only Inbox.

This follow-up updates that single test to enforce the corrected deep link,
rather than reverting the feature or weakening evidence scope. No database
change, officer data mutation, enabled flag, or paid AI processing.

The v185.6 release contains the v185.5 implementation and this QA contract fix.
