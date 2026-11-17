# v161.5 — deterministic source order regression correction

The v161.4 build passed the revised privacy allowlist assertion, but the new CSV contract test expected SOCIAL-7 before INT-2026-000001. The issue register deliberately sorts the source IDs lexicographically to ensure stable deduplication, so the correct sanitized cell is `INT-2026-000001 | SOCIAL-7`. Updated this test expectation, with no change to sensitive data handling, authorization, occurrence accounting or the CSV generation logic. All automated release checks must pass before reporting LIVE.
