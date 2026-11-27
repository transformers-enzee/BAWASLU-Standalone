"""v186.6 isolated Render Gate 1 QA bootstrap.

ONLY the separately named Render QA Postgres database is eligible. The existing
BAWASLU Supabase project and staging service are explicitly ineligible.
No paid AI, social-listening calls, operational data or insight publication.
"""
import json
import os
from urllib.parse import urlsplit

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import hash_password
from app.db import Base, engine
from app.models import (
    AccessGrant, CampaignEvidence, EvidenceAssessment, MonitoringCampaign,
    SocialListeningResult, SocialListeningRun, User,
)
from app.inbox_human_corrections import (
    PILOT_QA_CAMPAIGN_NAME, PILOT_QA_PROVIDER, PILOT_QA_SOURCE_PREFIX,
)
from scripts.gate1_fixture_catalog_v1864 import QA_SCENARIOS

QA_DATABASE = "bawaslu_gate1_isolated_qa_db"
QA_DB_USER = "bawaslu_gate1_isolated_qa_db_user"
ADMIN_EMAIL = "gate1-qa-admin@example.invalid"
VIEWER_EMAIL = "gate1-qa-viewer@example.invalid"
BASELINE_KEY = "GATE1-QA-FAKE-1866-01"
WATCHLIST_KEY = "GATE1-QA-WATCHLIST-1866"
EXPECTED_KEYS = {BASELINE_KEY, WATCHLIST_KEY} | {
    PILOT_QA_SOURCE_PREFIX + "FICTIONAL-1864-" + key
    for key, *_ in QA_SCENARIOS
}


def assert_isolated_qa_database(url: str):
    """Fail closed before any SQL, even when other pilot flags are enabled."""
    parsed = urlsplit(url.replace("postgresql+psycopg://", "postgresql://", 1))
    host = (parsed.hostname or "").lower()
    local_ci = (host in {"127.0.0.1", "localhost"}
                and os.getenv("BAWASLU_ALLOW_ISOLATED_DB_TEST") == "YES")
    render_host = host.startswith("dpg-") and "supabase" not in host
    if not (
        os.getenv("BAWASLU_GATE1_QA_ISOLATED") == "YES"
        and os.getenv("BAWASLU_GATE1_QA_BOOTSTRAP") == "YES"
        and os.getenv("BAWASLU_STARTUP_READ_ONLY", "1") == "1"
        and parsed.scheme == "postgresql"
        and parsed.path == "/" + QA_DATABASE
        and parsed.username == QA_DB_USER
        and bool(parsed.password)
        and (render_host or local_ci)
    ):
        raise SystemExit(
            "REFUSED: only the dedicated Render Gate 1 QA PostgreSQL database "
            "or explicitly opted-in disposable localhost CI database may be seeded"
        )


def _existing_fixture_is_safe(db: Session):
    """Never overwrite or repair an unknown database on subsequent startups."""
    campaigns = db.query(MonitoringCampaign).all()
    sources = db.query(SocialListeningResult).all()
    users = db.query(User).all()
    links = db.query(CampaignEvidence).all()
    if (len(campaigns) != 1 or campaigns[0].id != 1
            or campaigns[0].name != PILOT_QA_CAMPAIGN_NAME
            or campaigns[0].status != "DRAFT"
            or {u.email for u in users} != {ADMIN_EMAIL, VIEWER_EMAIL}
            or len(sources) != len(EXPECTED_KEYS)
            or {s.provider_result_id for s in sources} != EXPECTED_KEYS
            or any(s.provider != PILOT_QA_PROVIDER or
                   s.review_state != "QA_ONLY" for s in sources)
            or len(links) != len(EXPECTED_KEYS)
            or any(link.campaign_id != 1 for link in links)):
        raise SystemExit("REFUSED: QA database contents differ from expected fictional fixture")
    for link in links:
        source = next((s for s in sources if s.id == link.result_id), None)
        if source is None:
            raise SystemExit("REFUSED: invalid QA evidence link")
        if source.provider_result_id == WATCHLIST_KEY:
            if link.match_method != "WATCHLIST_ACCOUNT":
                raise SystemExit("REFUSED: watchlist-only fixture relinked")
        elif link.match_method != "QA_SYNTHETIC":
            raise SystemExit("REFUSED: ordinary QA evidence link changed")
    if any(not s.canonical_url.startswith("https://example.invalid/")
           for s in sources if s.canonical_url):
        raise SystemExit("REFUSED: non-fictional canonical URL in QA database")


def bootstrap():
    assert_isolated_qa_database(os.getenv("DATABASE_URL", ""))
    admin_password = os.getenv("BAWASLU_GATE1_QA_ADMIN_PASSWORD", "")
    viewer_password = os.getenv("BAWASLU_GATE1_QA_VIEWER_PASSWORD", "")
    if (len(admin_password) < 24 or len(viewer_password) < 24
            or admin_password == viewer_password):
        raise SystemExit("REFUSED: unique strong synthetic QA credentials required")
    # Only now import the full model catalog and create isolated test tables.
    from app import main as _all_models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    with Session(engine) as db:
        if db.scalar(select(func.count()).select_from(MonitoringCampaign)):
            _existing_fixture_is_safe(db)
            print("Gate 1 isolated QA fixture already present; no changes made")
            return
        if (db.scalar(select(func.count()).select_from(User))
                or db.scalar(select(func.count()).select_from(SocialListeningResult))
                or db.scalar(select(func.count()).select_from(EvidenceAssessment))
                or db.scalar(select(func.count()).select_from(CampaignEvidence))
                or db.scalar(select(func.count()).select_from(SocialListeningRun))):
            raise SystemExit("REFUSED: nonempty unidentified QA database")
        admin = User(email=ADMIN_EMAIL, full_name="Fictional Gate 1 QA Admin",
                     password_hash=hash_password(admin_password), platform_admin=False)
        viewer = User(email=VIEWER_EMAIL, full_name="Fictional Gate 1 QA Viewer",
                      password_hash=hash_password(viewer_password), platform_admin=False)
        db.add_all([admin, viewer])
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
        campaign = MonitoringCampaign(
            name=PILOT_QA_CAMPAIGN_NAME, status="DRAFT",
            created_by=str(admin.id), primary_keywords_json="[]",
            platforms_json='["facebook"]', next_run_at=None,
            description="Fictional QA only. Never use for official election intelligence.",
        )
        db.add(campaign)
        db.flush()
        if campaign.id != 1:
            raise SystemExit("REFUSED: unexpected QA campaign ID; required allowlist is 1")
        run = SocialListeningRun(
            provider=PILOT_QA_PROVIDER,
            query_json='{"fictional":true,"paid_requests":0,"qa_only":true}',
            status="COMPLETED", credits_used=0, result_count=len(EXPECTED_KEYS),
            executed_by="render-isolated-qa-v1866",
        )
        db.add(run)
        db.flush()
        baseline = SocialListeningResult(
            run_id=run.id, provider=PILOT_QA_PROVIDER, provider_result_id=BASELINE_KEY,
            platform="facebook", content_type="post",
            canonical_url="https://example.invalid/gate1/qa-baseline",
            author_name="Fictional QA Baseline Account",
            text_content="Fictional election information post; QA baseline intentionally mislabeled.",
            raw_payload_json='{"fictional":true,"qa_only":true,"baseline":true}',
            source_identity_json='{"fictional":true}', geography_json="{}",
            content_fingerprint="render-gate1-qa-baseline-1866", review_state="QA_ONLY",
        )
        records = [(baseline, "IRRELEVANT", "NEGATIVE")]
        for key, label, sentiment, message in QA_SCENARIOS:
            records.append((
                SocialListeningResult(
                    run_id=run.id, provider=PILOT_QA_PROVIDER,
                    provider_result_id=PILOT_QA_SOURCE_PREFIX + "FICTIONAL-1864-" + key,
                    platform="facebook", content_type="post",
                    canonical_url="https://example.invalid/gate1/qa-" + key.lower(),
                    author_name="Fictional QA Scenario Account", text_content=message,
                    raw_payload_json=json.dumps({"fictional": True,"qa_only": True,
                                                  "scenario": key},sort_keys=True),
                    source_identity_json='{"fictional":true}', geography_json="{}",
                    content_fingerprint="render-gate1-qa-" + key.lower() + "-1866",
                    review_state="QA_ONLY",
                ), label, sentiment,
            ))
        watchlist = SocialListeningResult(
            run_id=run.id, provider=PILOT_QA_PROVIDER, provider_result_id=WATCHLIST_KEY,
            platform="facebook", content_type="post",
            canonical_url="https://example.invalid/gate1/qa-watchlist",
            author_name="Fictional QA Watchlist",
            text_content="Fictional watchlist-only example, excluded from ordinary review.",
            raw_payload_json='{"fictional":true,"qa_only":true,"watchlist_only":true}',
            source_identity_json='{"fictional":true}', geography_json="{}",
            content_fingerprint="render-gate1-qa-watchlist-1866", review_state="QA_ONLY",
        )
        db.add_all([row for row, _, _ in records] + [watchlist])
        db.flush()
        db.add_all([
            CampaignEvidence(campaign_id=campaign.id, result_id=row.id,
                             match_method="QA_SYNTHETIC")
            for row, _, _ in records
        ])
        db.add(CampaignEvidence(campaign_id=campaign.id, result_id=watchlist.id,
                                match_method="WATCHLIST_ACCOUNT"))
        db.add_all([
            EvidenceAssessment(
                campaign_id=campaign.id, result_id=row.id,
                assessment_version=1, model_version="OFFLINE_FICTIONAL_QA",
                relevance_label=label, sentiment=sentiment,
                explanation="Deliberately fictional QA baseline; not a real model judgment.",
            )
            for row, label, sentiment in records if label is not None
        ])
        db.commit()
        print("Gate 1 isolated QA bootstrapped: 6 ordinary fictional posts, "
              "1 watchlist-only post, zero paid API calls")


if __name__ == "__main__":
    bootstrap()
