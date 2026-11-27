# BAWASLU v186.4 - Human Gate 1 synthetic QA fixture coverage

## Observed issue

Staging campaign 12 (BAWASLU Gate 1 QA Pilot) is DRAFT and has no ordinary links, synthetic sources, or correction events. Its empty queue is expected. Changing classification filters does not manufacture data.

## Isolation decision

The BAWASLU Supabase project contains existing operational social listening results. The global social source index is not proven to exclude provider GATE1_QA_SYNTHETIC. Therefore **do not seed fictional QA sources into this shared database**. A staging application is not automatically an isolated database. v186.4 does not alter or seed the live staging DB.

## Implemented

- A fictional five-scenario Gate 1 test catalog (unassessed, uncertain, excluded, relevant, highly relevant) and existing baseline correction example, seeded only into disposable CI PostgreSQL by the existing strict localhost guard.
- Source identity and QA markers on every test post, and links only to the fictional pilot campaign.
- Read-only pilot preflight now explains missing ordinary evidence and refuses to imply that the campaign is ready for write testing.
- Inbox QA page gives a clear empty-campaign explanation, no fabricated items.
- CI executes isolation and catalog regression tests; no paid AI or social listening calls.

## Manual QA after deployment

1. In Intelligence Inbox > Human Gate 1, choose BAWASLU Gate 1 QA Pilot and click Check staging pilot readiness.
2. The UI should display zero linked evidence and an explicit warning that changing filters cannot fix an empty campaign.
3. Verify the correction feedback queue remains empty and no write, training, or publication controls are enabled.
4. Only after provisioning an independent QA database and controlled pilot credentials, run the full correction and Gate 2 readiness walkthrough there.

No user action is needed to seed the shared DB; it is intentionally prohibited until a documented operational isolation design is approved.
