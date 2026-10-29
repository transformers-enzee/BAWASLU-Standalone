# v102.8 CI contract fix

v102.7 source-scope response field was omitted even though the new end-to-end test expected it. Add explicit source_scope to the authorized saved Inbox Radar response and retain the regression test. An earlier v102.7 release built successfully but had 1/141 failed QA tests; do not call #13 complete until all tests pass and a live smoke check verifies the authenticated feed. No paid providers used.
