"""Seed fictional Gate 1 UI-pilot records into an EMPTY localhost Postgres CI DB.

NEVER run on Supabase, Render, persistent databases, or BAWASLU user records.
The fixture does not call any external provider or use actual election posts.
"""
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlsplit

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.auth import hash_password
from scripts.gate1_fixture_catalog_v1864 import QA_SCENARIOS
from app.db import Base
from app.models import (
    AccessGrant, CampaignEvidence, EvidenceAssessment, MonitoringCampaign,
    SocialListeningResult, SocialListeningRun, User,
)
from app.inbox_human_corrections import (
    PILOT_QA_CAMPAIGN_NAME, PILOT_QA_PROVIDER, PILOT_QA_SOURCE_PREFIX,
)

FIXTURE_DB = "bawaslu_gate1_pilot_ci"
SEED_GUARD = "BAWASLU_GATE1_ISOLATED_E2E"


def assert_local_postgres(url: str):
    parsed = urlsplit(url.replace("postgresql+psycopg://", "postgresql://", 1))
    if not (
        os.getenv(SEED_GUARD) == "YES"
        and os.getenv("BAWASLU_ALLOW_ISOLATED_DB_TEST") == "YES"
        and parsed.scheme == "postgresql"
        and parsed.hostname in {"127.0.0.1", "localhost"}
        and parsed.port == 5432
        and parsed.path == "/" + FIXTURE_DB
        and parsed.username == "gate1qa"
    ):
        raise SystemExit("REFUSED: isolated localhost Gate 1 PostgreSQL database required")


def seed(output_path: Path):
    url = os.environ.get("DATABASE_URL", "")
    assert_local_postgres(url)
    assert output_path.is_absolute() and output_path.parent.is_dir()
    # Register the complete app model catalog before creating the disposable DB.
    # Startup event is not executed while importing, and the CI server later
    # uses BAWASLU_STARTUP_READ_ONLY=true to suppress workers/seed routines.
    from app import main as _app_catalog  # noqa: F401
    engine = create_engine(url, pool_pre_ping=True)
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            # Fail closed rather than adding data to an unexpected existing DB.
            for model in (User, MonitoringCampaign, SocialListeningResult, EvidenceAssessment):
                if db.scalar(select(func.count()).select_from(model)):
                    raise SystemExit("REFUSED: CI fixture database is not empty")
            password = os.getenv("BAWASLU_CI_PILOT_PASSWORD", "")
            if len(password) < 16:
                raise SystemExit("REFUSED: synthetic officer password not configured")
            admin = User(
                email="gate1-ci-admin@example.invalid",
                full_name="Fictional Gate 1 CI Admin",
                password_hash=hash_password(password),
                platform_admin=False,
            )
            viewer = User(
                email="gate1-ci-viewer@example.invalid",
                full_name="Fictional Gate 1 CI Viewer",
                password_hash=hash_password(password),
                platform_admin=False,
            )
            db.add_all((admin, viewer))
            db.flush()
            db.add_all([
                AccessGrant(
                    user_id=admin.id, access_role="National Administrator",
                    status="Active", geographic_scope="Nationwide",
                    permissions_json=json.dumps({
                        "view_intelligence": True, "human_validation": True,
                        "edit_intelligence": True, "administration": True,
                        "add_intelligence": True,
                    }),
                ),
                AccessGrant(
                    user_id=viewer.id, access_role="Viewer",
                    status="Active", geographic_scope="Nationwide",
                    permissions_json=json.dumps({"view_intelligence": True}),
                ),
            ])
            pilot = MonitoringCampaign(
                name=PILOT_QA_CAMPAIGN_NAME, status="DRAFT",
                created_by=str(admin.id), platforms_json='["facebook"]',
                primary_keywords_json="[]", next_run_at=None,
            )
            operational = MonitoringCampaign(
                name="Fictional protected operational campaign",
                status="ACTIVE", created_by=str(admin.id),
                platforms_json='["facebook"]',
                primary_keywords_json="[]", next_run_at=None,
            )
            db.add_all([pilot, operational])
            db.flush()
            run = SocialListeningRun(
                provider=PILOT_QA_PROVIDER,
                query_json='{"fictional":true,"paid_requests":0}',
                status="COMPLETED", credits_used=0, result_count=3 + len(QA_SCENARIOS),
                executed_by="ci-only",
            )
            db.add(run)
            db.flush()
            source = SocialListeningResult(
                run_id=run.id, provider=PILOT_QA_PROVIDER,
                provider_result_id=PILOT_QA_SOURCE_PREFIX+"FAKE-1862-01",
                platform="facebook", content_type="post",
                canonical_url="https://example.invalid/gate1/fictional-qa",
                author_name="Fictional CI Test Account",
                text_content="Synthetic QA-only example about a fictional local election discussion.",
                raw_payload_json='{"fictional":true,"unchanged":true}',
                geography_json="{}", source_identity_json='{"fictional":true}',
                content_fingerprint="ci-fictional-1862", review_state="QA_ONLY",
            )
            protected = SocialListeningResult(
                run_id=run.id, provider="SOCIALCRAWL",
                provider_result_id="CI-ORDINARY-DENIED-1862",
                platform="facebook", content_type="post",
                text_content="Fictional protected source in another campaign.",
                raw_payload_json='{"fictional":true,"protected":true}',
                geography_json="{}",
            )
            watchlist = SocialListeningResult(
                run_id=run.id, provider=PILOT_QA_PROVIDER,
                provider_result_id=PILOT_QA_SOURCE_PREFIX+"WATCHLIST-1862",
                platform="facebook", content_type="post",
                text_content="Fictional watchlist only; not ordinary campaign evidence.",
                geography_json="{}",
            )
            db.add_all([source, protected, watchlist])
            db.flush()
            # Five additional fictional scenarios, never inserted into shared databases.
            qa_rows = []
            for key, label, sentiment, message in QA_SCENARIOS:
                qa_rows.append(SocialListeningResult(
                    run_id=run.id, provider=PILOT_QA_PROVIDER,
                    provider_result_id=PILOT_QA_SOURCE_PREFIX+"FICTIONAL-1864-"+key,
                    platform="facebook", content_type="post",
                    canonical_url="https://example.invalid/gate1/fictional-"+key.lower(),
                    author_name="Fictional CI QA Account", text_content=message,
                    raw_payload_json=json.dumps({"fictional": True, "ci_only": True,
                                                 "scenario": key}, sort_keys=True),
                    geography_json="{}", source_identity_json='{"fictional":true}',
                    content_fingerprint="ci-gate1-v1864-"+key.lower(),
                    review_state="QA_ONLY",
                ))
            db.add_all(qa_rows)
            db.flush()
            db.add_all([
                CampaignEvidence(campaign_id=pilot.id, result_id=source.id,
                                 match_method="QA_SYNTHETIC"),
                CampaignEvidence(campaign_id=pilot.id, result_id=watchlist.id,
                                 match_method="WATCHLIST_ACCOUNT"),
                CampaignEvidence(campaign_id=operational.id, result_id=protected.id,
                                 match_method="KEYWORD"),
            ])
            db.add_all([
                CampaignEvidence(campaign_id=pilot.id, result_id=row.id,
                                 match_method="QA_SYNTHETIC")
                for row in qa_rows
            ])
            db.add_all([
                EvidenceAssessment(
                    campaign_id=pilot.id, result_id=source.id,
                    assessment_version=1, model_version="OFFLINE_FICTIONAL_QA",
                    relevance_label="IRRELEVANT", sentiment="NEGATIVE",
                    explanation="Fictional offline QA baseline.",
                ),
                EvidenceAssessment(
                    campaign_id=operational.id, result_id=protected.id,
                    assessment_version=1, model_version="OFFLINE_FICTIONAL_QA",
                    relevance_label="RELEVANT", sentiment="NEUTRAL",
                    explanation="Fictional protected evidence.",
                ),
            ])
            # Deliberately omit an assessment for the UNASSESSED scenario.
            for (key, label, sentiment, _message), row in zip(QA_SCENARIOS, qa_rows):
                if label is not None:
                    db.add(EvidenceAssessment(
                        campaign_id=pilot.id, result_id=row.id,
                        assessment_version=1, model_version="OFFLINE_FICTIONAL_QA",
                        relevance_label=label, sentiment=sentiment,
                        explanation="Fictional CI baseline, not a real AI evaluation.",
                    ))
            db.commit()
            if pilot.id != 1:
                raise SystemExit("REFUSED: unexpected CI campaign sequence")
            metadata = {
                "campaign_id": pilot.id,
                "source_id": source.id,
                "protected_campaign_id": operational.id,
                "protected_source_id": protected.id,
                "watchlist_source_id": watchlist.id,
                "scenario_source_ids": {key: row.id for (key, *_), row in
                                        zip(QA_SCENARIOS, qa_rows)},
            }
        output_path.write_text(json.dumps(metadata), encoding="utf-8")
        print("Created fictional Gate 1 pilot fixture in disposable localhost PostgreSQL.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m scripts.seed_gate1_ci_v1862 /absolute/path/ci-ids.json")
    seed(Path(sys.argv[1]))
