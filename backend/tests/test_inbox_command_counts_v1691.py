"""v169.1 compare real Inbox eligibility with Command Center activity/coverage.

All evidence is synthetic and loaded in isolated SQLite. No provider calls,
casework mutations or production Supabase changes.
"""
from datetime import datetime
import json
from app.models import SocialListeningResult,EvidenceAssessment,CampaignEvidence,MonitoringCampaign,IssueCategory,EvidenceReview
from app.officer_sentiment import OfficerSentimentCorrection
from app.campaigns import campaign_action
from app.command_center import build_command_center
from app.inbox_radar import compile_inbox_findings
from app.module_acceptance_evidence import module_acceptance_evidence
from test_e2e_handoff_acceptance_v1689 import fixture

def view(db,p):
    inbox=campaign_action(db,p,'campaignIntelligenceInbox',{'campaign_id':'31'},'31')
    command=build_command_center(db,p,{'period':'all'})
    return inbox,command

def test_latest_saved_relevance_matches_command_indicator_and_inbox():
    e,db,p=fixture()
    try:
        inbox,command=view(db,p)
        assert {str(x['id']) for x in inbox['findings']}=={'1','3'}
        assert command['indicators']['relevant_mentions']==2
        assert command['coverage']['relevant_distinct_posts']==2
        assert module_acceptance_evidence(db)['counts']['eligible_saved_inbox_links']==2
        assert command['paid_provider_called'] is False
    finally:db.close();e.dispose()

def test_preliminary_relevant_source_does_not_inflate_coverage_or_alerts():
    e,db,p=fixture()
    try:
        db.add(SocialListeningResult(id=7,run_id=1,platform='twitter-ai-search',
            text_content='A synthetic complaint about Bawaslu voter register',
            author_name='Test',canonical_url='https://example.invalid/seven',
            published_at=datetime.utcnow().date().isoformat()+'T08:00:00Z'))
        db.add(CampaignEvidence(campaign_id=31,result_id=7,match_method='KEYWORD'))
        db.add(EvidenceAssessment(campaign_id=31,result_id=7,assessment_version=1,
            relevance_label='RELEVANT',model_version='PRISM_PENDING_OPENAI',
            sentiment='NEGATIVE'))
        db.commit()
        inbox,command=view(db,p)
        assert {str(x['id']) for x in inbox['findings']}=={'1','3'}
        assert command['indicators']['relevant_mentions']==2
        assert command['coverage']['assessed_posts_in_period']==3
        assert command['coverage']['unassessed_posts_in_period']==2
        assert command['coverage']['captured_posts_in_period']==5
        assert module_acceptance_evidence(db)['counts']['eligible_saved_inbox_links']==2
        assert command['paid_provider_called'] is False
    finally:db.close();e.dispose()

def test_platform_activity_uses_same_normalized_vocabulary_as_inbox():
    e,db,p=fixture()
    try:
        db.get(SocialListeningResult,1).platform='twitter-ai-search'
        db.get(SocialListeningResult,3).platform='x'
        db.commit()
        inbox,command=view(db,p)
        normalized={x['id']:x['platform'] for x in inbox['findings']}
        assert normalized['1']=='twitter-ai-search'
        assert normalized['3']=='x'
        platforms={x['platform']:x['count'] for x in command['activity']['top_platforms']}
        assert platforms=={'Instagram':2,'X':2}
        highlighted={x['platform'] for x in command['activity']['recent_captured']}
        assert highlighted <= {'Instagram','X'}
        radar=compile_inbox_findings(inbox['findings'])
        assert all(x['platform'] in ('Instagram','X')
                   for f in radar for x in f['posts'])
    finally:db.close();e.dispose()

def test_irrelevant_latest_revision_removes_source_from_both_modules():
    e,db,p=fixture()
    try:
        db.add(EvidenceAssessment(campaign_id=31,result_id=1,
            assessment_version=2,relevance_label='IRRELEVANT'))
        db.commit()
        inbox,command=view(db,p)
        assert {x['id'] for x in inbox['findings']}=={'3'}
        assert command['indicators']['relevant_mentions']==1
        assert command['coverage']['relevant_distinct_posts']==1
        assert module_acceptance_evidence(db)['counts']['eligible_saved_inbox_links']==1
        assert all(x['result_id']!='1' for x in command['alerts'])
    finally:db.close();e.dispose()


def test_latest_version_revision_wins_inbox_command_and_coverage():
    e,db,p=fixture()
    try:
        db.add(EvidenceAssessment(campaign_id=31,result_id=1,
            assessment_version=2,relevance_label='IRRELEVANT',sentiment='NEUTRAL'))
        db.commit()
        inbox,command=view(db,p)
        assert {x['id'] for x in inbox['findings']}=={'3'}
        assert command['indicators']['relevant_mentions']==1
        assert command['coverage']['assessed_pairs_in_period']==3
        assert command['coverage']['relevant_distinct_posts']==1
        assert command['paid_provider_called'] is False
    finally:db.close();e.dispose()


def test_later_pending_provider_row_does_not_replace_completed_classification():
    e,db,p=fixture()
    try:
        db.add(EvidenceAssessment(campaign_id=31,result_id=1,
            assessment_version=10,relevance_label='IRRELEVANT',
            model_version='PRISM_PENDING_OPENAI'))
        db.commit()
        inbox,command=view(db,p)
        assert {x['id'] for x in inbox['findings']}=={'3'}
        assert command['indicators']['relevant_mentions']==1
        assert command['coverage']['assessed_pairs_in_period']==2
        assert command['paid_provider_called'] is False
    finally:db.close();e.dispose()


def test_topic_classifier_saved_label_matches_inbox_eligibility():
    e,db,p=fixture()
    try:
        db.add(SocialListeningResult(id=8,run_id=1,platform='x',
            text_content='Synthetic pending-only post',
            published_at=datetime.utcnow().date().isoformat()+'T01:00:00Z'))
        db.add(CampaignEvidence(campaign_id=31,result_id=8,match_method='KEYWORD'))
        db.add(EvidenceAssessment(campaign_id=31,result_id=8,
            assessment_version=1,relevance_label='RELEVANT',
            model_version='PRISM_OPENAI_TOPIC_CLASSIFIER'))
        db.commit()
        inbox,command=view(db,p)
        assert '8' in {x['id'] for x in inbox['findings']}
        assert command['indicators']['relevant_mentions']==3
        assert command['coverage']['captured_posts_in_period']==5
        assert command['coverage']['assessed_posts_in_period']==4
        assert command['paid_provider_called'] is False
    finally:db.close();e.dispose()


def test_recent_feed_preserves_completed_legacy_null_model_version():
    e,db,p=fixture()
    try:
        command=build_command_center(db,p,{'period':'all'})
        ids={x.get('result_id') for x in command['latest_intelligence']}
        assert ids & {'1','2','3'}
        assert command['paid_provider_called'] is False
    finally:db.close();e.dispose()


def test_inbox_effective_sentiment_preserves_original_ai_label():
    e,db,p=fixture()
    try:
        db.add(OfficerSentimentCorrection(campaign_id=31,result_id=1,
            sentiment='NEUTRAL',rationale='Source context verified',actor_id=1))
        db.commit()
        inbox,command=view(db,p)
        row=next(x for x in inbox['findings'] if x['id']=='1')
        assert row['sentiment']=='NEUTRAL'
        assert row['sentiment_origin']=='OFFICER_CORRECTION'
        assert row['ai_sentiment_original']=='NEGATIVE'
        assert row['sentiment_confidence']=='HUMAN_REVIEWED'
        assert row['sentiment_model']=='OFFICER_CORRECTION'
        assert db.query(EvidenceAssessment).filter_by(campaign_id=31,result_id=1).first().sentiment=='NEGATIVE'
        assert command['paid_provider_called'] is False
    finally:db.close();e.dispose()


def test_inbox_latest_officer_sentiment_override_wins():
    e,db,p=fixture()
    try:
        db.add(OfficerSentimentCorrection(campaign_id=31,result_id=1,
            sentiment='POSITIVE',rationale='Old correction',actor_id=1))
        db.add(OfficerSentimentCorrection(campaign_id=31,result_id=1,
            sentiment='NEUTRAL',rationale='New correction',actor_id=1))
        db.commit()
        inbox,_=view(db,p)
        row=next(x for x in inbox['findings'] if x['id']=='1')
        assert row['sentiment']=='NEUTRAL'
        assert row['sentiment_explanation']=='New correction'
    finally:db.close();e.dispose()


def test_saved_issue_alert_and_officer_dismissal_match_both_modules():
    e,db,p=fixture()
    try:
        db.add(IssueCategory(id=88,name='Synthetic issue',active=True))
        assessment=db.query(EvidenceAssessment).filter_by(campaign_id=31,result_id=1,assessment_version=1).first()
        assessment.potential_issue_signals_json=json.dumps([{
            'category_id':88,'signal_type':'POTENTIAL_VIOLATION',
            'evidence_quote':'Daftar pemilih tetap perlu diverifikasi di TPS',
            'explanation':'Source allegation requiring review'}])
        db.commit()
        inbox,command=view(db,p)
        assert next(x for x in inbox['findings'] if x['id']=='1')['is_flagged']
        assert command['indicators']['potential_alerts']==1
        db.add(EvidenceReview(assessment_id=assessment.id,reviewer_id='synthetic',
            decision='FLAG_DISMISSED',rationale='Not substantiated'))
        db.commit()
        inbox,command=view(db,p)
        row=next(x for x in inbox['findings'] if x['id']=='1')
        assert row['is_flagged'] is False
        assert row['flag_review_status']=='FLAG_DISMISSED'
        assert command['indicators']['potential_alerts']==0
        assert command['paid_provider_called'] is False
    finally:db.close();e.dispose()
