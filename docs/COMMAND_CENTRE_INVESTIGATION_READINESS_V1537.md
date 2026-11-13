# BAWASLU v153.7: Investigative readiness for Command Centre reporting

A read-only readiness matrix classifies authorized casework in the selected UTC reporting cohort into evidence recheck, review history check, officer next action, submitted for independent review, completed workflow, and other follow-up. It reuses the latest report per authorized case and source-review events already fetched for the management report. One category per case; capped 12-case preview but complete authorized counts. The dashboard displays bilingual group totals and a filterable case table with permission-rechecked Inbox links.

Source-review events are observed only inside the selected reporting window. Missing events are UNKNOWN historical evidence, not proof that no officer check occurred. A source check logged in the window is merely evidence of an officer workflow action; neither it nor a submitted report is an official or legal determination. Approved and closed casework are counted as workflow-complete without factual clearance.

The existing interim report includes the readiness breakdown in its narrative, procedural follow-up recommendations and methodology so the same grounded text appears in existing PDF, Word and Excel exports. No separate legal module, raw notes, new DB queries, migrations, model inference, automatic approvals or assignments.

Mandatory backend and frontend regression tests cover the stage matrix, counts, province restrictions, audit precedence, format exports and release-version compatibility.
