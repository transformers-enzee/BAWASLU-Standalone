"""No-cost, database-backed regression for SocialCrawl Discover duplicate posts.

This test deliberately uses the application's autoflush=False session and a
fake provider response: no live Supabase, SocialCrawl or OpenAI requests.
"""
import json
import os

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
from app.db import Base, engine, SessionLocal
from app.models import (
    MonitoringCampaign, SocialListeningRun, SocialListeningResult,
    CampaignRun, CampaignEvidence, EvidenceAssessment,
)
from app import prism_discover


def setup_function():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def seed(db):
    campaign = MonitoringCampaign(
        name='Discover local QA', description='Gibran election monitoring',
        primary_keywords_json='["Gibran"]',
        platforms_json='["instagram","tiktok"]',
        created_by='qa-admin', status='DRAFT',
    )
    db.add(campaign)
    db.flush()
    run = SocialListeningRun(
        provider='SOCIALCRAWL_PRISM', status='QUEUED',
        query_json=json.dumps({
            'campaign_id': campaign.id,
            'body': {'groups': [{'keywords': ['Gibran']}]},
        }),
        executed_by='qa-admin',
    )
    db.add(run)
    db.flush()
    db.add(CampaignRun(
        campaign_id=campaign.id, social_listening_run_id=run.id,
        triggered_by='PRISM_DISCOVER',
    ))
    db.commit()
    return campaign, run


def post(source_id, url, stance='negative', platform='instagram'):
    return {
        'id': source_id, 'platform': platform, 'url': url,
        'text': 'Warga membahas Gibran dan pengawasan Pilkada Jawa Barat.',
        'published_at': '2026-10-29T12:00:00Z',
        'author': {'username': 'public_news'},
        'judgments': {
            'stance': {'label': stance, 'confidence': 0.91},
            'relevance': {'p': 0.94},
        },
        'matched_keywords': ['Gibran'],
    }


def test_duplicate_id_and_url_in_single_provider_batch(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    db = SessionLocal()
    campaign, run = seed(db)
    first = post('post-1', 'https://instagram.com/p/source-1')
    duplicate_id = post('post-1', 'https://instagram.com/p/source-1')
    alternate_id_same_url = post('post-2', 'https://instagram.com/p/source-1')
    second = post('post-3', 'https://instagram.com/p/source-3', 'positive')
    saved = prism_discover.store(
        db, run, campaign,
        [first, duplicate_id, alternate_id_same_url, second],
    )
    assert saved == 2
    assert db.query(SocialListeningResult).count() == 2
    assert db.query(CampaignEvidence).count() == 2
    assessments = db.query(EvidenceAssessment).order_by(
        EvidenceAssessment.result_id).all()
    assert len(assessments) == 2
    assert {x.sentiment for x in assessments} == {'NEGATIVE', 'POSITIVE'}
    assert all(x.sentiment_model == 'socialcrawl-prism-stance' for x in assessments)
    assert all(x.relevance_label == 'RELEVANT' for x in assessments)
    db.close()


def test_repeated_run_reuses_existing_assessments_and_links(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    db = SessionLocal()
    campaign, run = seed(db)
    items = [
        post('post-1', 'https://instagram.com/p/source-1'),
        post('post-2', 'https://instagram.com/p/source-2'),
    ]
    assert prism_discover.store(db, run, campaign, items) == 2
    initial = {
        x.result_id: x.id for x in db.query(EvidenceAssessment).all()
    }
    assert prism_discover.store(
        db, run, campaign,
        items + [post('post-new-provider-id', 'https://instagram.com/p/source-1')],
    ) == 2
    assert db.query(SocialListeningResult).count() == 2
    assert db.query(CampaignEvidence).count() == 2
    assert {x.result_id: x.id for x in db.query(EvidenceAssessment).all()} == initial
    db.close()


def test_existing_human_assessment_is_not_overwritten(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    db = SessionLocal()
    campaign, run = seed(db)
    item = SocialListeningResult(
        run_id=run.id, provider='SOCIALCRAWL', provider_result_id='manual-1',
        platform='instagram', canonical_url='https://instagram.com/p/manual',
        text_content='Gibran public news',
    )
    db.add(item)
    db.flush()
    human = EvidenceAssessment(
        campaign_id=campaign.id, result_id=item.id,
        assessment_version=1, model_version='HUMAN',
        relevance_label='RELEVANT', sentiment='NEUTRAL',
    )
    db.add(human)
    db.commit()
    assert prism_discover.store(
        db, run, campaign,
        [post('discover-99', 'https://instagram.com/p/manual')],
    ) == 1
    assert db.query(CampaignEvidence).count() == 1
    assert db.query(SocialListeningResult).count() == 1
    rows = db.query(EvidenceAssessment).all()
    assert len(rows) == 1
    assert rows[0].id == human.id
    assert rows[0].model_version == 'HUMAN'
    assert rows[0].sentiment == 'NEUTRAL'
    db.close()


def test_execute_full_mock_provider_flow_completes_without_spending(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    db = SessionLocal()
    campaign, run = seed(db)
    provider_calls = []

    def fake_provider(method, url, body=None, timeout=50):
        provider_calls.append((method, url))
        return {
            'run': {'run_id': 'mock-provider', 'status': 'completed',
                    'credits': {'spent': 0}},
            'items': [
                post('same', 'https://instagram.com/p/same'),
                post('same', 'https://instagram.com/p/same'),
            ],
            'next': {},
        }, {'request_id': 'offline-mock', 'success': True}

    monkeypatch.setattr(prism_discover, 'call', fake_provider)
    prism_discover.execute(run.id)
    db.expire_all()
    saved_run = db.get(SocialListeningRun, run.id)
    assert saved_run.status == 'COMPLETED', saved_run.error_text
    assert saved_run.result_count == 1
    assert saved_run.credits_used == 0
    assert len(provider_calls) == 1
    assert db.query(CampaignEvidence).count() == 1
    assert db.query(EvidenceAssessment).count() == 1
    db.close()
