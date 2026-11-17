# v162.8 - Evidence-review routing

A saved Assistant reply's audit result now includes a bounded deterministic review_route. Attribution gaps route to citation-attribution review, authorized sources with automated warnings route to source-based claim review, and otherwise to human spot checks. Missing current evidence routes to a separate access/presence check; unavailable owned history and ineligible historical formats have distinct suggested next steps. The list and single-reply views display those routes. These are unverified suggestions, not accuracy scores, source truth, legal findings or formal signoff.

No cross-user evidence read, source disclosure, persisted review state, model calls or database writes are introduced. Audit remains explicitly user-selected and limited to five replies per batch. Automated regression tests cover the routing priority, privacy-safe unavailable status, and no-verdict invariant.
