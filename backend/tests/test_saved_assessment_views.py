"""Zero-credit persisted classification reuse and permission regressions."""
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.models import (MonitoringCampaign, CampaignEvidence, SocialListeningResult,
                        EvidenceAssessment, IssueCategory, EvidenceReview)
from app.access import default_permissions
from app.saved_assessment_views import saved_classifications_for_posts


def setup_saved_rows():
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    db=Session(engine)
    post=SocialListeningResult(id=1,run_id=1,platform='instagram',
        text_content='Laporan dugaan pelanggaran politik uang dalam pemilu di Riau')
    campaign=MonitoringCampaign(id=10,name='Election oversight',province='Riau',
        created_by='1')
    category=IssueCategory(id=7,name='Election violation',active=True)
    db.add_all([post,campaign,category,CampaignEvidence(campaign_id=10,result_id=1)])
    db.flush()
    quote='dugaan pelanggaran politik uang dalam pemilu'
    assessment=EvidenceAssessment(campaign_id=10,result_id=1,assessment_version=2,
        relevance_label='RELEVANT',sentiment='NEGATIVE',model_version='test',
        potential_issue_signals_json=json.dumps([{'category_id':7,
            'signal_type':'POTENTIAL_VIOLATION','evidence_quote':quote}]))
    db.add(assessment)
    db.commit()
    return db,post,assessment


def national_profile():
    return {'status':'Active','geographic_scope':'Nationwide',
            'role':'National Administrator',
            'permissions':default_permissions('National Administrator')}


def test_watchlist_reuses_actual_saved_version_without_paid_processing():
    db,post,assessment=setup_saved_rows()
    try:
        records=saved_classifications_for_posts(db,national_profile(),[post])
        assert len(records[1])==1
        item=records[1][0]
        assert item['canonical_source_id']=='social:1'
        assert item['campaign_id']=='10'
        assert item['assessment_version']==2
        assert item['sentiment']=='NEGATIVE'
        assert item['signal_source']=='SAVED_ASSESSMENT'
        assert item['potential_issues'][0]['category_id']==7
        assert item['human_validation_required'] is True
        assert item['assessment_persisted'] is True
    finally:
        db.close()


def test_inactive_viewer_cannot_read_saved_assessments():
    db,post,_=setup_saved_rows()
    try:
        profile=national_profile()
        profile['status']='Inactive'
        assert saved_classifications_for_posts(db,profile,[post])=={1:[]}
    finally:
        db.close()


def test_superseded_relevant_assessment_does_not_leak_after_irrelevant_reassessment():
    db,post,_=setup_saved_rows()
    try:
        db.add(EvidenceAssessment(campaign_id=10,result_id=1,assessment_version=3,
            relevance_label='IRRELEVANT',potential_issue_signals_json='[]'))
        db.commit()
        assert saved_classifications_for_posts(db,national_profile(),[post])=={1:[]}
    finally:
        db.close()


def test_human_dismissal_is_reused_not_reflagged():
    db,post,assessment=setup_saved_rows()
    try:
        db.add(EvidenceReview(assessment_id=assessment.id,reviewer_id='1',
            decision='FLAG_DISMISSED',rationale='Reviewed with no actionable violation'))
        db.commit()
        item=saved_classifications_for_posts(db,national_profile(),[post])[1][0]
        assert item['review_status']=='FLAG_DISMISSED'
        assert item['is_flagged'] is False
        assert item['potential_issues'][0]['requires_human_verification'] is True
    finally:
        db.close()


def test_unlinked_campaign_assessment_is_not_exposed():
    db,post,_=setup_saved_rows()
    try:
        db.query(CampaignEvidence).delete()
        db.commit()
        assert saved_classifications_for_posts(db,national_profile(),[post])=={1:[]}
    finally:
        db.close()


def test_watchlist_feed_routes_through_saved_classifications():
    from pathlib import Path
    from app import registry
    content=Path(registry.__file__).read_text(encoding='utf-8')
    block=content.split("if action=='watchlistCapturedFeed':",1)[1].split("if action=='createWatchlist':",1)[0]
    assert 'saved_classifications_for_posts(db,p,rows)' in block
    assert "'saved_assessments':saved_views.get(item.id,[])" in block
    assert "'paid_provider_called':False" in block
