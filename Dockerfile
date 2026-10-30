FROM node:22-slim AS frontend-build
WORKDIR /src/frontend
COPY frontend/package*.json ./
RUN npm install --no-audit --no-fund
COPY frontend ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend ./backend
# Include the Inbox source for zero-credit cross-layer regression assertions.
COPY frontend/src/pages/Inbox.jsx ./frontend/src/pages/Inbox.jsx
COPY frontend/public/ui-freeze/watchlist-live.js ./frontend/public/ui-freeze/watchlist-live.js
COPY frontend/public/ui-freeze/watchlist-v2_2.html ./frontend/public/ui-freeze/watchlist-v2_2.html
COPY frontend/src/components/intel/CampaignPanel.jsx ./frontend/src/components/intel/CampaignPanel.jsx
COPY frontend/src/components/QAPromptWorkbench.jsx ./frontend/src/components/QAPromptWorkbench.jsx
COPY frontend/src/pages/WatchlistPosts.jsx ./frontend/src/pages/WatchlistPosts.jsx
# Verify backend syntax and Stage 1 QA validators before the live deployment.
RUN python -m compileall -q ./backend && cd backend && python -m pytest -q tests/test_topic_themes_v1069.py tests/test_campaign_captured_posts_full.py tests/test_smart_radar_qa_validation.py tests/test_smart_radar_qa_v2.py tests/test_smart_radar_qa_tuning.py tests/test_smart_radar_qa_alignment.py tests/test_smart_radar_qa_limits.py tests/test_role_matrix.py tests/test_processing_hints.py tests/test_saved_assessment_views.py tests/test_command_centre_v1090.py tests/test_command_centre_sections_v1089.py tests/test_inbox_read_cache_v1081.py tests/test_candidate_mentions_dedupe_v1088.py tests/test_candidate_alias_radar_v1076.py tests/test_narrative_patterns_v1085.py tests/test_live_inbox_radar_v1075.py tests/test_shared_violation_hard_cases_v107.py tests/test_watchlist_feed_scope.py tests/test_role_actions_v2.py tests/test_classification_accuracy.py tests/test_campaign_sentiment_pipeline.py tests/test_bulk_integration_v956.py tests/test_captured_sentiment_filters.py tests/test_candidate_incident_bulk.py tests/test_processing_acceptance_snapshot.py tests/test_incident_temporal_qa.py tests/test_candidate_registry_groups.py tests/test_classification_enrichment.py tests/test_jurisdiction_cross_module.py tests/test_finding_group_freshness.py tests/test_valid_absence_contract.py tests/test_grouping_readiness.py tests/test_classification_contract_provenance.py tests/test_cross_module_player_contract.py tests/test_grouping_candidate_counts.py tests/test_group_review_source_navigation.py tests/test_grouping_determinism.py tests/test_candidate_explicit_mentions.py tests/test_e2e_baw_980.py tests/test_intelligence_bulk_v981.py tests/test_issue_review_e2e_v983.py tests/test_issue_phrase_seed_v984.py tests/test_qa_confusion_v986.py tests/test_production_acceptance_v986.py tests/test_exemplar_coverage_v987.py tests/test_acceptance_evidence_v988.py tests/test_calibration_briefs_v989.py tests/test_acceptance_next_actions_v991.py tests/test_summary_readiness_v992.py tests/test_real_group_summary_v993.py
COPY --from=frontend-build /src/frontend/dist ./frontend_dist
ENV FRONTEND_DIST=/app/frontend_dist
WORKDIR /app/backend
EXPOSE 8000
CMD ["sh","-c","alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
