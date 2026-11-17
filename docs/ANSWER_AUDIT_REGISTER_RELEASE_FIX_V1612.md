# v161.2 — precise sanitized-export privacy contract

The v161.1 backend suite passed 1,182 tests, but a frontend contract assertion incorrectly rejected the flag `contains_source_excerpt:false` because it searched for the substring `source_excerpt`. The revised contract checks the exact exported entry keys and verifies that both `contains_source_excerpt` and `contains_raw_answer` are false. No raw answer or source excerpt is exported. This build keeps the v161.1 issue categorization and session-only QA register and uses sequential version labels.
