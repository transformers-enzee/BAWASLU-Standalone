# v185.4 — Final QA regression follow-up for live campaign-listing 500 fix

- v185.3 resolved the actual live exception `MonitoringCampaign.jurisdiction_type` not existing, and improved the frontend load error state.
- Full backend test run: 2,997 passed, one failed because test_admin_campaign_scopes_are_checked mocked `jurisdiction_type` but omitted the mapped `regency_city` field.
- v185.4 updates that older test to instantiate the **real SQLAlchemy MonitoringCampaign model** instead of an invented SimpleNamespace, retaining the real-model v185.3 test.
- The v185.3 and v185.4 fixes are included in this single candidate image, with no database schema or officer record changes, no AI spending, and no governance write activation.
