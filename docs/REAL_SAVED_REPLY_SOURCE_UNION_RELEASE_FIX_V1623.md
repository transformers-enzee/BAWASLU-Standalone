# v162.3 — Cited-only source notice JSX release correction

The v162.2 backend suite passed 1,221 tests and both synthetic scaling
benchmarks. The frontend build found a missing JSX conditional closing brace
after the new cited-only source explanatory text. This commit closes the brace
and adds a frontend contract assertion for its boundary. No source
authorization changes or expanded access beyond the strict combined 20-ID
replay scope. Normal Assistant citation limits and current source permissions
remain unchanged.
