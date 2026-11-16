# v156.9 — Release contract alignment

v156.8 passed 954 backend regression tests, but an older frontend contract asserted the build version was exactly 156.7 and blocked a valid sequential version bump. Updated the contract to enforce minimum version while preserving backend/frontend build parity; new v156.8 exception contract remains in place. No production business logic change in this follow-up, no Supabase migration, no writes to officer cases. Full automated QA and Render deployment verification required.
