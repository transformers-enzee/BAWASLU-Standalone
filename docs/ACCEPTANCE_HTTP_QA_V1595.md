# v159.5 — two-administrator HTTP acceptance QA and concurrency guard

An isolated FastAPI TestClient integration suite runs with a shared-memory SQLite test database and real registered application routes, bearer-token session lookup, user grants and persistence. Synthetic users 1 and 2 are separate active nationwide National Administrators; synthetic viewers, inactive administrators, and province-scoped administrators must be denied. The suite covers submit, self-review rejection, independent review, repeat/conflicting review rejection, revision history, separate resubmission, invalid references, invalid actions, no-store headers and persistent non-approval states.

On real PostgreSQL, the review transaction now locks the parent submission row with SELECT ... FOR UPDATE before checking the current event and committing a new event, preventing concurrent reviewers from both recording a terminal outcome. SQLite ignores row locks: this test suite validates sequential decisions and source-level presence of the locking primitive, **not** a verified concurrent PostgreSQL race test.

No staging officer/case/acceptance records, test users or external AI calls are made by these automated checks. A **real** two-administrator staging UAT remains pending and must be coordinated with authorized users. Do not treat evidence review as verified external legal or formal client signoff.
