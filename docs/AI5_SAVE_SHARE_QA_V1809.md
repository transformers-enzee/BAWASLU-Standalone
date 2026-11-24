# BAWASLU v180.9 — AI-5 save/share regression compatibility

v180.8 added durable saved chats and read-only recipient-scoped shares on the latest v180.7 branch. The isolated backend feature-specific tests and the frontend React build passed. The broader AI-5 research suite failed because a legacy research fixture passed a plain object as db, not a SQLAlchemy Session; the new automatic persistence hook attempted db.rollback() on that fake object. This is an integration-only problem, not a saved-chat authorization failure.

v180.9 restricts the auto-save path to valid SQLAlchemy Session instances. Actual FastAPI requests always use the real Session dependency. Synthetic research fixtures can continue running without a database. Errors from the real session are rolled back, logged, and surfaced as COULD_NOT_SAVE without discarding the in-memory answer. Owner/recipient authorization, frozen share semantics, draft retention, signed-in access, expiry/revocation and migration remain unchanged.

Tables are in additive migration database/migrations/20261124090000_ai5_saved_shares_v1808.sql. Stage migration only after successful QA; do not auto-deploy image. Candidate GHCR: ghcr.io/transformers-enzee/bawaslu-standalone:staging-180.9.
