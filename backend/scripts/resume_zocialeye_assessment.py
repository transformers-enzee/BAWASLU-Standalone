"""Consent-gated, import-scoped CLI for existing BAWASLU AI assessment jobs.

Usage (on an authenticated backend host WITH its existing environment):
    PYTHONPATH=backend python backend/scripts/resume_zocialeye_assessment.py --run-id 36
    PYTHONPATH=backend python backend/scripts/resume_zocialeye_assessment.py --run-id 36 --execute --acknowledge-metered --limit 50

Dry run is the default. This never creates jobs, alters budgets, retries failed
requests, changes officer decisions, or bypasses existing provider limits.
"""
import argparse
import json
import os
from sqlalchemy import func
from app.db import SessionLocal
from app.models import (
    AIAssessmentJob, CampaignEvidence, EvidenceAssessment,
    SocialListeningResult, SocialListeningRun,
)
from app.activation_assessment import remaining_budget
from app.sentiment_processing import relevance_is_assessed

PREFIX = "offline-xlsx-20261119-batch-"
CAMPAIGN_ID = 1


def inspect_queue(db, run_id):
    run = db.get(SocialListeningRun, run_id)
    if run is None or run.provider != "AI_ASSESS_ALL":
        raise ValueError("Expected an existing Assess All run")
    metadata = json.loads(run.query_json or "{}")
    if int(metadata.get("campaign_id", -1)) != CAMPAIGN_ID:
        raise ValueError("This tool only supports the BAWASLU campaign")
    if not metadata.get("cost_confirmed"):
        raise ValueError("Existing run must record paid-AI consent")
    original_ids = [int(v) for v in metadata.get("assessment_result_ids", [])]
    if len(original_ids) != 434 or len(set(original_ids)) != 434:
        raise ValueError("Expected the exact 434-record consented import run")
    rows = (db.query(
            SocialListeningResult.id, SocialListeningRun.provider,
            SocialListeningRun.provider_request_id, AIAssessmentJob.state,
            AIAssessmentJob.attempts)
        .join(SocialListeningRun, SocialListeningResult.run_id == SocialListeningRun.id)
        .join(CampaignEvidence, (CampaignEvidence.result_id == SocialListeningResult.id)
              & (CampaignEvidence.campaign_id == CAMPAIGN_ID))
        .join(AIAssessmentJob, (AIAssessmentJob.result_id == SocialListeningResult.id)
              & (AIAssessmentJob.campaign_id == CAMPAIGN_ID))
        .filter(SocialListeningResult.id.in_(original_ids),
                CampaignEvidence.match_method != "WATCHLIST_ACCOUNT").all())
    mapped = {int(row.id): row for row in rows}
    if set(mapped) != set(original_ids):
        raise ValueError("Missing or duplicate campaign-assessment links")
    for row in mapped.values():
        if row.provider != "ZOCIALEYE" or not row.provider_request_id.startswith(PREFIX):
            raise ValueError("Run contains a post outside the authorized ZocialEye import")
    # Jobs must never be reset, and ambiguous/failed calls must not be retried.
    pending = [rid for rid in original_ids
               if mapped[rid].state == "PENDING" and int(mapped[rid].attempts or 0) < 3]
    return pending, {state: sum(row.state == state for row in mapped.values())
                     for state in ("COMPLETED", "PENDING", "PROCESSING", "FAILED")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True, type=int)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--acknowledge-metered", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.limit <= 500:
        parser.error("--limit must be between 1 and 500")
    if args.execute and not args.acknowledge_metered:
        parser.error("--execute requires --acknowledge-metered")
    db = SessionLocal()
    try:
        pending, counts = inspect_queue(db, args.run_id)
        budget = remaining_budget(db, CAMPAIGN_ID)
    finally:
        db.close()
    planned = min(len(pending), args.limit, max(0, int(budget["available"])))
    print(json.dumps({"run_id": args.run_id, "job_counts": counts,
                      "pending_eligible": len(pending), "budget": {k: v for k, v in budget.items()
                      if k not in ("provider_ready",)}, "provider_ready": budget["provider_ready"],
                      "planned_calls": planned, "dry_run": not args.execute}))
    if not args.execute:
        return
    if not os.getenv("OPENAI_API_KEY") or not budget["provider_ready"] or not budget["database_ready"]:
        raise RuntimeError("Existing backend provider/database configuration unavailable")
    if planned == 0:
        return
    from app.auto_relevance import assess_pending_campaign
    for rid in pending[:planned]:
        # The worker rechecks and atomically claims each targeted PENDING job and
        # reserves its own daily/lifetime budget before making the paid call.
        db = SessionLocal()
        try:
            active, _ = inspect_queue(db, args.run_id)
            balance = remaining_budget(db, CAMPAIGN_ID)
            if rid not in active:
                continue
            if balance["available"] < 1:
                print("Quota reached; remaining PENDING jobs preserved")
                break
        finally:
            db.close()
        assess_pending_campaign(CAMPAIGN_ID, requested_limit=1, target_result_id=rid)
    db = SessionLocal()
    try:
        _, final_counts = inspect_queue(db, args.run_id)
    finally:
        db.close()
    print(json.dumps({"run_id": args.run_id, "final_job_counts": final_counts}))


if __name__ == "__main__":
    main()
