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
COPY frontend/src/components/intel/CampaignPanel.jsx ./frontend/src/components/intel/CampaignPanel.jsx
COPY frontend/src/pages/WatchlistPosts.jsx ./frontend/src/pages/WatchlistPosts.jsx
# Verify backend syntax and Stage 1 QA validators before the live deployment.
RUN python -m compileall -q ./backend && cd backend && python -m pytest -q tests/test_smart_radar_qa_validation.py tests/test_smart_radar_qa_v2.py tests/test_smart_radar_qa_tuning.py tests/test_smart_radar_qa_alignment.py tests/test_smart_radar_qa_limits.py tests/test_role_matrix.py tests/test_processing_hints.py tests/test_saved_assessment_views.py tests/test_watchlist_feed_scope.py tests/test_role_actions_v2.py tests/test_classification_accuracy.py tests/test_campaign_sentiment_pipeline.py tests/test_bulk_integration_v956.py
COPY --from=frontend-build /src/frontend/dist ./frontend_dist
ENV FRONTEND_DIST=/app/frontend_dist
WORKDIR /app/backend
EXPOSE 8000
CMD ["sh","-c","alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
