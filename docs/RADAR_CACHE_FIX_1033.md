# v103.3 Cache production syntax repair

The v103.2 live adapter contained an invalid JavaScript regular expression in its eligible cache-route detection. Replace regex with explicit exact and prefix checks. This keeps the approved Smart Radar pilot UI unchanged, caches only bounded GET endpoints and never decision POST requests, and allows node --check to catch syntax failures. v103.2 was LIVE but its UI parity CI failed; verify v103.3 CI before claiming cache functionality accepted.
