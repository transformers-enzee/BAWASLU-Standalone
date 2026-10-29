# v102.1 production blocker repaired

The /api/source-lineage/{reference:path} catchall route was registered before /inbox-radar-feed/{campaign_id}, potentially swallowing the real Smart Radar feed. Register the specific feed route first; add a FastAPI routing test to ensure it matches the real request path. This fixes an actual integration blocker not caught by direct-function-only tests. Previous v102 was CI-green but functional endpoint reachability was not thereby guaranteed. No paid provider calls.
