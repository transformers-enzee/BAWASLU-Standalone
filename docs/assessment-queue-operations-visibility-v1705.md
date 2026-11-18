# v170.5 – clearer queue review priorities
The existing authorized campaign Assessment operations panel splits nonzero lifecycle buckets into *Review / investigation* and *Informational states* based on the API-supplied priority. History and queue review are distinguished and show the prescribed next steps. It surfaces snapshot timestamps, in-progress refresh warnings, and cross-aggregate drift (including worker/completion consistency, not only local triage sum drift). Count totals remain visible. No new server endpoints, database writes, paid requests, state mutations, or hidden automatic retries.

The static QA guard runs in the mandatory frontend build and checks safe action bindings. A browser-only authenticated staging visual check remains separate from this automated build contract.
