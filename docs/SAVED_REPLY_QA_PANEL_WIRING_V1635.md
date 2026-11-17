# v163.5 - Saved Assistant reply QA frontend integration

The existing `AssistantSavedReplyAudit` component was implemented through v163.4 but not imported or rendered by the Intelligence Assistant page, making its pilot review actions inaccessible from the product UI. This release imports and mounts the component inside the pre-existing collapsed `Development QA tools (administrators)` panel. It stays behind `canShowAssistantQa`, which excludes demo, inactive and non-administrator users; existing APIs still enforce server-side reviewer and evidence permissions. The component is disabled while Assistant message generation or history operations are active.

The panel now exposes the existing controls **Find my saved replies**, **Load my pilot review queue**, **Select next eligible batch**, and **Export sanitized pilot handoff**, plus individual and batch audit functionality. No database writes, schema migration, new AI calls, relaxed source access or expanded user permissions are introduced.

A production-build regression checks the route page import, one mounted instance inside the admin panel, permission visibility, expected controls, and synchronized frontend/backend v163.5 build label. Human UAT using an authenticated staging administrator remains separate from automated build verification.
