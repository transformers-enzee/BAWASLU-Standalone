# v161.4 — regression check alignment for occurrence-aware exports

v161.3 expands sanitized JSON issue entries to include a bounded `occurrences` number. The earlier v161.1 privacy contract now explicitly includes this additional non-sensitive integer while retaining an exact allowlist of exported entry fields. The v161.3 CSV test checks the actual selected category's generic review instruction rather than unrelated categories. Neither change relaxes privacy or source authorization; all audit counts remain warning occurrences, not verified AI failures.
